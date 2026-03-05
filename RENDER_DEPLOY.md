# Deploy Backend to Render (Flask + Postgres)

This backend supports:
- Local dev on Windows/XAMPP (MySQL by default)
- Render Postgres by setting `DATABASE_URL`
- Production hosting on Render using Gunicorn

## 1) Prerequisites

- Your code must be in a Git repo (GitHub/GitLab) for Render to deploy it.
- Your Render Postgres database must be created (or create it during setup).

## 2) Create the Render Web Service

Render Dashboard → **New** → **Web Service** → connect your repo.

**Settings**
- **Environment**: Python
- **Root Directory**: (leave blank) or `.`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn wsgi:app --bind 0.0.0.0:$PORT`

If you deploy using the included `render.yaml`, Render will use these commands automatically.

## 3) Set Environment Variables (Render → Service → Environment)

Required:
- `FLASK_ENV=production`
- `DEBUG=False`
- `SECRET_KEY=<generate a long random string>`
- `JWT_SECRET_KEY=<generate a long random string>`
- `DATABASE_URL=<Render Postgres INTERNAL database URL>`

Optional (only if you use PayMongo / OTP etc):
- `PAYMONGO_SECRET_KEY=...`
- `PAYMONGO_WEBHOOK_SECRET=...`
- `PUBLIC_HTTPS_BASE_URL=https://<your-render-service>.onrender.com`

### OTP Email via SendGrid (recommended)

This backend sends Loyalty Member OTP emails via SMTP (see `utils/otp_email.py`).
This backend supports SendGrid in two ways:

1) SendGrid HTTP API (recommended on Render)

- `SENDGRID_API_KEY=<your SendGrid API key>`
- `SENDGRID_FROM=<a verified sender email in SendGrid>`

2) SendGrid SMTP (fallback)

- `SMTP_HOST=smtp.sendgrid.net`
- `SMTP_PORT=587`
- `SMTP_USERNAME=apikey`
- `SMTP_PASSWORD=<your SendGrid API key>`
- `SMTP_FROM=<a verified sender email in SendGrid>`
- `SMTP_USE_TLS=true`

Timeouts (recommended):
- `EMAIL_SEND_TIMEOUT_SECONDS=8`

Optional email text:
- `OTP_EMAIL_SUBJECT=Vivian Loyalty Verification Code`
- `OTP_EMAIL_BODY_TEMPLATE=Your Vivian Loyalty verification code is {otp}. It expires in 5 minutes.`

Optional password reset email text (used by `/api/auth/password-reset/*`):
- `PWD_RESET_EMAIL_SUBJECT=Vivian Cosmetic Shop Password Reset Code`
- `PWD_RESET_EMAIL_BODY_TEMPLATE=Your Vivian Cosmetic Shop password reset code is {otp}. It expires in 5 minutes.`

Notes:
- Verify the sender (`SMTP_FROM`) in SendGrid (Single Sender or Domain Authentication), otherwise SendGrid will reject the email.
- Keep secrets (`SENDGRID_API_KEY` / `SMTP_PASSWORD`) in Render Environment only, never in the repo.

## 4) Initialize the database schema (first deploy only)

This project uses `db.create_all()` for initial schema.

Options:
- If Render provides a **Shell** for the service, run:
  - `python database/init_db.py`
  - (optional) `python database/insert_tiers.py`

If there is no Shell, you can temporarily run a one-off deploy with:
- Add env var `RUN_SCHEMA_PATCH_ON_STARTUP=true` (optional)
- Or run the init scripts locally against the Render database by setting `DATABASE_URL` locally.

## 5) Verify

- Health check:
  - `https://<your-render-service>.onrender.com/api/health`

## Notes

- Do **not** commit `.env`. The repo `.gitignore` already excludes it.
- For Render Postgres, external connections usually require SSL (`sslmode=require`).
  Internal URLs on Render typically work without extra parameters.
