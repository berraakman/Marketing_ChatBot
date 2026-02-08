# FundEd Marketing Chatbot

A production-ready RAG-powered chatbot for FundEd, designed for marketing presentations and first-touch conversations at events and booths.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o--mini-purple)
![Railway](https://img.shields.io/badge/Deploy-Railway-blueviolet)

## Overview

This chatbot serves as FundEd's AI assistant, answering questions about the platform using Retrieval-Augmented Generation (RAG). It retrieves relevant context from indexed PDF documents and generates natural, marketing-friendly responses.

### Key Features

- **RAG Pipeline**: ChromaDB vector store + OpenAI embeddings for accurate retrieval
- **Multi-language Support**: English, German, and Arabic dispatchers
- **Production-Ready**: Rate limiting, CORS, admin endpoints, graceful error handling
- **Self-Contained**: Frontend served from the same backend (no separate deployment)
- **Railway-Optimized**: Works without persistent volumes, builds index from bundled PDFs

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                             │
│   index.html + styles.css + app.js (served via FastAPI)    │
└─────────────────────────┬───────────────────────────────────┘
                          │ POST /chat
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │  Router  │→ │   RAG    │→ │Dispatcher│→ │    LLM     │  │
│  │ (intent) │  │(retrieve)│  │ (en/de/ar)│  │(OpenAI API)│  │
│  └──────────┘  └────┬─────┘  └──────────┘  └────────────┘  │
│                     │                                       │
│              ┌──────▼──────┐                               │
│              │  ChromaDB   │                               │
│              │(vector store)│                              │
│              └─────────────┘                               │
└─────────────────────────────────────────────────────────────┘
```

## Project Structure

```
Funded_AI/
├── backend/
│   ├── app.py              # FastAPI application, routes, middleware
│   ├── config.py           # Environment configuration
│   ├── rag.py              # RAG pipeline: indexing, retrieval, chunking
│   ├── llm.py              # OpenAI API calls (chat, embeddings)
│   ├── router.py           # Intent routing and language detection
│   ├── dispatchers/        # Language-specific response handlers
│   │   ├── en.py           # English dispatcher
│   │   ├── de.py           # German dispatcher
│   │   └── ar.py           # Arabic dispatcher
│   └── prompts/            # System prompts for the LLM
│       └── marketing_system.txt
├── frontend/
│   ├── index.html          # Chat UI
│   ├── styles.css          # Styling
│   ├── app.js              # Frontend logic
│   └── assets/             # Images (ai.png, user.png)
├── data/
│   └── docs/               # PDF documents for RAG indexing
│       ├── FundEd.pdf      # Main knowledge base
│       └── cards.pdf       # Info cards content
├── Dockerfile              # Production Docker image
├── railway.toml            # Railway deployment config
├── requirements.txt        # Python dependencies
└── .env.example            # Environment variables template
```

## Quick Start

### Prerequisites

- Python 3.11+
- OpenAI API key

### Local Development

1. **Clone and setup**
   ```bash
   cd Funded_AI
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env and add your OPENAI_API_KEY
   ```

3. **Add your PDFs**
   ```bash
   # Place PDF documents in data/docs/
   ```

4. **Run the server**
   ```bash
   uvicorn backend.app:app --reload --port 8000
   ```

5. **Open the UI**
   ```
   http://localhost:8000
   ```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | ✅ | - | Your OpenAI API key |
| `OPENAI_CHAT_MODEL` | ❌ | `gpt-4o-mini-2024-07-18` | Chat model |
| `OPENAI_EMBED_MODEL` | ❌ | `text-embedding-3-large` | Embedding model |
| `ADMIN_TOKEN` | ❌ | - | Token for `/reload` endpoint |
| `RATE_LIMIT` | ❌ | `15/minute` | Rate limit per IP |
| `ALLOWED_ORIGINS` | ❌ | `*` | CORS allowed origins |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Serves the chat frontend |
| `GET` | `/health` | Health check |
| `POST` | `/chat` | Main chat endpoint |
| `GET` | `/pitch` | Auto-generated startup pitch |
| `GET` | `/info-cards` | Retrieve info card content |
| `POST` | `/reload` | Rebuild document index (requires `X-Admin-Token`) |

### Chat Request Example

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What problem does FundEd solve?",
    "history": []
  }'
```

### Reload Index

```bash
curl -X POST https://your-app.railway.app/reload \
  -H "X-Admin-Token: your-admin-token"
```

## Deployment

### Railway (Recommended)

1. **Connect your repository** to Railway
2. **Set environment variables** in Railway dashboard:
   - `OPENAI_API_KEY`
   - `ADMIN_TOKEN`
3. **Deploy** - Railway auto-detects the Dockerfile

The app will:
- Build the Docker image
- Index PDFs from `data/docs/` at startup
- Serve the frontend and API on the same URL

### Docker

```bash
docker build -t funded-chatbot .
docker run -p 8080:8080 \
  -e OPENAI_API_KEY=sk-... \
  -e ADMIN_TOKEN=your-token \
  funded-chatbot
```

## How It Works

### Document Indexing

1. PDFs in `data/docs/` are parsed using `pypdf`
2. Text is split into 500-character chunks with 100-character overlap
3. Each chunk is embedded using OpenAI's embedding model
4. Embeddings are stored in ChromaDB

### Query Flow

1. User sends a question via `/chat`
2. Question is embedded and matched against stored chunks
3. Top 4 relevant chunks are retrieved (if similarity > 0.5)
4. Context + question are sent to GPT-4o-mini
5. Model generates a natural response grounded in the context

## Customization

### Adding Documents

1. Add PDF files to `data/docs/`
2. Trigger reindex:
   ```bash
   curl -X POST https://your-app.railway.app/reload \
     -H "X-Admin-Token: your-token"
   ```

### Modifying Prompts

Edit `backend/prompts/marketing_system.txt` to change the chatbot's personality and response style.

### Adding Languages

1. Create `backend/dispatchers/XX.py` (copy from `en.py`)
2. Create `backend/prompts/marketing_XX.txt`
3. Add the language to the dispatch map in `backend/rag.py`

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Chroma collection count: 0" | Check PDFs exist in `data/docs/` and rebuild index |
| APIConnectionError at startup | Network not ready; app retries automatically |
| "Unauthorized" on /reload | Use `X-Admin-Token` header (not `Authorization: Bearer`) |
| Empty responses | Check OpenAI API key is valid |

## License

Proprietary - FundEd © 2026
