"""
Module 3 & 9: Email Searching/Detection + optional AI-Based Email Classification.

Two layers, matching the project spec:
1. Keyword + regex matching (always on, free, fast).
2. Optional Gemini-based classification for emails keyword matching is unsure about.
"""
import re

SUBSCRIPTION_KEYWORDS = [
    "subscription", "payment successful", "renewal", "auto-renewal",
    "auto renewal", "invoice", "membership", "monthly payment",
    "subscription confirmation", "your receipt", "billing", "renews on",
    "next billing date", "payment confirmation", "order confirmation",
    "plan renewed", "recurring payment", "trial ending", "premium plan",
]

KNOWN_SERVICES = [
    "Netflix", "Spotify", "Amazon Prime", "YouTube Premium", "Disney+",
    "Hotstar", "Google One", "Google Drive", "iCloud", "Apple Music",
    "Coursera", "Udemy", "LinkedIn Premium", "Adobe Creative Cloud",
    "Canva", "Notion", "Dropbox", "Microsoft 365", "ChatGPT Plus",
    "Zomato Gold", "Swiggy One", "JioCinema", "SonyLIV", "Audible",
]

AMOUNT_RE = re.compile(r"(?:₹|Rs\.?|INR|\$|USD)\s?([\d,]+(?:\.\d{1,2})?)", re.IGNORECASE)
DATE_RE = re.compile(
    r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{2,4})\b",
    re.IGNORECASE,
)


def keyword_score(subject: str, snippet: str):
    """Returns (matched: bool, matched_keywords: list[str])."""
    text = f"{subject} {snippet}".lower()
    matched = [kw for kw in SUBSCRIPTION_KEYWORDS if kw in text]
    return (len(matched) > 0, matched)


def detect_service_name(subject: str, sender: str, snippet: str):
    text = f"{subject} {sender} {snippet}"
    for service in KNOWN_SERVICES:
        if service.lower() in text.lower():
            return service
    # fall back: use the sender's display name / domain
    if sender:
        name = sender.split("<")[0].strip().strip('"')
        if name:
            return name
        domain = sender.split("@")[-1].split(">")[0]
        return domain.split(".")[0].capitalize()
    return "Unknown service"


def extract_amount(text: str):
    m = AMOUNT_RE.search(text)
    if not m:
        return None, None
    amount = m.group(1)
    currency = "INR" if any(c in m.group(0) for c in ["₹", "Rs", "INR"]) else "USD"
    return amount, currency


def extract_renewal_date(text: str):
    m = DATE_RE.search(text)
    return m.group(1) if m else None


def categorize(service_name: str):
    entertainment = ["netflix", "spotify", "prime", "youtube", "disney", "hotstar",
                      "jiocinema", "sonyliv", "audible"]
    cloud = ["google one", "google drive", "icloud", "dropbox", "onedrive"]
    education = ["coursera", "udemy", "linkedin"]
    productivity = ["notion", "canva", "adobe", "microsoft 365", "chatgpt"]

    name = service_name.lower()
    if any(k in name for k in entertainment):
        return "Entertainment"
    if any(k in name for k in cloud):
        return "Cloud Storage"
    if any(k in name for k in education):
        return "Education"
    if any(k in name for k in productivity):
        return "Productivity"
    return "Other"


def rule_based_detect(subject: str, sender: str, snippet: str, date: str):
    """Pure keyword/regex path — Module 3 baseline. No API key needed."""
    is_match, matched_keywords = keyword_score(subject, snippet)
    if not is_match:
        return None

    full_text = f"{subject} {snippet}"
    service_name = detect_service_name(subject, sender, snippet)
    amount, currency = extract_amount(full_text)
    renewal_date = extract_renewal_date(full_text)

    return {
        "service_name": service_name,
        "status": "active",
        "payment_amount": amount,
        "currency": currency,
        "renewal_date": renewal_date,
        "category": categorize(service_name),
        "detection_method": "keyword",
        "confidence": min(1.0, 0.4 + 0.15 * len(matched_keywords)),
    }


def ai_classify(subject: str, sender: str, snippet: str, api_key: str):
    """
    Module 9: optional Gemini-based classification for emails the keyword
    pass skipped. Only called when GEMINI_API_KEY is set. Falls back to
    None (i.e. 'not a subscription email') on any error so the app never
    hard-depends on this.
    """
    if not api_key:
        return None
    try:
        import requests
        prompt = (
            "You classify emails for a subscription tracker app. "
            "Given the email subject, sender, and snippet below, respond with "
            "ONLY a JSON object and nothing else, in the form: "
            '{"is_subscription": true/false, "service_name": "...", '
            '"payment_amount": "..." or null, "renewal_date": "..." or null}. '
            f"Subject: {subject}\nSender: {sender}\nSnippet: {snippet}"
        )
        resp = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-1.5-flash:generateContent?key={api_key}",
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=15,
        )
        resp.raise_for_status()
        text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        text = text.strip().strip("```").replace("json", "", 1).strip()
        import json
        data = json.loads(text)
        if not data.get("is_subscription"):
            return None
        service_name = data.get("service_name") or detect_service_name(subject, sender, snippet)
        return {
            "service_name": service_name,
            "status": "active",
            "payment_amount": data.get("payment_amount"),
            "currency": None,
            "renewal_date": data.get("renewal_date"),
            "category": categorize(service_name),
            "detection_method": "ai",
            "confidence": 0.7,
        }
    except Exception:
        return None


def detect(subject: str, sender: str, snippet: str, date: str, api_key: str = ""):
    """Module 3 + Module 9 combined entry point."""
    result = rule_based_detect(subject, sender, snippet, date)
    if result:
        return result
    return ai_classify(subject, sender, snippet, api_key)
