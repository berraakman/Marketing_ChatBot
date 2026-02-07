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


@app.post("/reload")
def reload_docs():
    logging.info("🔄 Manual reload triggered")
    try:
        ensure_index()
        return {"status": "reloaded", "message": "Index rebuilt successfully"}
    except Exception as e:
        logging.error(f"Reload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cards")
def cards():
    logging.info("🧠 /cards endpoint called")
    return get_quick_info_cards()