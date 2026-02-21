# FundEd AI – Marketing & Lead Generation Chatbot 🚀

A production-ready, highly responsive RAG (Retrieval-Augmented Generation) chatbot explicitly designed to act as an AI Marketing Booth Assistant for FundEd. It handles investor, founder, and partner inquiries dynamically in multiple languages seamlessly—perfect for events and product presentations.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o--mini-purple)
![Responsive](https://img.shields.io/badge/Mobile-Optimized-success)
![Railway](https://img.shields.io/badge/Deploy-Railway-blueviolet)

---

## 🌟 Key Features

- **Responsive & Modern UI:** A beautiful, responsive frontend with tailored views for both Desktop browsers and Mobile phone users (featuring custom dynamic viewport scaling).
- **RAG Pipeline (`ChromaDB`):** Instantly parses your FundEd presentation/pitch PDFs, embeds them dynamically, and answers incredibly specific queries correctly.
- **Multi-Lingual AI:** The Dispatcher architecture determines language intent instantly—capable of pitching the startup natively in **English, German, and Arabic**.
- **Production-Ready & Secure:** Out-of-the-box Rate Limiting via `slowapi`, configurable CORS, and Prompt Injection safeguards protect your backend.
- **Instant Deployments:** The Frontend and Backend are merged elegantly—FastAPI serves both. Zero configuration required for platforms like Railway.

---

## 📸 UI Previews

### Desktop Experience
Take a look at how spacious and clean the interaction is for users on computers or large booth tablets:

![Desktop UI Preview 1](assets/desktop1.png)
![Desktop UI Preview 2](assets/desktop2.png)

### Mobile Experience (Optimized)
When an attendee scans a QR code, they get a perfectly scaled, intuitive messaging interface tailored for thumbs and variable viewport sizes:

![Mobile UI Preview 1](assets/mobile1.png)
![Mobile UI Preview 2](assets/mobile2.png)

---

## 🛠 Project Architecture

The application handles everything in one place. FastAPI acts as the backbone, serving the stunning frontend while also performing complex vector calculations and LLM calls under the hood.

```text
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

---

## 🚀 Quick Start (Local Development)

### 1. Requirements

- Python 3.11+
- An OpenAI API key

### 2. Setup Process

Clone the repository and jump into the directory:
```bash
git clone https://github.com/berraakman/Marketing_ChatBot.git
cd Marketing_ChatBot/Funded_AI
```

Activate an environment and install dependencies:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Environment Variables
Copy the `.env.example` file to create your own `.env` file:
```bash
cp .env.example .env
```
Open the `.env` file and strictly supply your `OPENAI_API_KEY`. (There are additional options for rate limits, models, etc.)

### 4. Inject Knowledge!
Place any presentation, brochure, or startup PDFs you want the AI to read into the `data/docs/` folder.

### 5. Launch the Server
Start the magic:
```bash
uvicorn backend.app:app --reload --port 8080 --host 0.0.0.0 --env-file .env
```
Visit `http://localhost:8080` to interact with your local bot!

---

## ☁️ Deployment

### The Railway Route (Easiest)
This project is configured right out of the box to deploy gracefully onto Railway using its innate Docker compatibility.

1. Connect this GitHub Repository.
2. In your Railway settings, set the `OPENAI_API_KEY` and an `ADMIN_TOKEN`.
3. Hit Deploy. The server will natively build the vector index and expose both your frontend and API endpoints!

### Docker Method
If you're deploying on a custom VPS, just build the image:
```bash
docker build -t funded-chatbot .
docker run -p 8080:8080 -e OPENAI_API_KEY=sk-... -e ADMIN_TOKEN=your-token funded-chatbot
```

---

## 🧰 Customization & Commands

**How do I update the bot's knowledge?**
Whenever you add new PDFs to `data/docs/`, you can tell the server to reindex them live (without stopping it) by pinging the reload endpoint:

```bash
curl -X POST http://localhost:8080/reload \
  -H "X-Admin-Token: <YOUR_ADMIN_TOKEN_FROM_ENV>"
```

**How do I change its personality?**
Simply tweak the instructions located in `backend/prompts/marketing_system.txt`.

**Troubleshooting:**
If the bot ever fails to boot, ensure your PDFs exist in `data/docs/` and that your OpenAI API Key is valid.

---
*Proprietary - FundEd © 2026. Developed with ❤️ by Berra Akman.*
