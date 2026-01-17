# main.py
"""
Application entry point for the DocuMind API.

This module:
- Initializes the FastAPI application
- Configures global middleware (CORS)
- Registers all API routers
- Exposes a simple health check endpoint
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.auth import router as auth_router
from app.api.files import router as files_router
from app.api.chat import router as chat_router

# Create FastAPI application instance
app = FastAPI(title="DocuMind API")

# ---------------------------------------------------------------------
# CORS Configuration
# ---------------------------------------------------------------------
# Enables frontend applications (e.g., web clients) to interact with this API.
# During development, allowing all origins is acceptable.
# In production, this should be restricted to trusted frontend domains.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # DEV ONLY: replace with specific frontend origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # Expose custom response headers so browser-based clients can access them
    # (used for returning chat session identifiers)
    expose_headers=["X-Session-Id"],
)

# ---------------------------------------------------------------------
# API Routers
# ---------------------------------------------------------------------
# Register modular route groups for authentication, file handling, and chat
app.include_router(auth_router)
app.include_router(files_router)
app.include_router(chat_router)

# ---------------------------------------------------------------------
# Health Check Endpoint
# ---------------------------------------------------------------------
# Simple endpoint used for uptime monitoring and deployment validation
@app.get("/health")
def health():
    return {"status": "ok"}
