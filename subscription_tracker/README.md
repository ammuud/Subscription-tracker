# Subscription Tracker and Management System

A Flask web app that scans Gmail for subscription/renewal/payment emails and
shows them on one organized dashboard. Built to match the project spec's
10 modules (login, Gmail connection, detection, extraction, database,
dashboard, details, manage/cancel redirect, optional AI classification,
and an AI chatbot).

## Quick start (demo mode — no Google account needed)

This is the fastest way to see the whole app working, using realistic
sample emails instead of your real inbox. Good for a project demo/presentation.

```bash
cd subscription_tracker
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # DEMO_MODE=true is already set
python app.py
```

Open **http://localhost:5000**, click "Try the demo", and it will sign you
in as a sample user and populate the dashboard from `data/sample_emails.json`.

## Connecting your real Gmail account

1. Go to the [Google Cloud Console](https://console.cloud.google.com/) and
   create a new project.
2. Under **APIs & Services > Library**, enable the **Gmail API**.
3. Under **APIs & Services > OAuth consent screen**, set it up as "External"
   and add your own Gmail address as a test user (required while the app is
   unpublished).
4. Under **APIs & Services > Credentials**, create an **OAuth client ID**
   of type **Web application**, and add this to "Authorized redirect URIs":
   `http://localhost:5000/oauth2callback`
5. Download the client secret JSON and save it as
   `subscription_tracker/google_client_secret.json`.
6. In `.env`, set `DEMO_MODE=false`.
7. Run `python app.py` and click "Sign in with Google" — you'll see Google's
   real consent screen asking for read-only Gmail access.

The app never requests permission to send, delete, or modify email — only
read access (`gmail.readonly`).

## Optional: smarter detection + chatbot with Gemini

Keyword matching alone catches most subscription emails, but some emails
mention a renewal without any of the exact trigger words. If you want the
AI-classification module (Module 9) and a smarter chatbot (Module 10) to
kick in for those edge cases:

1. Get a free key at https://aistudio.google.com/app/apikey
2. Put it in `.env` as `GEMINI_API_KEY=...`

Without a key, the app still works fully — it just relies on the built-in
keyword/regex detector and a small rule-based chatbot FAQ.

## Project structure

```
subscription_tracker/
├── app.py                  # Flask routes / all 10 modules wired together
├── config.py                # Env-based configuration
├── models.py                 # SQLAlchemy Subscription model (SQLite)
├── detector.py                # Module 3/4/9 — keyword+regex detection, extraction, optional AI
├── gmail_service.py            # Module 1/2 — Google OAuth + Gmail API calls
├── chatbot.py                   # Module 10 — rule-based FAQ + optional Gemini chatbot
├── data/sample_emails.json       # Demo-mode sample inbox
├── templates/                     # Jinja2 HTML templates
├── static/style.css, script.js     # Styling + chatbot widget behavior
└── requirements.txt
```

## How detection works (Module 3/4)

1. Gmail is queried with a search like
   `subject:(subscription OR renewal OR invoice OR receipt OR membership OR "payment successful" ...)`.
2. Each matching email's subject/sender/snippet is scanned for keywords
   (`subscription`, `renewal`, `invoice`, `auto-renewal`, etc.) — see
   `detector.SUBSCRIPTION_KEYWORDS`.
3. If matched, regex pulls out an amount (`₹649`, `$399`, ...) and a date.
4. The service name is matched against a list of common subscription
   services, falling back to the sender's name/domain.
5. If Gemini is configured, emails that keyword-matching skips are given one
   more pass through the AI classifier before being discarded.

## Known limitations (matches the project's stated scope)

- Cannot cancel subscriptions directly — "Manage/Cancel" redirects to each
  service's own account or cancellation page.
- Detection quality depends on keyword coverage; some ambiguous emails may
  be missed or misclassified without the optional AI layer.
- Built for academic/personal use, not production-scale email volumes.
