import os
import hashlib
import logging
import chromadb
from pypdf import PdfReader
from typing import List, Dict

from backend.config import (
    DOCS_DIR,
    CHROMA_DIR,
    MIN_SIM,
    SECTION_HEADERS,
    MAX_CONTEXT_TOKENS,
)
from backend.router import default_router
from backend.dispatchers import dispatch_en, dispatch_de, dispatch_ar
from backend.llm import embed, rag_chat, count_tokens

logger = logging.getLogger(__name__)

CARDS_PDF_NAME = "cards.pdf"
INDEX_HASH_FILE = ".index_hash"


# ===============================
# Index Hash Management
# ===============================
def _compute_docs_hash() -> str:
    """Compute hash of all documents in DOCS_DIR."""
    if not os.path.exists(DOCS_DIR):
        return ""
    
    hasher = hashlib.md5()
    for fname in sorted(os.listdir(DOCS_DIR)):
        if fname.lower().endswith(".pdf"):
            path = os.path.join(DOCS_DIR, fname)
            hasher.update(fname.encode())
            hasher.update(str(os.path.getmtime(path)).encode())
            hasher.update(str(os.path.getsize(path)).encode())
    return hasher.hexdigest()


def _get_stored_hash() -> str:
    """Get the previously stored index hash."""
    hash_path = os.path.join(CHROMA_DIR, INDEX_HASH_FILE)
    if os.path.exists(hash_path):
        with open(hash_path, "r") as f:
            return f.read().strip()
    return ""


def _store_hash(hash_val: str):
    """Store the current index hash."""
    hash_path = os.path.join(CHROMA_DIR, INDEX_HASH_FILE)
    with open(hash_path, "w") as f:
        f.write(hash_val)


# ===============================
# Index / Vector DB
# ===============================
def ensure_index():
    """Ensure vector index is up to date. Only rebuilds if documents changed."""
    os.makedirs(DOCS_DIR, exist_ok=True)
    os.makedirs(CHROMA_DIR, exist_ok=True)

    # Diagnostic logging for path resolution
    logger.info(f"DOCS_DIR resolved to: {DOCS_DIR}")
    logger.info(f"CHROMA_DIR resolved to: {CHROMA_DIR}")
    
    if os.path.exists(DOCS_DIR):
        files = os.listdir(DOCS_DIR)
        pdf_files = [f for f in files if f.lower().endswith('.pdf')]
        logger.info(f"Found {len(pdf_files)} PDF files in DOCS_DIR: {pdf_files}")
    else:
        logger.warning(f"DOCS_DIR does not exist: {DOCS_DIR}")

    current_hash = _compute_docs_hash()
    stored_hash = _get_stored_hash()
    
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    col = client.get_or_create_collection(
        name="startup_docs",
        metadata={"hnsw:space": "cosine"}
    )
    cards_col = client.get_or_create_collection(
        name="cards_docs",
        metadata={"hnsw:space": "cosine"}
    )
    
    # Skip if hash matches and collection is not empty
    if current_hash == stored_hash and col.count() > 0:
        logger.info(f"Index is up to date (hash: {current_hash[:8]}...), skipping rebuild")  # type: ignore[index]
        return
    
    logger.info(f"Building index (hash changed: {stored_hash[:8] if stored_hash else 'none'}... -> {current_hash[:8]}...)")  # type: ignore[index]
    
    existing = set(col.get(include=[])["ids"])

    for fname in os.listdir(DOCS_DIR):
        logger.info(f"Processing file: {fname}")
        is_cards_pdf = fname.lower() == CARDS_PDF_NAME
        if not fname.lower().endswith(".pdf"):
            continue

        path = os.path.join(DOCS_DIR, fname)
        reader = PdfReader(path)
        full_text = "\n".join(page.extract_text() or "" for page in reader.pages)
        logger.info(f"Extracted text length: {len(full_text)}")

        doc_id = hashlib.md5((fname + full_text).encode()).hexdigest()

        if doc_id in existing:
            continue

        if is_cards_pdf:
            sections = split_cards_sections(full_text)
            for title, text in sections:
                if not text.strip():
                    continue
                emb = embed(text)
                cards_col.upsert(
                    ids=[f"card_{title.lower()}"],
                    documents=[text.strip()],
                    embeddings=[emb],
                    metadatas=[{"section": title.lower()}]
                )
            continue

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
    
    # Store the hash after successful indexing
    _store_hash(current_hash)
    logger.info(f"Chroma collection count after indexing: {col.count()}")


# ===============================
# Section parsing
# ===============================

