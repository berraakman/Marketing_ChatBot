import logging
from typing import List, Dict
from openai import OpenAI
from tenacity import (
    retry,
    stop_after_attempt,
    stop_after_delay,
    wait_exponential,
    retry_if_exception_type,
)
import tiktoken

from backend.config import (
    OPENAI_API_KEY,
    OPENAI_CHAT_MODEL,
    OPENAI_EMBED_MODEL,
    OPENAI_TIMEOUT,
    MAX_RESPONSE_TOKENS,
    EXPECTED_EMBED_DIM,
)

logger = logging.getLogger(__name__)

# Initialize OpenAI client
_client = None


def get_openai_client() -> OpenAI:
    """Get or create OpenAI client singleton."""
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=OPENAI_API_KEY,
            timeout=OPENAI_TIMEOUT,
            max_retries=0,  # We handle retries ourselves with tenacity
        )
    return _client


# ===============================
# Token counting utilities
# ===============================
def count_tokens(text: str, model: str = OPENAI_CHAT_MODEL) -> int:
    """Count tokens in text using tiktoken."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))


def count_messages_tokens(messages: List[Dict[str, str]], model: str = OPENAI_CHAT_MODEL) -> int:
    """Count tokens in a list of messages."""
    total = 0
    for msg in messages:
        total += count_tokens(msg.get("content", ""), model)
        total += 4  # overhead per message
    total += 2  # overhead for the conversation
    return total


# ===============================
# Retry decorator for API calls
# ===============================
@retry(
    stop=(stop_after_attempt(3) | stop_after_delay(90)),
    wait=wait_exponential(multiplier=1, min=2, max=15),
    retry=retry_if_exception_type((Exception,)),
    before_sleep=lambda retry_state: logger.warning(
        f"Retrying OpenAI call, attempt {retry_state.attempt_number}"
    ),
)
def _openai_chat_with_retry(
    model: str,
    messages: List[Dict[str, str]],
    temperature: float,
    max_tokens: int,
) -> str:
    """Make OpenAI chat completion with retry logic."""
    client = get_openai_client()
    
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=OPENAI_TIMEOUT,
    )
    
    if not response.choices:
        raise RuntimeError("OpenAI returned empty response")
    
    content = response.choices[0].message.content
    if content is None:
        raise RuntimeError("OpenAI returned null content")
    
    return content


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((Exception,)),
)
def _openai_embed_with_retry(text: str) -> List[float]:
    """Make OpenAI embedding request with retry logic."""
    client = get_openai_client()
    
    response = client.embeddings.create(
        model=OPENAI_EMBED_MODEL,
        input=text,
        timeout=OPENAI_TIMEOUT,
    )
    
    if not response.data:
        raise RuntimeError("OpenAI returned empty embedding response")
    
    return response.data[0].embedding


# ===============================
# Public API functions
# ===============================
def marketing_chat(messages: List[Dict[str, str]]) -> str:
    """Generate marketing response using cloud model."""
    if not messages or not isinstance(messages, list):
        raise ValueError("messages must be a non-empty list")
    
    return _openai_chat_with_retry(
        model=OPENAI_CHAT_MODEL,
        messages=messages,
        temperature=0.4,
        max_tokens=MAX_RESPONSE_TOKENS,
    )


def rag_chat(messages: List[Dict[str, str]]) -> str:
    """Generate RAG response using deterministic settings."""
    if not messages or not isinstance(messages, list):
        raise ValueError("messages must be a non-empty list")
    
    return _openai_chat_with_retry(
        model=OPENAI_CHAT_MODEL,
        messages=messages,
        temperature=0.1,
        max_tokens=MAX_RESPONSE_TOKENS,
    )


def embed(text: str) -> List[float]:
    """Generate embedding for text."""
    if not text or not isinstance(text, str):
        raise ValueError("text must be a non-empty string")
    
    # Truncate text if too long (max 8191 tokens for embedding models)
    max_chars = 30000
    if len(text) > max_chars:
        text = text[:max_chars]  # type: ignore[index]
        logger.warning(f"Truncated embedding input to {max_chars} characters")
    
    embedding = _openai_embed_with_retry(text)
    
    if EXPECTED_EMBED_DIM is not None and len(embedding) != EXPECTED_EMBED_DIM:
        logger.warning(
            f"Embedding dimension mismatch: expected {EXPECTED_EMBED_DIM}, got {len(embedding)}"
        )
    
    return embedding


def semantic_extractor(text: str) -> Dict[str, str]:
    """Extract structured startup sections from unstructured text."""
    messages = [
        {
            "role": "system",
            "content": (
                "You extract structured startup sections.\n"
                "Return JSON with keys:\n"
                "problem, solution, product, value_proposition.\n"
                "If missing, return empty string."
            )
        },
        {
            "role": "user",
            "content": text
        }
    ]
    
    try:
        response = _openai_chat_with_retry(
            model=OPENAI_CHAT_MODEL,
            messages=messages,
            temperature=0.0,
            max_tokens=500,
        )
        import json
        return json.loads(response)
    except Exception as e:
        logger.warning(f"Semantic extraction failed: {e}")
        return {
            "problem": "",
            "solution": "",
            "product": "",
            "value_proposition": ""
        }