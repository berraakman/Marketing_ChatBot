import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ===============================
# Conversation / routing settings
# ===============================
MAX_HISTORY = 6

DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = ["en", "de", "ar"]

PROMPT_DIR = os.path.join(BASE_DIR, "backend", "prompts")

# ===============================
# Ollama / LLM configuration
# ===============================
OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Chat models
LOCAL_CHAT_MODEL = os.getenv("OLLAMA_LOCAL_MODEL", "llama3:latest")
CLOUD_CHAT_MODEL = os.getenv("OLLAMA_CLOUD_MODEL", "gpt-oss:120b-cloud")

# Embedding model (RAG)
EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text:latest")

# Embedding dimensions (must match the actual model output)
EMBED_DIMENSIONS = {
    "nomic-embed-text:latest": 768,
    "all-minilm": 384,
    "text-embedding-3-large": 3072
}

# Resolve expected embedding dimension for the active model
EXPECTED_EMBED_DIM = EMBED_DIMENSIONS.get(EMBED_MODEL)

# ===============================
# RAG / Vector DB configuration
# ===============================
DOCS_DIR = os.path.join(BASE_DIR, "data", "docs")
CHROMA_DIR = os.path.join(BASE_DIR, "data", "chroma")

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

# ===============================
# App metadata
# ===============================
STARTUP_NAME = os.getenv("STARTUP_NAME", "FundEd - AI")