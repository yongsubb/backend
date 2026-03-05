"""Database initialization entrypoint.

Used by Render as `releaseCommand` and for local one-off setup.
Operations are idempotent.
"""

from __future__ import annotations

from app import create_app
from database.bootstrap import ensure_schema_and_seed


def init_database(*, seed_sample_data: bool = True) -> None:
    print("Initializing database...")
    app = create_app()
    with app.app_context():
        ensure_schema_and_seed(seed_sample_data=seed_sample_data)
    print("Database initialization completed")


if __name__ == '__main__':
    init_database(seed_sample_data=True)
