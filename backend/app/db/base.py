from sqlalchemy.orm import DeclarativeBase

"""
Base class for all SQLAlchemy ORM models.

All database models in the application should inherit from this Base
to ensure consistent metadata handling and ORM behavior.
"""

class Base(DeclarativeBase):
    """
    Declarative base for SQLAlchemy models.

    This class serves as the common parent for all ORM model classes.
    SQLAlchemy uses it to collect table metadata and mappings.
    """
    pass
