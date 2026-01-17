# utils_extraction.py

import os
import re
from pathlib import Path
from typing import List

"""
Text extraction and preprocessing utilities.

This module is responsible for:
- Extracting raw text from supported document formats (.txt, .pdf, .docx)
- Cleaning extracted text to remove noise and control characters
- Splitting text into overlapping chunks suitable for embeddings and retrieval
"""

# Attempt to load sentence-level splitter for higher-quality chunking
try:
    from sentence_splitter import SentenceSplitter
    splitter = SentenceSplitter(language='en')
except Exception:
    # Fallback when sentence_splitter is unavailable
    splitter = None

# External libraries for document parsing
from docx import Document as DocxDocument  # .docx support
import fitz  # PyMuPDF for .pdf support


def extract_text_from_file(filepath: str) -> str:
    """
    Extract raw text from a file based on its extension.

    Supported formats:
    - .txt   : plain text files
    - .pdf   : parsed using PyMuPDF
    - .docx  : parsed using python-docx

    Returns extracted text or an empty string on failure.
    """

    ext = os.path.splitext(filepath)[1].lower()

    try:
        if ext == ".txt":
            # Read text file with UTF-8 fallback handling
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()

        elif ext == ".pdf":
            # Extract text from each PDF page
            text = []
            with fitz.open(filepath) as doc:
                for page in doc:
                    try:
                        page_text = page.get_text()
                    except Exception:
                        # Fallback for older PyMuPDF versions
                        page_text = page.get_text("text") if hasattr(page, "get_text") else ""
                    if page_text:
                        text.append(page_text)
            return "\n".join(text)

        elif ext == ".docx":
            # Extract text from Word document paragraphs
            doc = DocxDocument(filepath)
            return "\n".join([para.text for para in doc.paragraphs])

        else:
            # Unsupported file type
            print(f"[WARN] Skipping unsupported file type: {filepath}")
            return ""

    except Exception as e:
        # Fail gracefully on parsing errors
        print(f"[ERROR] Failed to extract text from {filepath}: {e}")
        return ""


def clean_text(text: str) -> str:
    """
    Perform basic text normalization and cleanup.

    - Removes extra whitespace and control characters
    - Normalizes newlines
    - Retains readable punctuation and structure
    """

    if not text:
        return ""

    text = text.replace('\u00A0', ' ')                      # Replace non-breaking spaces
    text = re.sub(r"[ \t]+", " ", text)                    # Collapse multiple spaces/tabs
    text = re.sub(r"[\r\n]{2,}", "\n", text)               # Collapse multiple newlines
    # Remove most non-printable Unicode characters
    text = re.sub(r"[^\x09\x0A\x0D\x20-\x7E]+", "", text)

    return text.strip()


def chunk_text(text: str, chunk_size: int = 300, overlap: int = 50) -> List[str]:
    """
    Split cleaned text into overlapping chunks.

    Strategy:
    - Prefer sentence-level splitting when available
    - Fallback to newline / punctuation-based splitting
    - Combine tokens into fixed-size overlapping chunks

    Parameters:
    - chunk_size: target number of tokens per chunk
    - overlap: number of tokens shared between consecutive chunks

    Returns a list of chunk strings.
    """

    if not text or not text.strip():
        return []

    # Attempt sentence-level splitting for better semantic coherence
    if splitter:
        try:
            sentences = splitter.split(text)
        except Exception:
            sentences = None
    else:
        sentences = None

    if not sentences or len(sentences) <= 1:
        # Fallback: split on newlines and sentence boundaries
        parts = []
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            if len(line) > 500:
                # Further split very long lines on sentence boundaries
                parts.extend(re.split(r'(?<=\.)\s+', line))
            else:
                parts.append(line)
        sentences = [p for p in parts if p.strip()]

    # Final cleanup of sentence list
    sentences = [s.strip() for s in sentences if s and s.strip()]

    chunks = []
    current_tokens = []

    # Build overlapping chunks by token count
    for sentence in sentences:
        tokens = sentence.split()
        if not tokens:
            continue
        current_tokens.extend(tokens)

        while len(current_tokens) >= chunk_size:
            chunk_tokens = current_tokens[:chunk_size]
            chunks.append(" ".join(chunk_tokens).strip())
            # Retain overlap tokens for next chunk
            current_tokens = current_tokens[chunk_size - overlap:]

    # Flush remaining tokens
    if current_tokens:
        chunks.append(" ".join(current_tokens).strip())

    # Deduplicate near-identical chunks while preserving order
    seen = set()
    unique_chunks = []
    for c in chunks:
        if c and c not in seen:
            unique_chunks.append(c)
            seen.add(c)

    return unique_chunks


def extract_and_chunk_documents(
    documents_path: str,
    chunk_size: int,
    chunk_overlap: int
) -> List[str]:
    """
    Extract, clean, and chunk all supported documents in a directory.

    - Walks the directory recursively
    - Processes .txt, .pdf, and .docx files
    - Logs progress and summary statistics

    Returns a list of all generated chunks.
    """

    all_chunks = []
    total_documents = 0

    for root, _, files in os.walk(documents_path):
        for fname in files:
            if fname.lower().endswith((".txt", ".pdf", ".docx")):
                fpath = os.path.join(root, fname)
                raw_text = extract_text_from_file(fpath)
                clean = clean_text(raw_text)

                if clean.strip():
                    total_documents += 1
                    chunks = chunk_text(clean, chunk_size, chunk_overlap)
                    all_chunks.extend(chunks)
                    print(f"[OK] {fname} → {len(chunks)} chunks")
                else:
                    print(f"[SKIP] {fname} → No clean text extracted")

    print(f"\nTotal documents processed: {total_documents}")
    print(f"Total chunks generated: {len(all_chunks)}")

    return all_chunks
