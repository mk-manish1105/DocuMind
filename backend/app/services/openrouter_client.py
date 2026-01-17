import requests
import json
from typing import List, Dict, Generator
from app.core.config import settings

"""
Streaming client for OpenRouter / Groq-compatible chat APIs.

This implementation handles:
- Chunked JSON streaming (NOT Server-Sent Events)
- Incremental token extraction from partial responses
- Graceful handling of API, timeout, and network errors
"""

# Standard authorization and content headers
HEADERS = {
    "Authorization": f"Bearer {settings.LLAMA_API_KEY}",
    "Content-Type": "application/json",
}


def stream_openrouter_chat(
    messages: List[Dict],
    max_tokens: int = 500,
    temperature: float = 0.6,
) -> Generator[str, None, None]:
    """
    Stream chat responses from a Groq/OpenRouter-compatible API.

    - Uses HTTP chunked transfer encoding instead of SSE
    - Buffers partial chunks until complete JSON lines are formed
    - Yields incremental text content suitable for real-time UI rendering
    """

    # Request payload following chat completion schema
    payload = {
        "model": settings.LLAMA_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": True,
    }

    try:
        # Open streaming POST request to the model API
        with requests.post(
            settings.LLAMA_API_URL,
            headers=HEADERS,
            json=payload,
            stream=True,
            timeout=(10, 300),
        ) as r:

            # Handle non-successful HTTP responses early
            if r.status_code != 200:
                yield f"⚠️ LLM error ({r.status_code})"
                return

            buffer = ""

            # Read raw streamed byte chunks
            for chunk in r.iter_content(chunk_size=None):
                if not chunk:
                    continue

                # Accumulate bytes until full JSON lines are available
                buffer += chunk.decode("utf-8")

                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        # Parse each JSON line and extract incremental content
                        data = json.loads(line)
                        delta = data["choices"][0].get("delta", {}).get("content")
                        if delta:
                            yield delta
                    except Exception:
                        # Ignore malformed or partial JSON fragments
                        continue

    except requests.exceptions.Timeout:
        # Timeout while waiting for streamed response
        yield "LLM request timed out."
    except requests.exceptions.RequestException:
        # Generic network or connection error
        yield "LLM network error."
