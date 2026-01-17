# app/services/llama_api.py

import requests
import json
from typing import List, Dict, Generator
from app.core.config import settings

"""
Streaming client for the language model API.

Responsibilities:
- Validate required configuration at startup
- Send chat-style requests to the external model API
- Stream partial responses token-by-token
- Gracefully handle API, timeout, and network errors
"""

# ----------------------------
# Validate configuration
# ----------------------------
# Fail fast if API key is missing to avoid runtime errors during requests.
if not settings.LLAMA_API_KEY:
    raise RuntimeError("LLAMA_API_KEY not set")

# API endpoint and model configuration
LLM_API_URL = settings.LLAMA_API_URL
LLM_MODEL = settings.LLAMA_MODEL

# Standard headers required for authenticated API access
HEADERS = {
    "Authorization": f"Bearer {settings.LLAMA_API_KEY}",
    "Content-Type": "application/json",
}


def stream_llama_response(
    messages: List[Dict],
    max_tokens: int = 500,
    temperature: float = 0.3,
) -> Generator[str, None, None]:
    """
    Stream a response from the language model API.

    - Sends a chat-style request with streaming enabled
    - Yields partial text chunks incrementally as they arrive
    - Designed to integrate with FastAPI StreamingResponse
    """

    # Request payload following chat completion schema
    payload = {
        "model": LLM_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": True,
    }

    try:
        # Open a streaming HTTP connection to the model API
        with requests.post(
            LLM_API_URL,
            headers=HEADERS,
            json=payload,
            stream=True,
            timeout=(10, 300),
        ) as r:

            # Handle non-successful responses explicitly
            if r.status_code != 200:
                try:
                    err = r.json()
                except Exception:
                    err = r.text
                yield f"LLM error: {err}"
                return

            # Iterate over streamed response lines
            for line in r.iter_lines():
                if not line:
                    continue

                decoded = line.decode("utf-8").strip()

                # Skip lines that do not follow streaming protocol
                if not decoded.startswith("data:"):
                    continue

                chunk = decoded.replace("data:", "").strip()

                # End-of-stream marker
                if chunk == "[DONE]":
                    break

                try:
                    # Parse streamed JSON chunk and extract incremental content
                    data = json.loads(chunk)
                    delta = data["choices"][0]["delta"].get("content")
                    if delta:
                        yield delta
                except Exception:
                    # Ignore malformed chunks and continue streaming
                    continue

    except requests.exceptions.Timeout:
        # Timeout while waiting for model response
        yield "LLM request timed out."
    except requests.exceptions.RequestException:
        # Generic network or connection error
        yield "Network error while contacting LLM."
