from app.db.engine import engine
from app.db.base import Base
from app.db import models  # noqa: F401 (important for model registration)

"""
Database initialization script.

This script:
- Imports all ORM models to ensure they are registered with SQLAlchemy
- Creates database tables based on model metadata
- Is typically run once during initial setup or development
"""


def main():
    """
    Create all database tables defined in SQLAlchemy models.

    SQLAlchemy inspects Base.metadata (populated by imported models)
    and generates the corresponding tables in the configured database.
    """
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")


# Entry point when running the script directly
if __name__ == "__main__":
    main()
