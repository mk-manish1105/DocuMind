from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from typing import Optional
from .config import settings

"""
Security utilities for authentication.

Responsibilities:
- Password hashing and verification
- JWT access token creation
- JWT token decoding and validation
"""

# Password hashing context using bcrypt.
# `deprecated="auto"` allows smooth upgrades of hashing schemes in the future.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ------------------------
# Password utilities
# ------------------------
def hash_password(password: str) -> str:
    """
    Hash a plain-text password using a secure one-way hashing algorithm.
    The returned hash is safe to store in the database.
    """
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verify a plain-text password against a previously hashed password.
    Returns True if the password matches, otherwise False.
    """
    return pwd_context.verify(plain, hashed)

# ------------------------
# JWT utilities
# ------------------------
def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a signed JWT access token.

    - `subject` typically represents the user identifier.
    - `expires_delta` optionally overrides the default expiration time.
    """

    # Use default expiration from settings if not explicitly provided
    if expires_delta is None:
        expires_delta = timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    # Token expiration timestamp (UTC)
    expire = datetime.utcnow() + expires_delta

    # Standard JWT payload
    payload = {
        "sub": subject,
        "exp": expire
    }

    # Encode and sign the JWT using configured secret and algorithm
    return jwt.encode(
        payload,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )


def decode_token(token: str) -> Optional[str]:
    """
    Decode and validate a JWT access token.

    - Returns the subject (`sub`) if the token is valid.
    - Returns None if the token is invalid or expired.
    """

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload.get("sub")
    except JWTError:
        # Covers invalid signature, expired token, or malformed payload
        return None
