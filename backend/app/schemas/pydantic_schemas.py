from pydantic import BaseModel, EmailStr
from typing import Optional

"""
Pydantic schemas used for request validation and response serialization.

These schemas:
- Validate incoming API payloads
- Define response shapes sent to the client
- Act as a clean contract between frontend and backend
"""

# ------------------------
# AUTH & USER SCHEMAS
# ------------------------
class UserCreate(BaseModel):
    """
    Payload for user registration.
    Used when creating a new user account.
    """
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    """
    Payload for user login.
    Validates user credentials before authentication.
    """
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """
    Response returned after successful authentication.
    Contains the access token and token type.
    """
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """
    Public user representation returned by the API.
    Excludes sensitive fields such as passwords.
    """
    id: int
    email: EmailStr
    full_name: Optional[str]

    class Config:
        # Enables compatibility with SQLAlchemy ORM objects
        from_attributes = True


# ------------------------
# CHAT SCHEMAS
# ------------------------
class ChatRequest(BaseModel):
    """
    Payload for sending a chat message.

    - `question`: user input text
    - `session_id`: optional chat session identifier (for continuing a conversation)
    - `max_tokens`: optional limit to control response length
    """
    question: str
    session_id: Optional[int] = None
    max_tokens: Optional[int] = 500
