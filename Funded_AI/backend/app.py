import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict
from fastapi import HTTPException

from backend.rag import answer, ensure_index, get_quick_info_cards
from backend.config import MAX_HISTORY
from backend.router import default_router

logging.basicConfig(level=logging.INFO)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# Add FastAPI startup event handler to ensure index on startup
@app.on_event("startup")
def startup_event():
    try:
        ensure_index()
    except Exception as e:
        logging.error(f"Startup index error: {e}")


class ChatRequest(BaseModel):
    question: str
    history: List[Dict[str, str]]


@app.get("/")
def health():
    return {"status": "ok"}


@app.post("/chat")
def chat(req: ChatRequest):
    history = req.history[-MAX_HISTORY:] if req.history else []
    question = req.question.strip()

    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    logging.info(f"Q: {question}")

    route = default_router(question, history) or {}

    # Greeting or directly handled intents
    if route.get("handled"):
        return {"response": route.get("response", "")}

    # Auto pitch mode
    if route.get("intent") == "auto_pitch":
        return {
            "response": answer(
                question="Give a clear startup pitch based on all available knowledge.",
                history=[]
            )
        }

    # Default QA (RAG)
    return {"response": answer(question, history)}


@app.post("/reload")
def reload_docs():
    ensure_index()
    return {"status": "reloaded"}


@app.get("/cards")
def cards():
    return get_quick_info_cards()