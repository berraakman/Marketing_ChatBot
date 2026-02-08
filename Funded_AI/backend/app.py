import logging
import os
from contextlib import asynccontextmanager
from typing import List, Dict

from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, field_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import chromadb

from backend.rag import answer, ensure_index, get_quick_info_cards
from backend.config import (
    MAX_HISTORY,
    MAX_QUESTION_LENGTH,
    CHROMA_DIR,
    ALLOWED_ORIGINS,
    RATE_LIMIT,
    ADMIN_TOKEN,
    INJECTION_PATTERNS,
    validate_config,
)
from backend.router import default_router

# ===============================
# Logging Configuration
# ===============================
logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","module":"%(module)s","message":"%(message)s"}',
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ===============================
# Frontend Directory
# ===============================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# ===============================
# Rate Limiter
# ===============================
limiter = Limiter(key_func=get_remote_address)


# ===============================
# Lifespan Context Manager
# ===============================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    # Startup
    logger.info("Application starting up...")
    
    try:
        validate_config()
        logger.info("Configuration validated successfully")
    except RuntimeError as e:
        logger.critical(f"Configuration validation failed: {e}")
        raise
    
    try:
        ensure_index()
        logger.info("Index ensured successfully")
    except Exception as e:
        logger.error(f"Index initialization error: {e}")
        # Don't crash - index can be built later via /reload
    
    yield
    
    # Shutdown
    logger.info("Application shutting down...")


# ===============================
# FastAPI Application
# ===============================
app = FastAPI(
    title="FundEd Marketing Chatbot",
    description="AI-powered marketing assistant",
    version="1.0.0",
    lifespan=lifespan,
)

# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Admin-Token"],
)


# ===============================
# Input Validation
# ===============================
def check_prompt_injection(text: str) -> bool:
    """Check if text contains potential prompt injection patterns."""
    lower = text.lower()
    for pattern in INJECTION_PATTERNS:
        if pattern in lower:
            return True
    return False


def sanitize_input(text: str) -> str:
    """Sanitize user input."""
    # Remove excessive whitespace
    text = " ".join(text.split())
    return text.strip()


# ===============================
# Request Models
# ===============================
class ChatRequest(BaseModel):
    question: str
    history: List[Dict[str, str]] = []
    
    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Question cannot be empty")
        if len(v) > MAX_QUESTION_LENGTH:
            raise ValueError(f"Question too long. Maximum {MAX_QUESTION_LENGTH} characters.")
        return v
    
    @field_validator("history")
    @classmethod
    def validate_history(cls, v: List[Dict[str, str]]) -> List[Dict[str, str]]:
        if len(v) > MAX_HISTORY * 2:
            v = v[-(MAX_HISTORY * 2):]  # type: ignore[index]
        return v


# ===============================
# Health Endpoints
# ===============================
@app.get("/health")
def health():
    """Liveness probe - basic health check."""
    return {"status": "healthy"}


@app.get("/ready")
def readiness():
    """Readiness probe - check dependencies."""
    errors = []
    
    # Check ChromaDB connectivity
    try:
        client = chromadb.PersistentClient(path=CHROMA_DIR)
        client.heartbeat()
    except Exception as e:
        errors.append(f"ChromaDB: {str(e)}")
    
    if errors:
        logger.error(f"Readiness check failed: {errors}")
        raise HTTPException(
            status_code=503,
            detail={"status": "not ready", "errors": errors}
        )
    
    return {"status": "ready"}


@app.get("/")
def root():
    """Serve chat frontend."""
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    return {"service": "FundEd Marketing Chatbot", "status": "ok", "version": "1.0.0"}


# ===============================
# Chat Endpoint
# ===============================
@app.post("/chat")
@limiter.limit(RATE_LIMIT)
def chat(request: Request, req: ChatRequest):
    """Main chat endpoint with rate limiting."""
    question = sanitize_input(req.question)
    
    # Check for prompt injection
    if check_prompt_injection(question):
        logger.warning(f"Potential prompt injection detected: {question[:100]}...")  # type: ignore[index]
        raise HTTPException(
            status_code=400,
            detail="Invalid input detected"
        )
    
    # Also check history for injections
    for msg in req.history:
        content = msg.get("content", "")
        if check_prompt_injection(content):
            logger.warning("Prompt injection detected in history")
            raise HTTPException(
                status_code=400,
                detail="Invalid input detected in conversation history"
            )
    
    history = req.history[-MAX_HISTORY:] if req.history else []  # type: ignore[index]
    
    logger.info(f"Chat request received: {question[:50]}...")  # type: ignore[index]
    
    route = default_router(question, history) or {}
    intent = route.get("intent")
    depth = route.get("depth")
    
    # Fully handled responses (e.g. greetings)
    if route.get("handled"):
        return {"response": route.get("response", "")}
    
    # Auto pitch mode (investor-style explanation)
    if intent in ["about", "auto_pitch"] and depth == "pitch":
        return {
            "response": answer(
                question="Give a concise startup pitch explaining FundEd, its problem, solution, product, and value.",
                history=[]
            )
        }
    
    # Standard QA (RAG-based answer)
    return {"response": answer(question, history)}


# ===============================
# Admin Endpoints
# ===============================
@app.post("/reload")
def reload_docs(x_admin_token: str = Header(None, alias="X-Admin-Token")):
    """Reload document index - protected endpoint."""
    if not ADMIN_TOKEN:
        raise HTTPException(
            status_code=503,
            detail="Reload endpoint not configured"
        )
    
    if x_admin_token != ADMIN_TOKEN:
        logger.warning("Unauthorized reload attempt")
        raise HTTPException(
            status_code=401,
            detail="Unauthorized"
        )
    
    logger.info("Manual reload triggered")
    try:
        ensure_index()
        return {"status": "reloaded", "message": "Index rebuilt successfully"}
    except Exception as e:
        logger.error(f"Reload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cards")
@limiter.limit(RATE_LIMIT)
def cards(request: Request):
    """Get quick info cards."""
    logger.info("/cards endpoint called")
    return get_quick_info_cards()


# ===============================
# Static Files (Frontend)
# ===============================
# Mount at paths that match what HTML expects (no /static prefix needed)
# This makes frontend code cleaner and backend the single source of truth
if os.path.exists(FRONTEND_DIR):
    # Mount assets directory at /assets (for images, fonts, etc.)
    assets_dir = os.path.join(FRONTEND_DIR, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
    
    # Mount root frontend files at /static (for CSS, JS)
    # These are accessed as /static/styles.css, /static/app.js
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")