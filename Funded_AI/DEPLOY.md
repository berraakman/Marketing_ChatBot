# Railway Deployment Guide

## Prerequisites

1. Railway account with billing enabled
2. OpenAI API key with billing enabled
3. Railway CLI installed (`npm i -g @railway/cli`)

---

## Required Environment Variables

Set these in Railway Dashboard → Variables:

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `OPENAI_API_KEY` | ✅ Yes | OpenAI API key | `sk-...` |
| `ADMIN_TOKEN` | ✅ Yes | Secret token for /reload endpoint | `your-secure-token` |
| `ALLOWED_ORIGINS` | Recommended | CORS origins (comma-separated) | `https://yourdomain.com` |
| `RATE_LIMIT` | Optional | Rate limit (default: 15/minute) | `20/minute` |
| `OPENAI_CHAT_MODEL` | Optional | Chat model version | `gpt-4o-mini-2024-07-18` |
| `OPENAI_EMBED_MODEL` | Optional | Embedding model | `text-embedding-3-small` |

---

## Volume Setup (CRITICAL)

ChromaDB requires persistent storage. Without this, your index is **lost on every deploy**.

### Step 1: Create Volume
```bash
railway volume create chroma_data
```

### Step 2: Attach Volume
The `railway.toml` already configures the mount at `/data`. Railway will automatically use this.

### Step 3: Upload Documents
After first deploy, copy your PDFs to the volume:
```bash
# Connect to your Railway service
railway shell

# Create docs directory and upload files
mkdir -p /data/docs
# Use Railway's file upload or SCP to add PDFs
```

---

## Deployment Steps

### 1. Initialize Railway Project
```bash
cd Funded_AI
railway init
```

### 2. Link to Project
```bash
railway link
```

### 3. Set Environment Variables
```bash
railway variables set OPENAI_API_KEY=sk-your-key-here
railway variables set ADMIN_TOKEN=your-secure-admin-token
railway variables set ALLOWED_ORIGINS=https://yourdomain.com
```

### 4. Deploy
```bash
railway up
```

### 5. Verify Deployment
```bash
# Get your deployment URL
railway open

# Test health endpoint
curl https://your-app.railway.app/health

# Test readiness
curl https://your-app.railway.app/ready

# Test chat (after index is built)
curl -X POST https://your-app.railway.app/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What is FundEd?", "history": []}'
```

---

## Resource Recommendations

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| Memory | 1024 MB | 2048 MB |
| CPU | 0.5 vCPU | 1 vCPU |
| Workers | 2 | 2-4 |

Set in Railway Dashboard → Settings → Resources.

---

## Rebuilding the Index

If you add new PDFs to `/data/docs`, trigger a rebuild:

```bash
curl -X POST https://your-app.railway.app/reload \
  -H "X-Admin-Token: your-admin-token"
```

---

## Monitoring

1. **Railway Logs**: `railway logs`
2. **Health Check**: Railway auto-monitors `/health`
3. **Metrics**: Railway Dashboard → Metrics

---

## Troubleshooting

### "ChromaDB not ready" on /ready
- Check that the volume is mounted correctly
- Verify `/data/chroma` directory exists
- Check logs for ChromaDB initialization errors

### "OpenAI API key invalid"
- Verify `OPENAI_API_KEY` is set correctly
- Check OpenAI billing is enabled
- Ensure the key has access to the models specified

### High latency on first request
- This is normal - sentence-transformers loads on first embedding call
- The Dockerfile pre-downloads the model, but loading still takes ~5-10s
- Health checks have a 60s start period to account for this

### Rate limit errors
- Default is 15 requests/minute per IP
- Adjust `RATE_LIMIT` environment variable if needed
- Consider implementing user-based rate limiting for production

---

## Security Checklist

- [ ] `OPENAI_API_KEY` is set via Railway Variables (not committed)
- [ ] `ADMIN_TOKEN` is a strong, unique secret
- [ ] `ALLOWED_ORIGINS` restricts to your domain(s)
- [ ] No `.env` file committed to git
- [ ] Rate limiting is enabled

---

## Cost Estimation (OpenAI)

| Operation | Cost (approximate) |
|-----------|-------------------|
| Embedding (text-embedding-3-small) | $0.02 / 1M tokens |
| Chat (gpt-4o-mini) | $0.15 / 1M input, $0.60 / 1M output |

With default settings (1000 max output tokens):
- Average chat: ~$0.001 per request
- Index rebuild: ~$0.01 per PDF page
