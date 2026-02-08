from typing import List, Dict, Optional
from backend.dispatchers.base import load_marketing_prompt
from backend.llm import marketing_chat


def dispatch(
    question: str,
    history: Optional[List[Dict[str, str]]] = None,
    context: Optional[str] = None
):
    """
    English (en) marketing dispatcher.
    """
    if not question or not isinstance(question, str):
        raise ValueError("question boş veya geçersiz")

    history = history or []

    if not isinstance(history, list):
        raise ValueError("history list tipinde olmalı")

    messages = [
        {"role": "system", "content": load_marketing_prompt("en")}
    ]

    # Inject retrieved context with clear instructions
    if context:
        messages.append(
            {
                "role": "system",
                "content": (
                    "Use the following context to answer the user's question. "
                    "Answer based on whatever relevant information is available. "
                    "Only say you lack information if the context contains nothing relevant.\n\n"
                    f"Context:\n{context}"
                )
            }
        )
    else:
        # No context available - tell LLM to use general FundEd knowledge
        messages.append(
            {
                "role": "system",
                "content": (
                    "No specific document context was retrieved for this query. "
                    "Answer based on your general knowledge about FundEd as an education funding platform. "
                    "Keep your response helpful and brief."
                )
            }
        )

    messages.extend(history)
    messages.append({"role": "user", "content": question})

    return marketing_chat(messages)