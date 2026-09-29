import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


# OAuthlib blocks HTTP callbacks by default. Allow it only for localhost
# development; deployed applications must use HTTPS instead.
if os.environ.get("GOOGLE_REDIRECT_URI", "").startswith("http://localhost:"):
    os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")


class Config:
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")
    DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
    elif DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
    SQLALCHEMY_DATABASE_URI = DATABASE_URL or "sqlite:///" + os.path.join(BASE_DIR, "subscriptions.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    DEMO_MODE = os.environ.get("DEMO_MODE", "true").lower() == "true"

    GOOGLE_CLIENT_SECRET_FILE = os.path.join(
        BASE_DIR, os.environ.get("GOOGLE_CLIENT_SECRET_FILE", "google_client_secret.json")
    )
    GOOGLE_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly",
                      "https://www.googleapis.com/auth/userinfo.email",
                      "https://www.googleapis.com/auth/userinfo.profile",
                      "openid"]
    GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "http://localhost:5000/oauth2callback")

    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
