# Healthcare Grant Proposal AI

AI-powered platform for automating healthcare grant and RFP proposal responses.

**Stack:** Django 5 · Django REST Framework · React · PostgreSQL · Ollama / OpenAI / Claude

---

## Features

| Feature | Description |
|---|---|
| **Document processing** | PDF, DOCX, Excel, scanned images (OCR) → structured content blocks |
| **Synthetic parsing** | Routes text / tables / images to the right extractor automatically |
| **Multi-LLM switch** | Ollama (local) · OpenAI GPT-4o · Anthropic Claude — swap per request |
| **Proposal generation** | Section-by-section generation with healthcare-specific prompts |
| **Compliance checking** | HIPAA, page limits, certifications, fabrication detection |
| **DOCX export** | Formatted Word document ready for submission |
| **React UI** | Dashboard, document manager, proposal builder, compliance reporter |

---

## Quick Start

### 1 — Clone

```bash
git clone https://github.com/SugandhaAgrawal-dev/grant-proposal-ai.git
cd grant-proposal-ai
```

### 2 — Backend setup

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env — set DATABASE_URL and DEFAULT_LLM_PROVIDER
```

### 3 — Database (Docker — recommended)

```bash
docker run -d \
  --name grant_proposal_db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=grant_proposal_db \
  -p 5432:5432 \
  pgvector/pgvector:pg16
```

### 4 — Migrate and create admin

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 5 — Pull Ollama models (for local LLM)

```bash
# Install Ollama: https://ollama.com/download
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

### 6 — Run backend

```bash
PYTHONPATH=. python manage.py runserver
# API: http://localhost:8000
# Admin: http://localhost:8000/admin
```

### 7 — Run Celery (background tasks)

```bash
# In a separate terminal
celery -A config worker --loglevel=info
```

### 8 — Run frontend

```bash
cd frontend
npm install --legacy-peer-deps
DISABLE_ESLINT_PLUGIN=true npm start
# UI: http://localhost:3000
```

---

## Project Structure

```
grant_proposal_ai/
│
├── backend/
│   ├── config/               # Django settings, URLs, Celery
│   ├── apps/
│   │   ├── documents/        # Upload, parse, OCR documents
│   │   ├── proposals/        # Generate, export, review proposals
│   │   ├── compliance/       # HIPAA, page limits, cert checks
│   │   └── llm/              # Multi-LLM router (Ollama/OpenAI/Claude)
│   │       └── providers/    # Individual provider implementations
│   ├── requirements.txt
│   └── manage.py
│
├── frontend/
│   └── src/
│       ├── pages/            # Dashboard, Documents, Proposals, Settings
│       ├── components/       # Layout, sidebar
│       └── utils/            # API client, helpers
│
├── docker-compose.yml
└── Makefile
```

---

## API Reference

All endpoints require JWT auth. Get a token:

```bash
curl -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "your-user", "password": "your-pass"}'
```

### Documents

| Method | Path | Description |
|---|---|---|
| `GET`  | `/api/documents/` | List documents |
| `POST` | `/api/documents/` | Upload document (multipart) |
| `GET`  | `/api/documents/{id}/` | Get document + blocks |
| `GET`  | `/api/documents/{id}/blocks/?type=table` | Get blocks by type |
| `POST` | `/api/documents/{id}/reprocess/` | Re-trigger parsing |
| `DELETE` | `/api/documents/{id}/` | Delete document |

### Proposals

| Method | Path | Description |
|---|---|---|
| `GET`  | `/api/proposals/` | List proposals |
| `POST` | `/api/proposals/generate/` | Create + start generation |
| `GET`  | `/api/proposals/{id}/` | Get proposal + sections |
| `GET`  | `/api/proposals/{id}/status/` | Poll generation status |
| `POST` | `/api/proposals/{id}/export/` | Export to DOCX |
| `GET`  | `/api/proposals/{id}/download/` | Download DOCX |
| `PATCH`| `/api/proposals/{id}/review/` | Save reviewer notes |
| `PATCH`| `/api/proposals/sections/{id}/` | Edit section content |
| `POST` | `/api/proposals/sections/{id}/regenerate/` | Regenerate with feedback |

### Compliance

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/compliance/{id}/check/` | Run compliance check |
| `GET`  | `/api/compliance/{id}/report/` | Get last report |

### LLM

| Method | Path | Description |
|---|---|---|
| `GET`  | `/api/llm/health/` | Check all providers |
| `GET`  | `/api/llm/providers/` | List providers + default |
| `GET`  | `/api/llm/models/?provider=ollama` | List models |
| `POST` | `/api/llm/test/` | Test generation |

---

## LLM Provider Guide

| Provider | Cost | Privacy | Best for |
|---|---|---|---|
| `ollama` | Free | 100% local | Development, sensitive data |
| `openai` | Pay per token | Cloud | Highest quality |
| `claude` | Pay per token | Cloud | Long documents, compliance |

Set default in `.env`:
```env
DEFAULT_LLM_PROVIDER=ollama   # or openai or claude
```

Override per proposal in the UI or API request.

---

## Environment Variables

```env
# Required
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://postgres:password@localhost:5432/grant_proposal_db
DEFAULT_LLM_PROVIDER=ollama

# Ollama (local — no key needed)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_LLM_MODEL=llama3.1:8b
OLLAMA_EMBED_MODEL=nomic-embed-text

# OpenAI (optional)
OPENAI_API_KEY=sk-...

# Claude (optional)
ANTHROPIC_API_KEY=sk-ant-...

# Redis (for Celery)
REDIS_URL=redis://localhost:6379/0
```

---

## Running Tests

```bash
cd backend
pytest apps/ -v
```

Tests mock all LLM provider calls — no running Ollama instance needed.
