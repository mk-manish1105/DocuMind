# app/api/auth.py
"""
Authentication and authorization routes.

Responsibilities:
- User registration
- User login (token generation)
- Current user retrieval via access token

This module follows OAuth2 password flow with bearer tokens.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import Optional

from app.db.engine import SessionLocal
from app.db.models import User
from app.schemas.pydantic_schemas import (
    UserCreate,
    TokenResponse,
    UserResponse
)
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token
)

# Router configuration for all auth-related endpoints
router = APIRouter(prefix="/auth", tags=["auth"])

# OAuth2 bearer token configuration.
# auto_error=False allows optional authentication in certain routes.
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login",
    auto_error=False
)

# ---------------------------------------------------------------------
# Database session dependency
# Creates a new DB session per request and ensures proper cleanup
# ---------------------------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------------------------------------------------------------
# Dependency: Get current authenticated user (REQUIRED)
# - Decodes access token
# - Fetches user from database
# - Raises 401 if token is invalid or user does not exist
# ---------------------------------------------------------------------
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    return user

# ---------------------------------------------------------------------
# Dependency: Get current user (OPTIONAL)
# - Used for endpoints that support both guest and authenticated users
# - Returns None if token is missing or invalid
# ---------------------------------------------------------------------
def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    if not token:
        return None

    user_id = decode_token(token)
    if not user_id:
        return None

    return db.query(User).filter(User.id == int(user_id)).first()

# ---------------------------------------------------------------------
# User Registration
# - Validates unique email
# - Hashes password before storing
# - Returns public user information
# ---------------------------------------------------------------------
@router.post("/register", response_model=UserResponse)
def register_user(
    data: UserCreate,
    db: Session = Depends(get_db)
):
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

# ---------------------------------------------------------------------
# User Login (OAuth2 Password Grant)
# - Verifies credentials
# - Issues JWT access token
# ---------------------------------------------------------------------
@router.post("/login", response_model=TokenResponse)
def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.email == form_data.username
    ).first()

    if not user or not verify_password(
        form_data.password,
        user.hashed_password
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    token = create_access_token(subject=str(user.id))
    return TokenResponse(
        access_token=token,
        token_type="bearer"
    )

# ---------------------------------------------------------------------
# Get current authenticated user
# - Protected route
# - Requires valid access token
# ---------------------------------------------------------------------
@router.get("/me", response_model=UserResponse)
def get_me(
    current_user: User = Depends(get_current_user)
):
    return current_user
