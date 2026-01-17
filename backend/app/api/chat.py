# app/api/chat.py
"""
Chat endpoints and streaming response handling.

Responsibilities:
- Create or continue chat sessions (authenticated users)
- Support guest users (no DB persistence, no document context)
- Perform document retrieval for authenticated users (via FAISS)
- Build prompts with optional document context
- Stream model responses back to the client and persist assistant replies
"""

from typing import Optional
import json
import re
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.engine import SessionLocal
from app.db.models import ChatSession, ChatMessage, User
from app.api.auth import get_current_user_optional
from app.services.llama_api import stream_llama_response
from app.services.retriever_service import load_faiss_index, load_chunks
from app.services.embeddings import embedding_service
from app.utils.file_utils import get_user_dirs
from app.schemas.pydantic_schemas import ChatRequest

router = APIRouter(prefix="/chat", tags=["chat"])

# ---------------------------------------------------------------------
# DB session dependency
# Provides a new SQLAlchemy session per request and ensures cleanup.
# ---------------------------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ----------------------------
# CREATE / CONTINUE CHAT
# ----------------------------
@router.post("")
async def chat(
    data: ChatRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """
    Handle a chat request. Two major flows:
    - Guest user: `current_user` will be None. No DB persistence, no document context.
    - Authenticated user: persist messages and sessions, and use document retrieval.
    """

    # Basic inputs from request
    question = data.question
    session_id = data.session_id
    # Cap tokens to a safe maximum
    max_tokens = min(data.max_tokens, 1600)

    # Variables used for persistence (only set when authenticated)
    persisted_session_id = None
    persisted_user_id = None

    # ----------------------------
    # AUTHENTICATED USER FLOW
    # ----------------------------
    if current_user:
        persisted_user_id = current_user.id

        # ----- session selection / creation (robust) -----
        session = None

        # If client provided a session_id, try to load that session for this user.
        if session_id:
            try:
                sid = int(session_id)
                session = (
                    db.query(ChatSession)
                    .filter(
                        ChatSession.id == sid,
                        ChatSession.user_id == current_user.id,
                    )
                    .first()
                )
            except Exception:
                # If parsing / lookup fails, fallback to creating a new session.
                session = None

        # Create a new session if none exists (we keep title empty to set later)
        if not session:
            session = ChatSession(user_id=current_user.id, title="")
            db.add(session)
            db.commit()
            db.refresh(session)

        persisted_session_id = session.id

        # Persist the incoming user message immediately so it appears in history.
        db.add(
            ChatMessage(
                session_id=persisted_session_id,
                user_id=persisted_user_id,
                role="user",
                content=question,
            )
        )
        db.commit()

        # --- Set session title from first user message if not already set
        # We derive a compact, clean title from the first non-empty line of the question.
        # Remove code blocks and simple markdown characters to make it readable.
        if not session.title or not session.title.strip():
            if question and question.strip():
                raw = question.strip()
                first_line = ""
                for line in raw.splitlines():
                    if line.strip():
                        first_line = line.strip()
                        break

                # remove triple-backtick code blocks and simple markdown noise
                first_line = re.sub(r'```[\s\S]*?```', '', first_line)
                first_line = re.sub(r'[`*_>#~-]+', '', first_line)
                clean_title = re.sub(r'\s+', ' ', first_line).strip()[:60]

                if clean_title:
                    session.title = clean_title
                    db.commit()
                    db.refresh(session)


    # ----------------------------
    # DOCUMENT RETRIEVAL (AUTH ONLY)
    # ----------------------------
    # Build context_text only for authenticated users with valid FAISS index/chunks.
    context_text = ""

    if current_user:
        dirs = get_user_dirs(current_user.id)
        index_dir = dirs["index"]
        faiss_index = load_faiss_index(index_dir / "faiss.index")
        chunks = load_chunks(index_dir / "chunk_texts.pkl")

        # If we have both index and chunks, run retrieval and build a short context.
        if faiss_index and chunks:
            q_emb = embedding_service.embed_query(question)
            D, I = faiss_index.search(q_emb, 3)
            print("FAISS scores:", D[0])

            # Use the top similarity score to decide whether there is relevant context.
            top_score = float(D[0][0])

            # If top score is below threshold, treat as no context.
            if top_score < 0.80:
                context_text = ""
            else:
                # Conservative similarity threshold for including individual chunks.
                SIM_THRESHOLD = 0.78
                for score, idx in zip(D[0], I[0]):
                    if score >= SIM_THRESHOLD and 0 <= idx < len(chunks):
                        context_text += chunks[idx] + "\n\n"

    # Truncate final context to a safe token/length budget for the model.
    context_text = context_text[:4000]

    # ----------------------------
    # BUILD PROMPT
    # ----------------------------
    # System message encodes answer style rules and explicit instructions for
    # how to use document context when present.
    messages = [
        {
            "role": "system",
            "content": (
                "You are DocuMind, an intelligent AI tutor and assistant.\n\n"

                "Answer style rules (VERY IMPORTANT):\n"

                "- If the topic is broad or tutorial-style, give a concise, complete SUMMARY instead of full detail.\n"
                "- Never start a code example unless it can be finished.\n"
                "- Prefer overview + small examples over long tutorials.\n"
                "- Never cut a sentence or code block mid-way.\n"

                "- Be concise but thorough.\n"
                "- Prefer clear structure: headings, bullet points, short paragraphs.\n"
                "- Avoid unnecessary verbosity.\n"
                "- End answers naturally (no abrupt stops).\n\n"

                "When DOCUMENT CONTEXT is provided:\n"
                "- Use it ONLY if it is clearly relevant to the question.\n"
                "- If the answer is found in the document, use it.\n"
                "- If the document does not contain the answer, ignore it and answer normally.\n"
                "- Never fabricate or assume facts from the document.\n"
            ),
        }
    ]


    # If we have document context, present it as part of the user message with an explicit instruction.
    if context_text.strip():
        messages.append(
            {
                "role": "user",
                "content": (
                    "DOCUMENT CONTEXT:\n"
                    f"{context_text}\n\n"
                    "QUESTION:\n"
                    f"{question}\n\n"
                    "If the document context is relevant, answer using it."
                ),
            }
        )
    else:
        # No document context: use the plain user question.
        messages.append(
            {
                "role": "user",
                "content": question
            }
        )

    # ----------------------------
    # STREAMING RESPONSE
    # ----------------------------
    # We stream tokens from the model to the client and capture the full assistant text.
    def event_stream():
        assistant_text = ""

        # stream_llama_response yields incremental tokens
        for token in stream_llama_response(messages, max_tokens=max_tokens):
            assistant_text += token
            # Each chunk sent as newline-delimited JSON for NDJSON streaming clients
            yield json.dumps({"content": token}) + "\n"

        # After stream completes, persist assistant reply when session/user exist
        if persisted_session_id and persisted_user_id:
            db2 = SessionLocal()
            try:
                db2.add(
                    ChatMessage(
                        session_id=persisted_session_id,
                        user_id=persisted_user_id,
                        role="assistant",
                        content=assistant_text,
                    )
                )
                db2.commit()
            finally:
                db2.close()

    # Include session id header so client can associate streamed replies with a session
    headers = {}
    if persisted_session_id:
        headers["X-Session-Id"] = str(persisted_session_id)

    return StreamingResponse(
        event_stream(),
        media_type="application/x-ndjson",
        headers=headers
    )

# ----------------------------
# LIST CHAT SESSIONS
# ----------------------------
@router.get("/sessions")
def list_sessions(
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """
    Return recent chat sessions for an authenticated user.
    Guests receive an empty list.
    """
    if not current_user:
        return []

    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.created_at.desc())
        .all()
    )

    return [
        {
            "id": s.id,
            "created_at": s.created_at,
            "title": s.title,
        }
        for s in sessions
    ]


# ----------------------------
# GET CHAT HISTORY
# ----------------------------
@router.get("/history/{session_id}")
def get_history(
    session_id: int,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """
    Return ordered messages for a specific session belonging to the current user.
    Guests receive an empty list.
    """
    if not current_user:
        return []

    messages = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.session_id == session_id,
            ChatMessage.user_id == current_user.id,
        )
        .order_by(ChatMessage.created_at)
        .all()
    )

    return [
        {
            "role": m.role,
            "content": m.content,
            "created_at": m.created_at,
        }
        for m in messages
    ]
