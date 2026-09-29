"""
Module 10: AI Chatbot.

Answers basic questions about subscriptions/renewals/the app. Uses the
user's own detected subscription data as context. Falls back to a small
rule-based FAQ when no Gemini API key is configured, so the chatbot always
works even for a free/offline demo.
"""
import json
import requests
from config import Config

FAQ = [
    # More specific phrases must be checked before broader ones like "how".
    (["how many", "count", "total"], "Check the dashboard header — it shows your "
     "total number of detected subscriptions."),
    (["cancel"], "I can't cancel subscriptions directly since that has to happen "
     "on each service's own site. Click 'Manage / Cancel' on a subscription card "
     "and I'll send you straight to that service's cancellation page."),
    (["renew", "renewal date"], "Renewal dates are pulled from the email text when "
     "a date is present near a renewal/billing keyword. If a subscription shows "
     "no date, the source email just didn't mention one clearly."),
    (["safe", "privacy", "secure"], "The app only requests read-only Gmail access "
     "and only looks at subject lines, senders, and short snippets — it never "
     "reads full email bodies unless it needs to, and it can't send or delete mail."),
    (["how", "work", "detect"], "I scan your Gmail inbox for emails containing "
     "words like 'subscription', 'invoice', 'renewal', or 'payment successful', "
     "then pull out the service name, amount, and renewal date from each match."),
]


def rule_based_reply(message: str):
    text = message.lower()
    for keywords, answer in FAQ:
        if any(k in text for k in keywords):
            return answer
    return ("I can help with questions about your detected subscriptions, "
            "renewal dates, or how this app works. Try asking something like "
            "'how many subscriptions do I have?' or 'how does detection work?'")


def gemini_reply(message: str, subscriptions: list):
    context = "\n".join(
        f"- {s['service_name']}: status={s['status']}, amount={s.get('payment_amount')}, "
        f"renewal={s.get('renewal_date')}, category={s.get('category')}"
        for s in subscriptions[:20]
    ) or "(no subscriptions detected yet)"

    prompt = (
        "You are a helpful assistant inside a subscription-tracker web app. "
        "Answer briefly and only using the data given below when relevant. "
        f"User's detected subscriptions:\n{context}\n\nUser question: {message}"
    )
    resp = requests.post(
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-1.5-flash:generateContent?key={Config.GEMINI_API_KEY}",
        json={"contents": [{"parts": [{"text": prompt}]}]},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()


def get_reply(message: str, subscriptions: list):
    if Config.GEMINI_API_KEY:
        try:
            return gemini_reply(message, subscriptions)
        except Exception:
            pass  # fall through to rule-based
    return rule_based_reply(message)
