from typing import List, Dict, Optional
from backend.dispatchers.base import load_marketing_prompt
from backend.llm import marketing_chat


def dispatch(
    question: str,
    history: Optional[List[Dict[str, str]]] = None,
    context: Optional[dict] = None
):
    if not question or not isinstance(question, str):
        raise ValueError("question boş veya geçersiz")

    history = history or []

    if not isinstance(history, list):
        raise ValueError("history list tipinde olmalı")

    messages = [
        {"role": "system", "content": load_marketing_prompt("ar")},
        *history,
        {"role": "user", "content": question}
    ]

    return marketing_chat(messages)