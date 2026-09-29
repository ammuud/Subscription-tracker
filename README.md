# Subscription Tracker

A Flask app that scans Gmail for subscription-related emails and organizes detected services, payments, and renewal dates in a dashboard.

The application source code and full setup instructions are in [`subscription_tracker/`](subscription_tracker/README.md).

## Quick Start

Open a terminal in the `subscription_tracker` folder, install the requirements, copy `.env.example` to `.env`, and run the demo:

```powershell
cd subscription_tracker
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python app.py
```

Then visit <http://localhost:5000>. Demo mode uses sample email data and does not require Google OAuth.

For real Gmail setup, Neon PostgreSQL configuration, and deployment notes, see the [full README](subscription_tracker/README.md).

## Security

Never commit `.env`, Google OAuth credential JSON files, database connection strings, or API keys. The repository ignores local secret files; configure deployment secrets in your hosting provider instead.