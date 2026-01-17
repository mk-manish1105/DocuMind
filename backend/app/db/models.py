from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    Boolean,
    func
)
from sqlalchemy.orm import relationship
from .base import Base

"""
Database ORM models.

This module defines all SQLAlchemy models used by the application:
- User accounts
- Uploaded documents
- Chat sessions
- Individual chat messages

Relationships are explicitly defined to support cascading deletes
and consistent data cleanup.
"""

# ------------------------
# USER TABLE
# ------------------------
class User(Base):
    """
    Represents an application user.

    Each user can:
    - Upload multiple documents
    - Have multiple chat sessions
    """

    __tablename__ = "users"

    # Primary identifier
    id = Column(Integer, primary_key=True, index=True)

    # Authentication & profile fields
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)

    # Account creation timestamp (set by database)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    # Deleting a user cascades deletion to documents and chat sessions
    documents = relationship(
        "Document",
        back_populates="owner",
        cascade="all, delete"
    )
    sessions = relationship(
        "ChatSession",
        back_populates="user",
        cascade="all, delete"
    )


# ------------------------
# DOCUMENT TABLE
# ------------------------
class Document(Base):
    """
    Represents a user-uploaded document.

    Documents are soft-deleted using the `is_deleted` flag,
    allowing safe rebuilds of retrieval indexes without losing history.
    """

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)

    # Owner reference
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))

    # File metadata
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)

    # Upload timestamp
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    # Soft-delete flag (used instead of hard DB deletes)
    is_deleted = Column(Boolean, default=False)

    # Relationship back to owning user
    owner = relationship("User", back_populates="documents")


# ------------------------
# CHAT SESSION TABLE
# ------------------------
class ChatSession(Base):
    """
    Represents a logical chat session for a user.

    A session groups multiple chat messages and has a short,
    user-visible title derived from the first user message.
    """

    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)

    # Owning user
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))

    # Short title used in chat history UI
    title = Column(String(255), nullable=True)

    # Session creation timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="sessions")
    messages = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete"
    )


# ------------------------
# CHAT MESSAGE TABLE
# ------------------------
class ChatMessage(Base):
    """
    Represents a single message within a chat session.

    Messages are stored sequentially and include both user and assistant roles.
    """

    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)

    # References
    session_id = Column(Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))

    # Message role: "user" or "assistant"
    role = Column(String(20), nullable=False)

    # Message content (plain text or rendered markdown)
    content = Column(Text, nullable=False)

    # Message timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship back to parent session
    session = relationship("ChatSession", back_populates="messages")
