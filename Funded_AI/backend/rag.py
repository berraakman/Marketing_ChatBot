import os
import hashlib
import chromadb
from pypdf import PdfReader
from typing import List, Dict

from backend.config import (
    DOCS_DIR,
    CHROMA_DIR,
    MIN_SIM,
    SECTION_HEADERS,
)
from backend.router import default_router
from backend.dispatchers import dispatch_en, dispatch_de, dispatch_ar
from backend.llm import embed, rag_chat
from backend.llm import semantic_extractor


# ===============================
# Index / Vector DB
# ===============================
def ensure_index():
    os.makedirs(DOCS_DIR, exist_ok=True)
    os.makedirs(CHROMA_DIR, exist_ok=True)

    client = chromadb.PersistentClient(path=CHROMA_DIR)
    col = client.get_or_create_collection(
        name="startup_docs",
        metadata={"hnsw:space": "cosine"}
    )

    existing = set(col.get(include=[])["ids"])

    for fname in os.listdir(DOCS_DIR):
        if not fname.lower().endswith(".pdf"):
            continue

        path = os.path.join(DOCS_DIR, fname)
        doc_id = hashlib.md5(fname.encode()).hexdigest()

        if doc_id in existing:
            continue

        reader = PdfReader(path)
        full_text = "\n".join(page.extract_text() or "" for page in reader.pages)

        sections = split_sections(full_text)

        for i, (title, text) in enumerate(sections):
            if not text.strip():
                continue
            emb = embed(text)
            col.add(
                ids=[f"{doc_id}_{i}"],
                documents=[text],
                embeddings=[emb],
                metadatas=[{"section": title}]
            )


# ===============================
# Section parsing
# ===============================
def split_sections(text: str):
    """
    First try deterministic header-based splitting.
    If nothing meaningful is found, fall back to LLM semantic extraction.
    """
    sections = []
    current = None
    buffer = []

    for line in text.splitlines():
        l = line.strip().lower()
        if l in SECTION_HEADERS:
            if current is not None and buffer:
                sections.append((current, "\n".join(buffer)))
            current = line.strip()
            buffer = []
        else:
            buffer.append(line)

    if current is not None and buffer:
        sections.append((current, "\n".join(buffer)))

    # 🔁 Fallback: semantic extraction via LLM
    if not sections or sum(len(t) for _, t in sections) < 500:
        semantic = semantic_extractor(text)
        sections = [
            (k, v)
            for k, v in semantic.items()
            if k.lower() in SECTION_HEADERS and isinstance(v, str) and v.strip()
        ]

    return sections
# ===============================
# Auto Pitch
# ===============================
def auto_pitch():
    """
    Generate a clean startup narrative using all indexed knowledge.
    """
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    col = client.get_or_create_collection(
        name="startup_docs",
        metadata={"hnsw:space": "cosine"}
    )

    docs = col.get(include=["documents"])
    documents = docs.get("documents", [])
    if not documents:
        return "No startup knowledge indexed yet."
    full_context = "\n\n".join(documents)

    prompt = (
        "Using the following information, write a concise and compelling startup pitch. "
        "Clearly explain the problem, solution, product, target customer, and competitive advantage.\n\n"
        f"{full_context}"
    )

    messages = [
        {"role": "system", "content": "You are a professional startup pitch generator."},
        {"role": "user", "content": prompt},
    ]
    return rag_chat(messages)


# ===============================
# Retrieval
# ===============================
def retrieve_context(question: str) -> str:
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    col = client.get_or_create_collection(
        name="startup_docs",
        metadata={"hnsw:space": "cosine"}
    )

    q_emb = embed(question)

    results = col.query(
        query_embeddings=[q_emb],
        n_results=6,
        include=["documents", "distances", "metadatas"]
    )

    context_blocks = []

    for doc, dist, meta in zip(
        results["documents"][0],
        results["distances"][0],
        results["metadatas"][0],
    ):
        sim = 1 - dist
        if sim >= MIN_SIM:
            header = meta.get("section", "").upper()
            context_blocks.append(f"[{header}]\n{doc}")

    return "\n\n".join(context_blocks)


# ===============================
# Cards (kept for UI)
# ===============================
def get_quick_info_cards():
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    col = client.get_or_create_collection(
        name="startup_docs",
        metadata={"hnsw:space": "cosine"}
    )

    cards = []

    for h in SECTION_HEADERS:
        try:
            h_emb = embed(h)
        except ValueError:
            # Embedding dimension mismatch or model issue → skip cards safely
            return []

        res = col.query(
            query_embeddings=[h_emb],
            n_results=1,
            include=["documents"]
        )

        if res.get("documents") and res["documents"][0]:
            cards.append({
                "title": h.title(),
                "content": res["documents"][0][0][:300]
            })

    return cards


# ===============================
# Orchestration
# ===============================
def _sanitize_history(history):
    return [m for m in history if m.get("role") != "system"]


def answer(question: str, history: List[Dict[str, str]]):
    if not question or not isinstance(question, str):
        raise ValueError("question must be a non-empty string")

    history = _sanitize_history(history)
    route = default_router(question, history) or {}

    context = retrieve_context(question)

    if question.lower().strip() in [
        "bu startup'ı anlat",
        "describe the startup",
        "pitch the startup",
        "what is this startup"
    ]:
        return auto_pitch()

    if route.get("handled"):
        return route["response"]

    dispatch_map = {
        "en": dispatch_en,
        "de": dispatch_de,
        "ar": dispatch_ar,
    }

    lang = route.get("lang", "en")
    dispatcher = dispatch_map.get(lang, dispatch_en)
    return dispatcher(question, history, context)