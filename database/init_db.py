"""
Database initialization script
Run this after creating the database to seed initial data
"""
from app import create_app

from database.bootstrap import ensure_schema_and_seed


def init_database() -> None:
    """Initialize database with tables and seed data."""
    print("Initializing database...")
    app = create_app()
    with app.app_context():
        ensure_schema_and_seed(seed_sample_data=True)
    print("Database initialization completed")
                    category_id=cat_id,
                    low_stock_threshold=10
                )
                db.session.add(product)
                print(f"  ✓ Product '{name}' created")
            else:
                print(f"  - Product '{name}' already exists")
    
    db.session.commit()


def init_db():
    """Initialize database with default data"""
    with app.app_context():
        print("\n" + "="*50)
        print("Vivian Cosmetic Shop - Database Initialization")
        print("="*50 + "\n")
        
        # Create tables
        print("Creating database tables...")
        db.create_all()
        print("  ✓ Tables created\n")
        
        # Seed data
        seed_users()
        print()
        seed_categories()
        print()
        seed_products()
        
        print("\n" + "="*50)
        print("Database initialization complete!")
        print("="*50)
        print("\nDefault login credentials:")
        print("  Supervisor: admin / admin123 (PIN: 1234)")
        print("  Cashier: cashier1 / cashier123")
        print()


if __name__ == '__main__':
    init_db()
