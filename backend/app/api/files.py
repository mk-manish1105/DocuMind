# app/api/files.py
"""
File upload and document management endpoints.

Responsibilities:
- Handle multipart file uploads and persist file metadata to the database.
- Offload heavy processing (text extraction, chunking, embeddings, FAISS index build)
  to a background task to keep the request non-blocking.
- Provide endpoints to list and delete user documents.
- Ensure index/chunk state is rebuilt after deletions to keep retrieval consistent.
"""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pathlib import Path
from fastapi import BackgroundTasks
from app.db.engine import SessionLocal
from app.db.models import Document
from app.api.auth import get_current_user
from app.utils.file_utils import get_user_dirs, save_upload_file, delete_file_safe
from app.services.retriever_service import (
    load_chunks, save_chunks, build_faiss_index
)
from app.services.embeddings import embedding_service
from app.utils_extraction import extract_text_from_file, clean_text, chunk_text

router = APIRouter(prefix="/files", tags=["files"])

# ---------------------------------------------------------------------
# DB session dependency
# Creates a new SQLAlchemy session per request and ensures proper cleanup.
# ---------------------------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------------------
# BACKGROUND PROCESSOR
# ---------------------------
def process_uploaded_files(
    user_id: int,
    files: list[str],
):
    """
    Background task that:
    - Reads uploaded files from the user's uploads directory
    - Extracts and cleans text
    - Produces text chunks suitable for retrieval/embedding
    - Merges with existing chunks and persists them
    - Builds/updates the FAISS index (heavy CPU work moved off the request thread)
    """

    dirs = get_user_dirs(user_id)
    uploads_dir = dirs["uploads"]
    index_dir = dirs["index"]

    all_new_chunks = []

    # Iterate uploaded filenames and extract textual content
    for filename in files:
        file_path = uploads_dir / filename

        raw = extract_text_from_file(str(file_path))
        cleaned = clean_text(raw)
        chunks = chunk_text(cleaned)

        if chunks:
            all_new_chunks.extend(chunks)

    # If no new chunks were produced, nothing to do
    if not all_new_chunks:
        return

    # Merge with any existing chunks and persist
    chunk_path = index_dir / "chunk_texts.pkl"
    existing = load_chunks(chunk_path)
    merged = existing + all_new_chunks
    save_chunks(chunk_path, merged)

    # Build or rebuild the FAISS index using the merged chunks.
    # This is intentionally a heavy, synchronous CPU task executed in the background.
    build_faiss_index(merged, index_dir / "faiss.index")


# ---------------------------
# UPLOAD FILES (NON-BLOCKING)
# ---------------------------
@router.post("/upload")
async def upload_files(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Accept multiple uploaded files, save them to storage, record Document rows,
    and schedule background processing (extraction, chunking, index build).
    - The request returns immediately while the heavy processing runs in the background.
    """

    dirs = get_user_dirs(current_user.id)
    uploads_dir = dirs["uploads"]

    saved_filenames = []

    # Persist file to disk and record a Document entry per file synchronously.
    for f in files:
        file_path = uploads_dir / f.filename
        save_upload_file(f, file_path)

        doc = Document(
            user_id=current_user.id,
            filename=f.filename,
            file_path=str(file_path)
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        saved_filenames.append(f.filename)

    # Schedule the CPU-bound processing after the response is returned.
    background_tasks.add_task(
        process_uploaded_files,
        current_user.id,
        saved_filenames
    )

    return {
        "message": f"{len(files)} files uploaded successfully. Processing started."
    }

# ---------------------------
# LIST USER DOCUMENTS
# ---------------------------
@router.get("/list")
def list_documents(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Return non-deleted documents for the authenticated user.
    The response includes basic metadata used by the frontend.
    """
    docs = (
        db.query(Document)
        .filter(Document.user_id == current_user.id, Document.is_deleted == False)
        .all()
    )
    return [
        {
            "id": d.id,
            "filename": d.filename,
            "uploaded_at": d.uploaded_at
        }
        for d in docs
    ]

# ---------------------------
# DELETE DOCUMENT
# ---------------------------
@router.delete("/{document_id}")
def delete_document(
    document_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a user's document:
    - Remove file from storage (safe-delete utility)
    - Mark document as deleted in DB (soft delete)
    - Rebuild the chunk store and FAISS index from remaining documents so retrieval stays consistent
    """

    # Ensure the document belongs to the current user
    doc = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.user_id == current_user.id
        )
        .first()
    )

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Remove the file from disk (safe delete that tolerates missing files)
    delete_file_safe(Path(doc.file_path))

    # Soft-delete in DB so history is preserved if needed
    doc.is_deleted = True
    db.commit()

    # Rebuild FAISS index and chunk store from all remaining (non-deleted) documents.
    # This ensures the retrieval index reflects the current set of user documents.
    dirs = get_user_dirs(current_user.id)
    index_dir = dirs["index"]
    chunk_path = index_dir / "chunk_texts.pkl"

    all_chunks = []
    for d in (
        db.query(Document)
        .filter(Document.user_id == current_user.id, Document.is_deleted == False)
        .all()
    ):
        raw = extract_text_from_file(d.file_path)
        cleaned = clean_text(raw)
        all_chunks.extend(chunk_text(cleaned))

    save_chunks(chunk_path, all_chunks)
    build_faiss_index(all_chunks, index_dir / "faiss.index")

    return {"message": "Document deleted successfully"}
