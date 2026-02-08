import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ===============================
# Railway Volume Paths
# ===============================
# Railway volume is mounted at /data
# These can be overridden via environment variables
CHROMA_DIR = os.getenv("CHROMA_DIR", "/data/chroma")
DOCS_DIR = os.getenv("DOCS_DIR", "/data/docs")

# Fallback to local paths for development
if os.getenv("RAILWAY_ENVIRONMENT") is None:
    CHROMA_DIR = os.getenv("CHROMA_DIR", os.path.join(BASE_DIR, "data", "chroma"))
    DOCS_DIR = os.getenv("DOCS_DIR", os.path.join(BASE_DIR, "data", "docs"))

# ===============================
# Conversation / routing settings
# ===============================
MAX_HISTORY = 6
MAX_QUESTION_LENGTH = 2000
MAX_CONTEXT_TOKENS = 3000
MAX_RESPONSE_TOKENS = 1000

DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = ["en", "de", "ar"]

PROMPT_DIR = os.path.join(BASE_DIR, "backend", "prompts")

# ===============================
# OpenAI Configuration
# ===============================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini-2024-07-18")
OPENAI_EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-large")

# Timeout for OpenAI API calls in seconds
OPENAI_TIMEOUT = int(os.getenv("OPENAI_TIMEOUT", "60"))

# ===============================
# Embedding dimensions
# ===============================
EMBED_DIMENSIONS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "all-MiniLM-L6-v2": 384,
}

EXPECTED_EMBED_DIM = EMBED_DIMENSIONS.get(OPENAI_EMBED_MODEL, 1536)

# ===============================
# RAG / Vector DB configuration
# ===============================
MIN_SIM = 0.50

SECTION_HEADERS = [
    "problem",
    "solution",
    "product",
    "target users",
    "value proposition",
    "impact tracking",
    "revenue model",
    "why funded",
    "go-to-market",
    "vision"
]

# ===============================
# Rate Limiting
# ===============================
RATE_LIMIT = os.getenv("RATE_LIMIT", "15/minute")

# ===============================
# Admin Token for protected endpoints
# ===============================
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")

# ===============================
# CORS Settings
# ===============================
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

# ===============================
# App metadata
# ===============================
STARTUP_NAME = os.getenv("STARTUP_NAME", "FundEd - AI")


# ===============================
# Config Validation
# ===============================
def validate_config():
    """Validate required configuration at startup."""
    errors = []
    
    if not OPENAI_API_KEY:
        errors.append("OPENAI_API_KEY is required")
    
    if not ADMIN_TOKEN:
        errors.append("ADMIN_TOKEN is required")
    
    if errors:
        raise RuntimeError(f"Configuration errors: {', '.join(errors)}")


# ===============================
# Prompt Injection Patterns
# ===============================
INJECTION_PATTERNS = [
    "ignore previous",
    "ignore all instructions",
    "ignore above",
    "disregard previous",
    "disregard all",
    "forget previous",
    "forget all instructions",
    "you are now",
    "new instructions:",
    "system prompt:",
    "reveal your prompt",
    "show your instructions",
    "what are your instructions",
    "override:",
    "jailbreak",
]