# Chunking configuration
CHUNK_SIZE = 500      # Characters per chunk (good for embedding context window)
CHUNK_OVERLAP = 100   # Overlap to preserve semantic continuity


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    Split text into overlapping chunks of specified size.
    
    For a ~1800 char document with chunk_size=500, overlap=100:
    - Chunk 1: chars 0-500
    - Chunk 2: chars 400-900 (100 char overlap)
    - Chunk 3: chars 800-1300
    - Chunk 4: chars 1200-1700
    - Chunk 5: chars 1600-1800
    = ~5 chunks (good for n_results=4)
    """
    if len(text) <= chunk_size:
        return [text] if text.strip() else []
    
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        
        # Try to break at sentence boundary if not at end
        if end < len(text):
            # Look for sentence endings in last 20% of chunk
            break_zone = chunk[int(chunk_size * 0.8):]
            for sep in ['. ', '.\n', '! ', '?\n', '\n\n']:
                if sep in break_zone:
                    break_idx = chunk.rfind(sep) + len(sep)
                    chunk = chunk[:break_idx]
                    end = start + break_idx
                    break
        
        if chunk.strip():
            chunks.append(chunk.strip())
        
        start = end - overlap
    
    return chunks


def split_sections(text: str):
    """Split text by section headers, with chunking fallback."""
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
            buffer.append(line)  # type: ignore[arg-type]

    if current is not None and buffer:
        sections.append((current, "\n".join(buffer)))

    # If no section headers found, use character-based chunking
    if not sections:
        logger.info(f"No section headers found, using character-based chunking (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})")
        chunks = chunk_text(text)
        logger.info(f"Created {len(chunks)} chunks from document")
        return [(f"chunk_{i}", chunk) for i, chunk in enumerate(chunks)]
    
    # If sections found but any are too long, chunk them too
    final_sections = []
    for title, content in sections:
        if len(content) > CHUNK_SIZE * 2:  # Section is too long
            chunks = chunk_text(content)
            for i, chunk in enumerate(chunks):
                final_sections.append((f"{title}_part{i}", chunk))
        else:
            final_sections.append((title, content))
    
    return final_sections


def split_cards_sections(text: str):
    """Split cards PDF by section headers."""
    sections = {}
    current = None

    normalized_headers = {h.lower(): h.lower() for h in SECTION_HEADERS}

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        lower = line.lower()
        if lower in normalized_headers:
            current = normalized_headers[lower]
            sections[current] = []
        elif current:
            sections[current].append(line)  # type: ignore[union-attr]

    return [
        (k, " ".join(v).strip())
        for k, v in sections.items()
        if v
    ]


# ===============================
# Auto Pitch
# ===============================
def auto_pitch():
    """Generate a clean startup narrative using all indexed knowledge."""
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    col = client.get_or_create_collection(
        name="startup_docs",
        metadata={"hnsw:space": "cosine"}
    )

    docs = col.get(include=["documents"])
    documents = docs.get("documents", [])
    if not documents:
        return "No startup knowledge indexed yet."
    
    # Truncate context to token limit
    full_context = ""
    for doc in documents:
        if count_tokens(full_context + "\n\n" + doc) > MAX_CONTEXT_TOKENS:
            break
        full_context += "\n\n" + doc
    full_context = full_context.strip()

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
    """Retrieve relevant context from vector database."""
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    col = client.get_or_create_collection(
        name="startup_docs",
        metadata={"hnsw:space": "cosine"}
    )

    # Dynamic n_results to avoid "requested results > elements" error
    collection_size = col.count()
    n_results = min(4, collection_size) if collection_size > 0 else 1
    
    if collection_size == 0:
        logger.warning("No documents in collection, cannot retrieve context")
        return ""

    q_emb = embed(question)

    results = col.query(
        query_embeddings=[q_emb],
        n_results=n_results,
        include=["documents", "distances", "metadatas"]
    )

    context_blocks: list[str] = []
    total_tokens: int = 0

    for doc, dist, meta in zip(
        results["documents"][0],
        results["distances"][0],
        results["metadatas"][0],
    ):
        sim = 1 - dist  # type: ignore[operator]
        if sim >= MIN_SIM:
            header = meta.get("section", "").upper()  # type: ignore[union-attr]
            block = f"[{header}]\n{doc}"
            block_tokens = count_tokens(block)
            
            # Stop if we exceed token budget
            if total_tokens + block_tokens > MAX_CONTEXT_TOKENS:  # type: ignore[operator]
                break
                
            context_blocks.append(block)
            total_tokens += block_tokens  # type: ignore[operator]

    return "\n\n".join(context_blocks)


# ===============================
# Cards (kept for UI)
# ===============================
def get_quick_info_cards():
    """Get quick info cards from the cards collection."""
    logger.info("Running Quick Info Cards")
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    col = client.get_or_create_collection(
        name="cards_docs",
        metadata={"hnsw:space": "cosine"}
    )

    cards = []

    for h in SECTION_HEADERS:
        key = h.lower()
        res = col.get(
            ids=[f"card_{key}"],
            include=["documents"]
        )

        if res.get("documents") and res["documents"]:
            cards.append({
                "title": h.title(),
                "content": res["documents"][0]
            })

    return cards


# ===============================
# Orchestration
# ===============================
def _sanitize_history(history):
    """Remove system messages from history."""
    return [m for m in history if m.get("role") != "system"]


def answer(question: str, history: List[Dict[str, str]]):
    """Generate answer to user question."""
    if not question or not isinstance(question, str):
        raise ValueError("question must be a non-empty string")

    history = _sanitize_history(history)
    route = default_router(question, history) or {}

    context = retrieve_context(question)
    
    # Log context availability for debugging (don't block on empty)
    if context.strip():
        logger.info(f"Retrieved context length: {len(context)} chars")
    else:
        logger.info("No matching context found, LLM will respond based on general knowledge")

    # Handle special pitch requests
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
    
    # Pass context to dispatcher - it handles None/empty gracefully
    # The LLM will decide if it has enough information based on the system prompt
    return dispatcher(question, history, context if context.strip() else None)