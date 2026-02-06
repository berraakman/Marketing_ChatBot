import requests
from backend.config import (
    OLLAMA_BASE,
    LOCAL_CHAT_MODEL,
    CLOUD_CHAT_MODEL,
    EMBED_MODEL,
    EXPECTED_EMBED_DIM
)
import json
from typing import List, Dict

# ===============================
# Internal Ollama chat helper
# ===============================
def _ollama_chat(model: str, messages: List[Dict[str, str]], temperature: float) -> str:
    if not messages or not isinstance(messages, list):
        raise ValueError("messages must be a non-empty list")

    payload = {
        "model": model,
        "messages": messages,
        "options": {"temperature": temperature},
        "stream": False,
    }

    try:
        response = requests.post(
            f"{OLLAMA_BASE}/api/chat",
            json=payload,
            timeout=120
        )
        response.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Ollama chat request failed: {e}")

    data = response.json()
    if "message" not in data or "content" not in data["message"]:
        raise RuntimeError("Unexpected Ollama response format")

    return data["message"]["content"]

# ===============================
# Marketing / booth assistant
# (cloud / large model)
# ===============================
def marketing_chat(messages: List[Dict[str, str]]) -> str:
    return _ollama_chat(
        model=CLOUD_CHAT_MODEL,
        messages=messages,
        temperature=0.4
    )

# ===============================
# RAG final answer
# (local / deterministic model)
# ===============================
def rag_chat(messages: List[Dict[str, str]]) -> str:
    return _ollama_chat(
        model=LOCAL_CHAT_MODEL,
        messages=messages,
        temperature=0.1
    )

# ===============================
# Embeddings for RAG
# ===============================
def embed(text: str) -> List[float]:
    if not text or not isinstance(text, str):
        raise ValueError("text must be a non-empty string")

    payload = {
        "model": EMBED_MODEL,
        "prompt": text
    }

    try:
        response = requests.post(
            f"{OLLAMA_BASE}/api/embeddings",
            json=payload,
            timeout=60
        )
        response.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Ollama embedding request failed: {e}")

    embedding = response.json()["embedding"]

    if EXPECTED_EMBED_DIM is not None and len(embedding) != EXPECTED_EMBED_DIM:
        import logging
        logging.warning(
            f"Embedding dimension changed for model '{EMBED_MODEL}': "
            f"expected {EXPECTED_EMBED_DIM}, got {len(embedding)}. "
            "Proceeding with new dimension."
        )

    return embedding

# ===============================
# Semantic section extraction
# ===============================
def semantic_extractor(text: str) -> Dict[str, str]:
    """
    Extract Problem / Solution / Product / Value Proposition
    from unstructured text using an LLM.
    """
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

    response = _ollama_chat(
        model=LOCAL_CHAT_MODEL,
        messages=messages,
        temperature=0.0
    )

    try:
        return json.loads(response)
    except Exception:
        return {
            "problem": "",
            "solution": "",
            "product": "",
            "value_proposition": ""
        }