from backend.config import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES
from typing import List, Dict

AUTO_PITCH_KEYWORDS = [
    "bu startup",
    "startup",
    "anlat",
    "özetle",
    "pitch",
    "what is this",
    "tell me about",
    "explain",
]


def is_greeting(text: str) -> bool:
    if not text or not isinstance(text, str):
        return False

    greetings = [
        "hi", "hello", "hey",
        "selam", "merhaba",
        "hallo", "guten",
        "مرحبا", "السلام"
    ]
    t = text.lower().strip()
    return any(t == g or t.startswith(g + " ") for g in greetings)


def detect_language(text: str) -> str:
    if not text or not isinstance(text, str):
        return DEFAULT_LANGUAGE

    t = text.lower()

    if any(w in t for w in ["hallo", "guten", "wie"]):
        return "de"
    if any(w in t for w in ["مرحبا", "كيف", "ما", "هل"]):
        return "ar"

    return DEFAULT_LANGUAGE


def detect_intent(text: str) -> str:
    if not text or not isinstance(text, str):
        return "qa"

    t = text.lower()

    if is_greeting(t):
        return "greeting"

    if any(k in t for k in AUTO_PITCH_KEYWORDS):
        return "auto_pitch"

    return "qa"


def default_router(question: str, history: List[Dict[str, str]]):
    if not question or not isinstance(question, str):
        return {}

    lang = detect_language(question)
    if lang not in SUPPORTED_LANGUAGES:
        lang = DEFAULT_LANGUAGE

    intent = detect_intent(question)

    if intent == "greeting" and not history:
        greetings = {
            "en": "Hi! I’m the FundEd marketing assistant. How can I help?",
            "de": "Hallo! Ich bin der FundEd Marketing-Assistent. Wie kann ich helfen?",
            "ar": "مرحبًا! أنا مساعد FundEd التسويقي. كيف يمكنني المساعدة؟"
        }
        return {
            "handled": True,
            "lang": lang,
            "intent": intent,
            "response": greetings.get(lang, greetings[DEFAULT_LANGUAGE])
        }

    return {
        "handled": False,
        "lang": lang,
        "intent": intent
    }