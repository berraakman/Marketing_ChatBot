import os

OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LOCAL_CHAT_MODEL = os.getenv("OLLAMA_LOCAL_MODEL", "llama3:latest")
CLOUD_CHAT_MODEL = os.getenv("OLLAMA_CLOUD_MODEL", "gpt-oss:120b-cloud")
EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
STARTUP_NAME = os.getenv("STARTUP_NAME", "FundEd - AI")

DOCS_DIR = "backend/data/docs"
CHROMA_DIR = "backend/data/chroma"

MIN_SIM = 0.50

SECTION_HEADERS = [
    "problem",
    "solution",
    "product",
    "how it works",
    "target customer",
    "competitive advantage",
    "value proposition"
]