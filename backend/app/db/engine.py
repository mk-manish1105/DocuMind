from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

"""
Database engine and session factory setup.

This module:
- Loads database configuration from environment variables
- Initializes the SQLAlchemy engine
- Provides a reusable session factory for database access
"""

# Load environment variables from .env into process environment
load_dotenv()

# Read database connection URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Fail fast if database configuration is missing
    raise RuntimeError("DATABASE_URL not found in environment")

# Create SQLAlchemy engine.
# `future=True` enables SQLAlchemy 2.0 style behavior.
# `echo=False` disables SQL query logging (enable for debugging).
engine = create_engine(
    DATABASE_URL,
    echo=False,
    future=True
)

# SQLAlchemy session factory.
# - autocommit=False ensures explicit transaction control
# - autoflush=False prevents automatic flushes before queries
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)
