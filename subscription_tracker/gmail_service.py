"""
Module 1: User Login and Authentication (Google OAuth)
Module 2: Gmail Connection (Gmail API)
"""
import base64
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

from config import Config

# A generous search query covering common subscription/payment language.
GMAIL_SEARCH_QUERY = (
    'subject:(subscription OR renewal OR invoice OR receipt OR membership '
    'OR "payment successful" OR "auto-renewal" OR "auto renewal" '
    'OR "payment confirmation") newer_than:180d'
)


def build_flow(state=None, code_verifier=None):
    flow = Flow.from_client_secrets_file(
        Config.GOOGLE_CLIENT_SECRET_FILE,
        scopes=Config.GOOGLE_SCOPES,
        state=state,
    )
    flow.redirect_uri = Config.GOOGLE_REDIRECT_URI
    if code_verifier:
        # Must reuse the SAME code_verifier that was used to build the
        # authorization URL in /login — PKCE requires it to match exactly
        # when the code is exchanged for a token in /oauth2callback.
        flow.code_verifier = code_verifier
    return flow


def credentials_to_dict(creds: Credentials):
    return {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes,
    }


def credentials_from_dict(data: dict):
    return Credentials(**data)


def get_user_email(creds: Credentials):
    service = build("oauth2", "v2", credentials=creds)
    return service.userinfo().get().execute().get("email")


def fetch_subscription_emails(creds: Credentials, max_results: int = 40):
    """
    Module 2 + 3: pull permitted emails matching subscription-ish search
    terms, and return a lightweight list of {subject, sender, snippet, date, id}.
    Uses metadata/snippet only — never downloads full message bodies unless needed.
    """
    service = build("gmail", "v1", credentials=creds)

    results = service.users().messages().list(
        userId="me", q=GMAIL_SEARCH_QUERY, maxResults=max_results
    ).execute()
    messages = results.get("messages", [])

    parsed = []
    for m in messages:
        msg = service.users().messages().get(
            userId="me", id=m["id"], format="metadata",
            metadataHeaders=["Subject", "From", "Date"],
        ).execute()

        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        parsed.append({
            "id": msg["id"],
            "subject": headers.get("Subject", ""),
            "sender": headers.get("From", ""),
            "date": headers.get("Date", ""),
            "snippet": msg.get("snippet", ""),
        })
    return parsed
