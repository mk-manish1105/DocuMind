from pathlib import Path
import shutil
import os

"""
File system utilities for managing user-specific storage.

This module:
- Defines a safe base directory for storing user data outside the codebase
- Creates per-user directory structures
- Provides helpers for saving and deleting files safely
"""

# -------------------------------------------------
# Store user data OUTSIDE the codebase
# -------------------------------------------------
# Keeping user data outside the project directory prevents:
# - Accidental deletion during redeployments
# - Auto-reload issues in development servers
# - Mixing application code with user-generated content

# Directory resolution priority:
# 1) Environment variable DOCUMIND_DATA_DIR
# 2) Fallback to a hidden directory in the user's home folder
BASE_DIR = Path(
    os.getenv("DOCUMIND_DATA_DIR", Path.home() / ".documind_data")
)


def get_user_dirs(user_id: int) -> dict:
    """
    Return directory paths for a specific user.

    Directory structure:
      BASE_DIR/
        └── <user_id>/
            ├── uploads/   -> raw uploaded files
            └── index/     -> embeddings, chunks, and FAISS index

    Directories are created if they do not already exist.
    """

    user_root = BASE_DIR / str(user_id)
    uploads = user_root / "uploads"
    index = user_root / "index"

    uploads.mkdir(parents=True, exist_ok=True)
    index.mkdir(parents=True, exist_ok=True)

    return {
        "root": user_root,
        "uploads": uploads,
        "index": index
    }


def save_upload_file(upload_file, destination: Path):
    """
    Save an uploaded file to disk safely.

    Uses stream-based copying to handle large files efficiently
    without loading the entire file into memory.
    """
    with destination.open("wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)


def delete_file_safe(path: Path):
    """
    Safely delete a file from disk.

    - Checks for existence before deletion
    - Silently ignores filesystem errors to avoid crashing the application
    """
    try:
        if path.exists():
            path.unlink()
    except Exception:
        # Avoid crashing on file system errors (permissions, race conditions, etc.)
        pass
