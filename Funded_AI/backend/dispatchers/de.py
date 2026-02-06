from typing import List, Dict, Optional
from backend.dispatchers.base import load_marketing_prompt
from backend.llm import marketing_chat


def dispatch(
    question: str,
    history: Optional[List[Dict[str, str]]] = None,
    context: Optional[str] = None
):
    """
    German (de) marketing dispatcher.
    """
    if not question or not isinstance(question, str):
        raise ValueError("question boş veya geçersiz")

    history = history or []

    if not isinstance(history, list):
        raise ValueError("history list tipinde olmalı")

    messages = [
        {"role": "system", "content": load_marketing_prompt("de")}
    ]

    # Inject retrieved context (if any) as a system message to ground the model
    if context:
        messages.append(
            {
                "role": "system",
                "content": f"Context (for grounding, do not quote verbatim):\n{context}"
            }
        )

    messages.extend(history)
    messages.append({"role": "user", "content": question})

    return marketing_chat(messages)