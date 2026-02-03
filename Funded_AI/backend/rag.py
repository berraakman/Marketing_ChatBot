#calistirmak icin
#vs terminal --> uvicorn backend.app:app --reload
#terminal --> dosyaya gir --> open frontend/index.html

import os, math, hashlib, requests, chromadb
from pypdf import PdfReader
from backend.config import *

# index
def ensure_index():
    os.makedirs(DOCS_DIR, exist_ok=True)
    os.makedirs(CHROMA_DIR, exist_ok=True)

    client = chromadb.PersistentClient(path=CHROMA_DIR)
    col = client.get_or_create_collection("startup_docs")

    if col.count() == 0:
        ingest_docs()

# ollama
def ollama_embed(text: str):
    text = text[:4000]
    r = requests.post(
        f"{OLLAMA_BASE}/api/embeddings",
        json={"model": EMBED_MODEL, "prompt": text},
        timeout=60
    )
    r.raise_for_status()
    return r.json()["embedding"]

def ollama_chat(messages, temp=0.65, model=None):
    r = requests.post(
        f"{OLLAMA_BASE}/api/chat",
        json={
            "model": model or LOCAL_CHAT_MODEL,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temp}
        },
        timeout=60
    )
    r.raise_for_status()
    return r.json()["message"]["content"]

# document ingest
def read_pdf(path):
    reader = PdfReader(path)
    return "\n".join(p.extract_text() or "" for p in reader.pages)

def chunk_by_sections(text):
    sections = {}
    current = None

    for line in text.split("\n"):
        clean = line.strip().lower().rstrip(":")
        for h in SECTION_HEADERS:
            if clean == h:
                current = h
                sections[current] = []
                break
        else:
            if current:
                sections[current].append(line)

    return {k: "\n".join(v) for k, v in sections.items() if len(v) > 20}

def ingest_docs():
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    col = client.get_or_create_collection("startup_docs")

    for fn in os.listdir(DOCS_DIR):
        if not fn.endswith(".pdf"):
            continue

        text = read_pdf(os.path.join(DOCS_DIR, fn))
        sections = chunk_by_sections(text) or {"full": text}

        for sec, content in sections.items():
            cid = hashlib.sha1(f"{fn}-{sec}".encode()).hexdigest()
            emb = ollama_embed(content)
            col.upsert(
                ids=[cid],
                documents=[content],
                embeddings=[emb],
                metadatas=[{"source": fn, "section": sec}]
            )

# RAG 
def cosine(a, b):
    return sum(x*y for x, y in zip(a, b)) / (
        math.sqrt(sum(x*x for x in a)) *
        math.sqrt(sum(y*y for y in b))
    )

