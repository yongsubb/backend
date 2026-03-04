"""Database bootstrap helpers.

Used for:
- Render / managed Postgres first deploy (create tables + seed defaults)
- One-off initialization via `python database/init_db.py`

All operations are designed to be idempotent.
"""

from __future__ import annotations

from typing import Dict

from extensions import db
from models.user import User
from models.product import Product, Category


def seed_users() -> None:
    """Create default users (idempotent)."""

    # Admin
    if not User.query.filter_by(username="admin").first():
        admin = User(
            username="admin",
            first_name="Admin",
            last_name="User",
            password="admin123",
            role="supervisor",
            email="admin@viviancosmetics.com",
        )
        admin.set_pin("1234")
        db.session.add(admin)

    # Cashier
    if not User.query.filter_by(username="cashier1").first():
        cashier = User(
            username="cashier1",
            first_name="Maria",
            last_name="Santos",
            password="cashier123",
            role="cashier",
            email="cashier1@viviancosmetics.com",
        )
        db.session.add(cashier)

    db.session.commit()


def seed_categories() -> None:
    """Create default categories (idempotent)."""

    categories = [
        ("Lipstick", "Lipsticks and lip products", "lips", "#E91E63"),
        ("Foundation", "Foundation and base makeup", "face", "#F5E6DA"),
        ("Skincare", "Skincare products and treatments", "spa", "#4CAF50"),
        ("Eyeshadow", "Eye makeup products", "visibility", "#9C27B0"),
        ("Mascara", "Mascara and eye products", "remove_red_eye", "#2196F3"),
        ("Blush", "Blush and cheek products", "favorite", "#FF5722"),
        ("Perfume", "Fragrances and perfumes", "air", "#C9A24D"),
        ("Tools", "Makeup brushes and tools", "brush", "#607D8B"),
    ]

    for name, desc, icon, color in categories:
        if not Category.query.filter_by(name=name).first():
            db.session.add(
                Category(name=name, description=desc, icon=icon, color=color)
            )

    db.session.commit()


def _category_id_map() -> Dict[str, int]:
    mapping: Dict[str, int] = {}
    for c in Category.query.all():
        mapping[c.name] = c.id
    return mapping


def seed_products() -> None:
    """Create sample products (idempotent)."""

    # Ensure categories are present and we can map by name (don’t assume ID=1..N).
    seed_categories()
    cat_ids = _category_id_map()

    products = [
        ("LIP-001", "8901234567890", "Velvet Matte Lipstick - Rose", 150.00, 350.00, 50, "Lipstick"),
        ("LIP-002", "8901234567891", "Velvet Matte Lipstick - Nude", 150.00, 350.00, 45, "Lipstick"),
        ("LIP-003", "8901234567892", "Glossy Lip Shine - Pink", 100.00, 250.00, 30, "Lipstick"),
        ("FND-001", "8901234567893", "Flawless Foundation - Light", 250.00, 599.00, 25, "Foundation"),
        ("FND-002", "8901234567894", "Flawless Foundation - Medium", 250.00, 599.00, 20, "Foundation"),
        ("SKN-001", "8901234567895", "Hydrating Moisturizer", 200.00, 450.00, 40, "Skincare"),
        ("SKN-002", "8901234567896", "Vitamin C Serum", 350.00, 799.00, 15, "Skincare"),
        ("EYE-001", "8901234567897", "Eyeshadow Palette - Natural", 300.00, 699.00, 20, "Eyeshadow"),
        ("MAS-001", "8901234567898", "Volume Mascara - Black", 120.00, 299.00, 35, "Mascara"),
        ("BLU-001", "8901234567899", "Powder Blush - Coral", 100.00, 280.00, 28, "Blush"),
        ("PRF-001", "8901234567900", "Floral Eau de Parfum", 500.00, 1299.00, 10, "Perfume"),
        ("TLS-001", "8901234567901", "Professional Brush Set", 400.00, 899.00, 12, "Tools"),
    ]

    with db.session.no_autoflush:
        for sku, barcode, name, cost, price, stock, category_name in products:
            if Product.query.filter_by(sku=sku).first():
                continue

            category_id = cat_ids.get(category_name)
            if not category_id:
                # Should not happen if categories seeded correctly.
                continue

            db.session.add(
                Product(
                    sku=sku,
                    barcode=barcode,
                    name=name,
                    cost_price=cost,
                    selling_price=price,
                    stock_quantity=stock,
                    category_id=category_id,
                    low_stock_threshold=10,
                )
            )

    db.session.commit()


def ensure_schema_and_seed(*, seed_sample_data: bool = True) -> None:
    """Create tables and seed default data.

    Safe to run multiple times.
    """

    db.create_all()
    seed_users()
    if seed_sample_data:
        seed_products()
