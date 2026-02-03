import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from backend.rag import answer, ensure_index, get_quick_info_cards

logging.basicConfig(level=logging.INFO)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # dev için OK
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ensure_index()

MAX_HISTORY = 6

class ChatRequest(BaseModel):
    question: str
    history: list

@app.get("/")
def health():
    return {"status": "ok"}

@app.post("/chat")
def chat(req: ChatRequest):
    try:
        history = req.history[-MAX_HISTORY:]
        logging.info(f"Q: {req.question}")
        return {"response": answer(req.question, history)}
    except Exception:
        return {
            "response": "Sorry, something went wrong while processing your request."
        }

@app.post("/reload")
def reload_docs():
    ensure_index()
    return {"status": "reloaded"}

@app.get("/cards")
def cards():
    return get_quick_info_cards()