def answer(question, history):
    def analyze_message(text: str):
        prompt = [
            {
                "role": "system",
                "content": (
                    "Analyze the user message and respond ONLY with valid JSON.\n"
                    "Schema:\n"
                    "{\n"
                    '  "intent": one of ["GREETING","IDENTITY","DETAIL","CONTINUE","QUESTION"],\n'
                    '  "topic": one of ["FUNDED","OTHER"],\n'
                    '  "language": ISO 639-1 code\n'
                    "}\n"
                    "Rules:\n"
                    "- CONTINUE = short confirmations like yes, please, ok, continue, explain more\n"
                    "- DETAIL = explicit request for details or explanation\n"
                    "- QUESTION = factual question\n"
                    "- Topic FUNDED if the message is a greeting, continuation, or refers implicitly to the company in context\n"
                    "- Topic OTHER only if the message is clearly unrelated to the company (e.g. history, weather, general knowledge)\n"
                    "- No extra text"
                )
            },
            {
                "role": "user",
                "content": text
            }
        ]

        raw = ollama_chat(prompt, temp=0.0, model=LOCAL_CHAT_MODEL)

        import json, re
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            return {"intent": "QUESTION", "topic": "OTHER", "language": "en"}

        return json.loads(match.group(0))

    analysis = analyze_message(question)
    intent = analysis.get("intent", "QUESTION")
    topic = analysis.get("topic", "OTHER")
    lang = analysis.get("language", "en")

    # Dil devamlılıgı
    if history:
        for m in reversed(history):
            prev_lang = m.get("lang")
            if prev_lang:
                if lang == "en" and prev_lang != "en":
                    lang = prev_lang
                break

    has_started = any(m.get("role") == "assistant" for m in history)

    if intent in {"GREETING", "CONTINUE", "DETAIL"} and topic == "OTHER":
        topic = "FUNDED"
        if intent == "CONTINUE":
            intent = "DETAIL"

    if intent == "GREETING" and not has_started:
        greeting = (
            "Hi! 👋 I’m FundEd’s AI booth assistant. "
            "I help explain FundEd’s product, impact, and investment opportunity."
        )

        if lang != "en":
            greeting = ollama_chat(
                [
                    {"role": "system", "content": f"Translate into {lang}. Do not add information."},
                    {"role": "user", "content": greeting}
                ],
                model=CLOUD_CHAT_MODEL
            )
        return greeting

    if intent == "IDENTITY" and not has_started:
        identity = (
            "I’m FundEd‑AI, the official AI booth assistant for FundEd."
        )

        if lang != "en":
            identity = ollama_chat(
                [
                    {"role": "system", "content": f"Translate into {lang}. Do not add information."},
                    {"role": "user", "content": identity}
                ],
                model=CLOUD_CHAT_MODEL
            )
        return identity

    #  CONTEXTUAL CONTINUATION ??
    if intent in {"CONTINUE"} and history:
        for m in reversed(history):
            if m["role"] == "user":
                question = m["content"]
                break

    client = chromadb.PersistentClient(path=CHROMA_DIR)
    col = client.get_collection("startup_docs")

    qemb = ollama_embed(question)
    res = col.query(
        query_embeddings=[qemb],
        n_results=5,
        include=["documents", "embeddings"]
    )

    scored = sorted(
        [(cosine(qemb, e), d) for d, e in zip(res["documents"][0], res["embeddings"][0])],
        reverse=True
    )

    top_score = scored[0][0] if scored else 0.0

    if top_score < 0.25:
        redirect = (
            "That’s a great question and it’s directly related to FundEd. "
            "To be fully accurate, this is something our booth team usually explains in person. "
            "I can connect you with them, or we can continue with areas I can explain clearly—"
            "such as the product flow, ESG reporting, or pilot use cases."
        )

        if lang != "en":
            redirect = ollama_chat(
                [
                    {"role": "system", "content": f"Translate into {lang}. Do not add information."},
                    {"role": "user", "content": redirect}
                ],
                model=CLOUD_CHAT_MODEL
            )
        return redirect

    context = "\n\n".join(d for _, d in scored)

    detailed = intent in {"DETAIL", "CONTINUE"}

    user_content = (
        f"QUESTION:\n{question}\n\nCONTEXT:\n{context}"
        if detailed
        else f"QUESTION:\n{question}"
    )

    messages = [
        {
            "role": "system",
            "content": (
                f"You are the official on‑booth marketing agent for {STARTUP_NAME}. "
                "Respond in a SHORT, clear, and confident marketing tone.\n"
                "Rules:\n"
                "- Maximum 2–3 sentences unless the user explicitly asks for details\n"
                "- Do NOT use bullet points or lists unless asked\n"
                "- Do NOT mention pricing, plans, or numbers unless asked\n"
                "- Start with a single strong value statement\n"
                "- End with a brief offer to explain more (one sentence max)\n"
                "- Sound natural and conversational, not like a pitch deck\n"
                "- NEVER mention blockchain, tokens, crypto, or Web3\n"
                "- NEVER repeat the same opening sentence twice in a conversation\n"
                "- If similar information was already given, rephrase it from a different angle\n"
                "- When possible, anchor answers to specific concepts (verification, reporting, pilots, dashboards)\n"
                "- After answering, suggest ONE related topic the user may want to explore next\n"
            )
        }
    ] + history[-8:] + [
        {
            "role": "user",
            "content": user_content
        }
    ]

    response = ollama_chat(messages, model=CLOUD_CHAT_MODEL)

    if lang != "en":
        response = ollama_chat(
            [
                {
                    "role": "system",
                    "content": f"Translate the following answer into {lang}. Do not add or remove any information."
                },
                {
                    "role": "user",
                    "content": response
                }
            ],
            model=CLOUD_CHAT_MODEL
        )

    return response

# sidebar cards

def load_cached_cards():
    path = os.path.join(CHROMA_DIR, "cards_cache.json")
    if os.path.exists(path):
        import json
        with open(path, "r") as f:
            return json.load(f)
    return None


def save_cached_cards(cards):
    path = os.path.join(CHROMA_DIR, "cards_cache.json")
    import json
    with open(path, "w") as f:
        json.dump(cards, f, indent=2)


def get_quick_info_cards():
    cached = load_cached_cards()
    if cached:
        return cached

    client = chromadb.PersistentClient(path=CHROMA_DIR)
    col = client.get_collection("startup_docs")

    all_docs = col.get(include=["documents"])["documents"]
    if not all_docs:
        return [
            {"title": "📄 No Content Found", "content": "PDF content could not be extracted."}
        ]

    full_text = "\n\n".join(all_docs[0])[:2500]

    prompt = [
        {
            "role": "system",
            "content": (
                "You are the official MARKETING AGENT for FundEd at an investor booth. "
                "Describe FundEd itself — not documents or sources. "
                "Focus on the real problem, solution, product, and advantage. "
                "Return ONLY valid JSON in this format:\n"
                "{"
                "\"Problem\": \"...\", "
                "\"Solution\": \"...\", "
                "\"Product\": \"...\", "
                "\"Advantage\": \"...\""
                "}"
            )
        },
        {
            "role": "user",
            "content": full_text
        }
    ]

    raw = ollama_chat(prompt, temp=0.3, model=LOCAL_CHAT_MODEL)

    import json, re

    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError("No JSON returned for cards")

    data = json.loads(match.group(0))

    cards = [
        {"title": "💡 Problem", "content": data.get("Problem", "").strip()},
        {"title": "💡 Solution", "content": data.get("Solution", "").strip()},
        {"title": "💡 Product", "content": data.get("Product", "").strip()},
        {"title": "💡 Advantage", "content": data.get("Advantage", "").strip()},
    ]

    # Deduplicate cards by title (safety guard)
    seen = set()
    deduped = []
    for c in cards:
        if c["title"] not in seen:
            seen.add(c["title"])
            deduped.append(c)
    cards = deduped

    save_cached_cards(cards)
    return cards