import json
import os
import re

from flask import Flask, render_template, redirect, url_for, session, request, jsonify, flash

from config import Config
from models import db, Subscription
import detector
import chatbot

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

with app.app_context():
    db.create_all()

DEMO_USER_EMAIL = "demo.user@gmail.com"


# ---------------------------------------------------------------- helpers --
def current_user_email():
    return session.get("user_email")


def require_login():
    if not current_user_email():
        return redirect(url_for("login"))
    return None


def run_detection_pipeline(user_email: str, emails: list):
    """Module 3/4/9 pipeline: detect + extract + store, skipping dupes."""
    existing_ids = {
        row.source_email_id
        for row in Subscription.query.filter_by(user_email=user_email).all()
    }
    added = 0
    for e in emails:
        if e["id"] in existing_ids:
            continue
        result = detector.detect(
            e["subject"], e["sender"], e["snippet"], e["date"],
            api_key=Config.GEMINI_API_KEY,
        )
        if not result:
            continue
        sub = Subscription(
            user_email=user_email,
            service_name=result["service_name"],
            status=result["status"],
            payment_amount=result["payment_amount"],
            currency=result["currency"],
            renewal_date=result["renewal_date"],
            category=result["category"],
            source_email_subject=e["subject"],
            source_email_from=e["sender"],
            source_email_date=e["date"],
            source_email_id=e["id"],
            detection_method=result["detection_method"],
            confidence=result["confidence"],
        )
        db.session.add(sub)
        added += 1
    db.session.commit()
    return added


# -------------------------------------------------------------- Module 1 --
@app.route("/")
def index():
    if current_user_email():
        return redirect(url_for("dashboard"))
    return render_template("login.html", demo_mode=Config.DEMO_MODE)


@app.route("/login")
def login():
    if Config.DEMO_MODE:
        # Demo mode: skip real Google OAuth, sign in as a sample user.
        session["user_email"] = DEMO_USER_EMAIL
        return redirect(url_for("sync"))

    import gmail_service
    flow = gmail_service.build_flow()
    auth_url, state = flow.authorization_url(
        access_type="offline", include_granted_scopes="true", prompt="consent"
    )
    session["oauth_state"] = state
    session["code_verifier"] = flow.code_verifier
    return redirect(auth_url)


@app.route("/oauth2callback")
def oauth2callback():
    import gmail_service
    from oauthlib.oauth2.rfc6749.errors import MismatchingStateError

    state = session.get("oauth_state")
    code_verifier = session.get("code_verifier")
    if not state:
        flash("Your Google login expired. Please try signing in again.")
        return redirect(url_for("login"))

    flow = gmail_service.build_flow(state=state, code_verifier=code_verifier)
    if request.host.split(":", 1)[0] in {"localhost", "127.0.0.1"}:
        os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")
    try:
        flow.fetch_token(authorization_response=request.url)
    except MismatchingStateError:
        session.pop("oauth_state", None)
        session.pop("code_verifier", None)
        flash("The Google login session was stale. Please try signing in again.")
        return redirect(url_for("login"))

    creds = flow.credentials

    session["credentials"] = gmail_service.credentials_to_dict(creds)
    session["user_email"] = gmail_service.get_user_email(creds)
    return redirect(url_for("sync"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# -------------------------------------------------- Modules 2, 3, 4, 5 --
@app.route("/sync")
def sync():
    redirect_needed = require_login()
    if redirect_needed:
        return redirect_needed

    user_email = current_user_email()

    if Config.DEMO_MODE:
        sample_path = os.path.join(os.path.dirname(__file__), "data", "sample_emails.json")
        with open(sample_path) as f:
            emails = json.load(f)
    else:
        import gmail_service
        creds = gmail_service.credentials_from_dict(session["credentials"])
        emails = gmail_service.fetch_subscription_emails(creds)

    added = run_detection_pipeline(user_email, emails)
    flash(f"Synced Gmail — {added} new subscription(s) detected.")
    return redirect(url_for("dashboard"))


# ------------------------------------------------------------- Module 6 --
@app.route("/dashboard")
def dashboard():
    redirect_needed = require_login()
    if redirect_needed:
        return redirect_needed

    subs = Subscription.query.filter_by(user_email=current_user_email()).order_by(
        Subscription.service_name
    ).all()

    total = len(subs)
    by_category = {}
    for s in subs:
        by_category.setdefault(s.category or "Other", []).append(s)

    return render_template(
        "dashboard.html",
        subs=subs,
        total=total,
        by_category=by_category,
        user_email=current_user_email(),
        demo_mode=Config.DEMO_MODE,
    )


# ------------------------------------------------------------- Module 7 --
@app.route("/subscription/<int:sub_id>")
def subscription_detail(sub_id):
    redirect_needed = require_login()
    if redirect_needed:
        return redirect_needed

    sub = Subscription.query.filter_by(
        id=sub_id, user_email=current_user_email()
    ).first_or_404()
    return render_template("subscription_detail.html", sub=sub)


# ------------------------------------------------------------- Module 8 --
CANCEL_URLS = {
    "netflix": "https://www.netflix.com/cancelplan",
    "spotify": "https://www.spotify.com/account/subscription/",
    "amazon prime": "https://www.amazon.in/mc/pipelines/cancellation",
    "google one": "https://one.google.com/storage",
    "youtube premium": "https://www.youtube.com/paid_memberships",
    "coursera": "https://www.coursera.org/account-settings",
    "adobe creative cloud": "https://account.adobe.com/plans",
    "udemy": "https://www.udemy.com/user/edit-subscriptions/",
    "reddit": "https://www.reddit.com/settings/premium",
    "razorpay": "https://dashboard.razorpay.com/app/subscriptions",
    "team razorpay": "https://dashboard.razorpay.com/app/subscriptions",
}


def extract_sender_domain(sender: str):
    """Pull the domain out of a 'Name <user@domain.com>' style From header."""
    m = re.search(r"@([\w.-]+)", sender or "")
    if not m:
        return None
    domain = m.group(1).lower()
    # Emails often come from a "no-reply.*" or "mail.*" subdomain — the
    # human-facing site is almost always the bare root domain, so collapse
    # to the last two labels (e.g. "notifications.reddit.com" -> "reddit.com").
    parts = domain.split(".")
    if len(parts) > 2:
        domain = ".".join(parts[-2:])
    return domain


@app.route("/subscription/<int:sub_id>/manage")
def manage_subscription(sub_id):
    redirect_needed = require_login()
    if redirect_needed:
        return redirect_needed

    sub = Subscription.query.filter_by(
        id=sub_id, user_email=current_user_email()
    ).first_or_404()

    url = CANCEL_URLS.get(sub.service_name.lower())
    if url:
        return redirect(url)

    # No exact cancellation page known — send them to the actual company's
    # site (parsed from the email sender's domain) rather than a search
    # results page, so they land in "the app" and can log in from there.
    domain = extract_sender_domain(sub.source_email_from)
    if domain:
        return redirect(f"https://{domain}")

    query = f"{sub.service_name} cancel subscription"
    return redirect(f"https://www.google.com/search?q={query.replace(' ', '+')}")


# ------------------------------------------------------------ Module 10 --
@app.route("/api/chat", methods=["POST"])
def api_chat():
    redirect_needed = require_login()
    if redirect_needed:
        return jsonify({"error": "not logged in"}), 401

    message = request.json.get("message", "").strip()
    if not message:
        return jsonify({"error": "empty message"}), 400

    subs = Subscription.query.filter_by(user_email=current_user_email()).all()
    reply = chatbot.get_reply(message, [s.to_dict() for s in subs])
    return jsonify({"reply": reply})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
