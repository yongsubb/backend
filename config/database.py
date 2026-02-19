"""backend.config.database

Database configuration.

Default: MySQL (XAMPP) using DB_* variables.
Optional: Postgres (Render or elsewhere) by setting DATABASE_URL.

Notes for Render Postgres:
- Copy the "External Database URL" (for local dev) or "Internal Database URL"
  (for services running on Render private network) into DATABASE_URL.
- Render URLs may be `postgres://...`; SQLAlchemy expects `postgresql://...`.
"""
import os
from dotenv import load_dotenv

_is_production = os.getenv('FLASK_ENV', 'development') == 'production'
load_dotenv(override=(not _is_production))


def _normalize_database_url(url: str) -> str:
    url = url.strip()
    # Heroku/Render-style scheme alias + make driver explicit.
    # We prefer psycopg (v3) for better Windows/Python 3.13 wheel support.
    if url.startswith('postgres://'):
        return 'postgresql+psycopg://' + url[len('postgres://'):]
    if url.startswith('postgresql://'):
        return 'postgresql+psycopg://' + url[len('postgresql://'):]

    return url


def _build_mysql_uri() -> str:
    # MySQL Database Configuration (XAMPP)
    database_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 3306)),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', ''),  # Default XAMPP has no password
        'database': os.getenv('DB_NAME', 'vivian_cosmetic_shop'),
        'charset': 'utf8mb4',
    }

    return (
        f"mysql+pymysql://{database_config['user']}:{database_config['password']}"
        f"@{database_config['host']}:{database_config['port']}/{database_config['database']}"
        f"?charset={database_config['charset']}"
    )


def get_sqlalchemy_database_uri() -> str:
    """Return the SQLAlchemy DB URI.

    Priority:
    1) DATABASE_URL (Postgres on Render/managed DBs)
    2) DB_* vars (MySQL on XAMPP)
    """

    database_url = os.getenv('DATABASE_URL') or os.getenv('RENDER_DATABASE_URL')
    if database_url:
        return _normalize_database_url(database_url)

    return _build_mysql_uri()

SQLALCHEMY_DATABASE_URI = get_sqlalchemy_database_uri()

SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_ECHO = os.getenv('DEBUG', 'False').lower() == 'true'
