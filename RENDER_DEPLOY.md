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
- **Root Directory**: `vivian_cosmetic_shop_application/backend`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn wsgi:app --bind 0.0.0.0:$PORT`

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
