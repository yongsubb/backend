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


def get_sqlalchemy_engine_options(database_uri: str) -> dict:
    """Return SQLAlchemy engine options.

    Render/managed Postgres connections can be long-lived and occasionally get
    dropped, which then surfaces as SSL/EOF errors on the next query. Using
    `pool_pre_ping` and a modest `pool_recycle` makes connections more resilient.
    """

    uri = (database_uri or '').strip().lower()
    if not (uri.startswith('postgresql://') or uri.startswith('postgresql+')):
        return {}

    connect_args: dict = {}
    # If the URL doesn't specify sslmode, default to require in production.
    # (Render external URLs require SSL; internal URLs also support it.)
    if _is_production and 'sslmode=' not in uri:
        connect_args['sslmode'] = os.getenv('PGSSLMODE', 'require')

    recycle_seconds_raw = (os.getenv('DB_POOL_RECYCLE_SECONDS') or '180').strip()
    try:
        recycle_seconds = int(recycle_seconds_raw)
    except Exception:
        recycle_seconds = 180

    # Keep pool small on free tiers.
    pool_size_raw = (os.getenv('DB_POOL_SIZE') or '5').strip()
    max_overflow_raw = (os.getenv('DB_MAX_OVERFLOW') or '10').strip()
    try:
        pool_size = int(pool_size_raw)
    except Exception:
        pool_size = 5
    try:
        max_overflow = int(max_overflow_raw)
    except Exception:
        max_overflow = 10

    options = {
        'pool_pre_ping': True,
        'pool_recycle': max(30, recycle_seconds),
        'pool_size': max(1, pool_size),
        'max_overflow': max(0, max_overflow),
    }
    if connect_args:
        options['connect_args'] = connect_args
    return options

SQLALCHEMY_DATABASE_URI = get_sqlalchemy_database_uri()

SQLALCHEMY_ENGINE_OPTIONS = get_sqlalchemy_engine_options(SQLALCHEMY_DATABASE_URI)

SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_ECHO = os.getenv('DEBUG', 'False').lower() == 'true'
