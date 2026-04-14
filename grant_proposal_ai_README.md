# Healthcare Grant Proposal AI

An AI-powered platform that automates healthcare grant and RFP proposal responses.
Processes PDF, DOCX, Excel, and scanned documents, then generates compliant proposal
sections using your choice of LLM — all through a single unified interface.

**Stack:** Django 5 · Django REST Framework · React · PostgreSQL/pgvector · Vertex AI / Ollama / OpenAI / Claude

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Document Processing Pipeline](#document-processing-pipeline)
- [LLM Provider Guide](#llm-provider-guide)
- [Vertex AI Setup](#vertex-ai-setup)
- [Proposal Generation](#proposal-generation)
- [Compliance Checker](#compliance-checker)
- [API Reference](#api-reference)
- [Environment Variables](#environment-variables)
- [Database Setup](#database-setup)
- [Running Tests](#running-tests)
- [Docker](#docker)

---

## Features

| Feature | Description |
|---|---|
| **Multi-format document processing** | PDF, DOCX, Excel, scanned images (OCR) → structured content blocks |
| **Synthetic parsing pipeline** | Routes text / tables / images to the right extractor automatically |
| **Multi-LLM switch** | Vertex AI · Ollama · OpenAI GPT-4o · Claude — swap per request |
| **Healthcare-specific generation** | Strategy-aware prompts per section type (technical, past perf, budget, HIPAA) |
| **Compliance checking** | HIPAA language, page limits, certifications, fabrication detection |
| **DOCX export** | Formatted Word document ready for submission |
| **React UI** | Dashboard, document manager, proposal builder, reviewer workflow |

---

## Architecture

```
Uploaded Document (PDF / DOCX / Excel / Scanned Image)
        │
        ▼
┌─────────────────────────────────────────────────────┐
│  Synthetic Parsing Pipeline  (apps/documents/)       │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │  PyMuPDF │  │pdfplumber│  │   pytesseract    │   │
│  │ (text)   │  │ (tables) │  │  (OCR / images)  │   │
│  └──────────┘  └──────────┘  └──────────────────┘   │
│           ↓ routes each block type ↓                 │
│        LLM metadata extraction (structured JSON)     │
└────────────────────────┬────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│  Multi-LLM Router  (apps/llm/)                       │
│  ┌──────────┐ ┌──────────┐ ┌────────┐ ┌──────────┐  │
│  │ Vertex AI│ │  Ollama  │ │OpenAI  │ │  Claude  │  │
│  │ (Gemini) │ │ (local)  │ │ GPT-4o │ │          │  │
│  └──────────┘ └──────────┘ └────────┘ └──────────┘  │
└────────────────────────┬────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│  Proposal Generator  (apps/proposals/)               │
│  Strategy detection → section prompts → generation   │
│  Executive summary → DOCX export                     │
└────────────────────────┬────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│  Compliance Checker  (apps/compliance/)              │
│  HIPAA · page limits · certifications · fabrication  │
└─────────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | >= 3.11 | |
| Node.js | >= 18 | For React frontend |
| PostgreSQL | >= 15 | With pgvector extension |
| Docker | any | Recommended for database |
| Tesseract OCR | any | macOS: `brew install tesseract tesseract-lang` |

### 1 — Clone the repository

```bash
git clone https://github.com/SugandhaAgrawal-dev/grant-proposal-ai.git
cd grant-proposal-ai
```

### 2 — Backend setup

```bash
cd backend

# Create and activate virtual environment
python3.11 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env
# Edit .env — minimum required: DATABASE_URL, SECRET_KEY, DEFAULT_LLM_PROVIDER
```

### 3 — Start PostgreSQL with pgvector (Docker)

```bash
docker run -d \
  --name grant_proposal_db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=grant_proposal_db \
  -p 5432:5432 \
  pgvector/pgvector:pg16
```

### 4 — Run migrations and create admin user

```bash
cd backend
python manage.py migrate
python manage.py createsuperuser
```

### 5 — Configure your LLM provider

**Option A — Vertex AI (recommended for production):**

```bash
# Install Google Cloud SDK
brew install google-cloud-sdk              # macOS
# or: https://cloud.google.com/sdk/docs/install

# Authenticate
gcloud auth application-default login

# Set in .env
DEFAULT_LLM_PROVIDER=vertex
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
VERTEX_LLM_MODEL=gemini-1.5-pro-002
VERTEX_EMBED_MODEL=text-embedding-004
```

**Option B — Ollama (local, free, private):**

```bash
# Install Ollama: https://ollama.com/download
ollama pull llama3.1:8b
ollama pull nomic-embed-text

# Set in .env
DEFAULT_LLM_PROVIDER=ollama
```

### 6 — Start the backend

```bash
# Terminal 1 — Django API server
cd backend
PYTHONPATH=. python manage.py runserver
# API docs: http://localhost:8000/api/
# Admin:    http://localhost:8000/admin/
```

```bash
# Terminal 2 — Celery worker (background tasks)
cd backend
celery -A config worker --loglevel=info
```

### 7 — Start the frontend

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
│   ├── config/
│   │   ├── settings.py              # Django + LLM config
│   │   ├── urls.py                  # Root URL routing
│   │   └── celery.py                # Background task queue
│   │
│   ├── apps/
│   │   ├── documents/
│   │   │   ├── models.py            # UploadedDocument, ParsedBlock
│   │   │   ├── parser.py            # Synthetic parsing pipeline
│   │   │   ├── serializers.py       # DRF serializers
│   │   │   ├── views.py             # Upload, list, reprocess endpoints
│   │   │   ├── tasks.py             # Background Celery tasks
│   │   │   └── urls.py
│   │   │
│   │   ├── proposals/
│   │   │   ├── models.py            # OrganizationProfile, GrantProposal, ProposalSection
│   │   │   ├── generator.py         # Section generation with strategy prompts
│   │   │   ├── exporter.py          # DOCX export
│   │   │   ├── serializers.py
│   │   │   ├── views.py             # Generate, review, download endpoints
│   │   │   ├── tasks.py             # Background generation tasks
│   │   │   └── urls.py
│   │   │
│   │   ├── compliance/
│   │   │   ├── checker.py           # HIPAA, page limits, certs, fabrication
│   │   │   ├── views.py             # Run check, get report endpoints
│   │   │   └── urls.py
│   │   │
│   │   └── llm/
│   │       ├── base.py              # Abstract BaseLLMProvider
│   │       ├── router.py            # LLMRouter — unified interface
│   │       ├── providers/
│   │       │   ├── vertex.py        # Google Vertex AI / Gemini
│   │       │   ├── ollama.py        # Ollama (local)
│   │       │   ├── openai.py        # OpenAI GPT-4o
│   │       │   └── claude.py        # Anthropic Claude
│   │       ├── views.py             # Health check, list models, test
│   │       └── urls.py
│   │
│   ├── requirements.txt
│   ├── manage.py
│   └── pyproject.toml
│
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── Dashboard.js         # Stats + recent activity
│       │   ├── DocumentsPage.js     # Document list and management
│       │   ├── UploadPage.js        # Drag-and-drop file upload
│       │   ├── ProposalsPage.js     # Proposal list
│       │   ├── ProposalDetail.js    # Sections, compliance, download
│       │   ├── NewProposal.js       # Create proposal from RFP
│       │   ├── OrgProfilePage.js    # Health system profile
│       │   └── LLMSettingsPage.js   # Provider health and testing
│       ├── components/
│       │   └── layout/Layout.js     # Sidebar navigation
│       └── utils/
│           ├── api.js               # Axios API client
│           └── helpers.js           # Formatters, badges, utilities
│
├── docker-compose.yml
├── Makefile
└── README.md
```

---

## Document Processing Pipeline

The synthetic parser routes each content type to the right extractor:

```
Uploaded file
    │
    ├── PDF  → PyMuPDF  (text blocks)
    │        → pdfplumber (tables → markdown)
    │        → pytesseract (embedded images → OCR)
    │
    ├── DOCX → python-docx (paragraphs + tables)
    │
    ├── Excel → openpyxl (sheets → markdown tables)
    │
    └── Image → pytesseract (full page OCR)
```

Each block is saved as a `ParsedBlock` record with its type (`text`, `table`, `image`, `metadata`). The LLM then extracts structured metadata (deadline, agency, budget limit, certifications) from the full text.

**Supported file types:**

| Type | Extensions | Extractor |
|---|---|---|
| PDF | `.pdf` | PyMuPDF + pdfplumber + OCR fallback |
| Word | `.docx` | python-docx |
| Excel | `.xlsx` | openpyxl |
| Scanned | `.png`, `.jpg`, `.tiff` | pytesseract OCR |

---

## LLM Provider Guide

The `LLMRouter` provides a single interface across all providers. Switch by setting `DEFAULT_LLM_PROVIDER` in `.env` or passing `provider=` per API request.

| Provider | Key | Cost | Privacy | Context | Best for |
|---|---|---|---|---|---|
| **Vertex AI** | `vertex` | Pay per char | HIPAA-eligible | 1M tokens | Production healthcare data |
| **Ollama** | `ollama` | Free | 100% local | 8K–128K | Development, private data |
| **OpenAI** | `openai` | Pay per token | Cloud | 128K | Highest raw quality |
| **Claude** | `claude` | Pay per token | Cloud | 200K | Long docs, compliance |

### Switching providers

```env
# .env
DEFAULT_LLM_PROVIDER=vertex   # or ollama / openai / claude
```

Or override per API request:

```json
POST /api/proposals/generate/
{
  "llm_provider": "vertex",
  "title": "DHCS Medi-Cal RFP Response",
  ...
}
```

### Embeddings

For vector search, embeddings always use one of:
- `text-embedding-004` (Vertex AI) — 768-dim, HIPAA-eligible
- `nomic-embed-text` (Ollama) — 768-dim, free and local

Both are compatible with the pgvector column — no schema changes needed when switching.

---

## Vertex AI Setup

Vertex AI / Gemini is the recommended LLM for production healthcare environments because it is HIPAA-eligible, VPC-SC compatible, and supports enterprise data residency controls.

### Step 1 — Enable the Vertex AI API

```bash
gcloud services enable aiplatform.googleapis.com \
  --project=your-gcp-project-id
```

### Step 2 — Authenticate

**Option A — Application Default Credentials (development):**

```bash
gcloud auth application-default login
```

**Option B — Service account key (CI/CD or server):**

```bash
# Create service account
gcloud iam service-accounts create grant-proposal-ai \
  --display-name="Grant Proposal AI"

# Grant Vertex AI user role
gcloud projects add-iam-policy-binding your-gcp-project-id \
  --member="serviceAccount:grant-proposal-ai@your-gcp-project-id.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"

# Create and download key
gcloud iam service-accounts keys create key.json \
  --iam-account=grant-proposal-ai@your-gcp-project-id.iam.gserviceaccount.com
```

**Option C — Workload Identity (Cloud Run / GKE):**

No key file needed — automatic credential injection.

### Step 3 — Configure .env

```env
DEFAULT_LLM_PROVIDER=vertex
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-central1
VERTEX_LLM_MODEL=gemini-1.5-pro-002
VERTEX_EMBED_MODEL=text-embedding-004
GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json   # only if using service account
```

### Step 4 — Verify

```bash
PYTHONPATH=. python -c "
import asyncio, os
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
import django; django.setup()
from apps.llm.router import LLMRouter
router = LLMRouter(provider='vertex')
result = asyncio.run(router.health_check())
print(result)
"
```

### Available Gemini models on Vertex AI

| Model | Context | Speed | Best for |
|---|---|---|---|
| `gemini-1.5-pro-002` | 1M tokens | Medium | Highest quality, long RFPs |
| `gemini-1.5-flash-002` | 1M tokens | Fast | Cost-effective, most tasks |
| `gemini-2.0-flash-001` | 1M tokens | Fastest | Latest model, strong reasoning |
| `gemini-1.0-pro-002` | 32K tokens | Medium | Stable, lower cost |

---

## Proposal Generation

The generator uses strategy-aware prompting — each section type gets a different system prompt tuned for that section's structure and tone.

### Section strategies

| Section keyword | Strategy | Prompt guidance added |
|---|---|---|
| "technical approach", "methodology" | `technical` | Sub-headings per component, numbered steps, timeline |
| "management plan" | `management` | Org structure, roles, governance, communication plan |
| "past performance", "relevant experience" | `past_performance` | Agency → Contract Value → Scope → Role → Outcomes format |
| "staffing plan", "key personnel" | `staffing` | FTE table, bios, retention/succession |
| "budget", "cost" | `budget` | Line-item structure: Personnel/Fringe/Travel/Equipment/Indirect |
| "executive summary" | `executive_summary` | Need → Solution → Differentiators → Commitment |
| "data security", "hipaa", "privacy" | `data_security` | AES-256, TLS 1.3, BAA, HITRUST, SOC 2, incident response |
| anything else | `default` | Clear headings, specificity, evidence-based |

### Creating a proposal via API

```bash
# 1. Upload your RFP document
curl -X POST http://localhost:8000/api/documents/ \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@dhcs_rfp_2025.pdf" \
  -F "name=DHCS Medi-Cal RFP 2025"

# 2. Create organisation profile (once)
curl -X POST http://localhost:8000/api/proposals/organisations/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Valley Health System",
    "service_area": "Santa Clara County, CA",
    "certifications": ["HIPAA", "HITRUST", "SOC 2"],
    "mission_statement": "Providing quality healthcare to all community members."
  }'

# 3. Generate proposal
curl -X POST http://localhost:8000/api/proposals/generate/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Response to DHCS Medi-Cal Population Health RFP 2025",
    "rfp_document_id": "<document-uuid>",
    "org_profile_id": "<org-uuid>",
    "llm_provider": "vertex",
    "sections": [
      {"name": "Executive Summary",  "requirements": "Overview of programme and qualifications.", "page_limit": 3,  "order": 1},
      {"name": "Technical Approach", "requirements": "Describe your care coordination model.", "page_limit": 10, "order": 2},
      {"name": "Past Performance",   "requirements": "Three examples from the past 5 years.",  "page_limit": 6,  "order": 3},
      {"name": "Budget",             "requirements": "Detailed line-item budget with narrative.", "page_limit": 5, "order": 4}
    ]
  }'

# 4. Poll status until complete
curl http://localhost:8000/api/proposals/<id>/status/ \
  -H "Authorization: Bearer $TOKEN"

# 5. Export and download DOCX
curl -X POST http://localhost:8000/api/proposals/<id>/export/ \
  -H "Authorization: Bearer $TOKEN"

curl http://localhost:8000/api/proposals/<id>/download/ \
  -H "Authorization: Bearer $TOKEN" \
  --output proposal.docx
```

### Regenerating a section with feedback

```bash
curl -X POST http://localhost:8000/api/proposals/sections/<section-id>/regenerate/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "reviewer_feedback": "Add contract values to all past performance examples. Strengthen the HIPAA paragraph.",
    "llm_provider": "vertex"
  }'
```

---

## Compliance Checker

Validates generated sections against:

| Check | Type | Severity |
|---|---|---|
| PHI/EHR mentioned without HIPAA addressed | `hipaa` | Error |
| Section exceeds page limit | `page_limit` | Error |
| Required certification not mentioned | `missing_cert` | Warning |
| Fabricated statistics or claims | `fabrication` | Error |
| RFP requirements not addressed | `missing_req` | Warning |

```bash
# Run compliance check
curl -X POST http://localhost:8000/api/compliance/<proposal-id>/check/ \
  -H "Authorization: Bearer $TOKEN"

# Response
{
  "passed": false,
  "errors": 1,
  "warnings": 2,
  "summary": "1 error found. Resolve before submission.",
  "issues": [
    {
      "section": "Technical Approach",
      "issue_type": "hipaa",
      "severity": "error",
      "message": "Section references patient data but does not address HIPAA compliance.",
      "suggestion": "Add a paragraph confirming HIPAA compliance and BAA availability."
    }
  ]
}
```

---

## API Reference

All endpoints require JWT authentication. Obtain a token:

```bash
curl -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "your-user", "password": "your-pass"}'

# Returns: {"access": "<token>", "refresh": "<token>"}
# Use: Authorization: Bearer <token>
```

### Documents — `/api/documents/`

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/documents/` | List all documents |
| `POST` | `/api/documents/` | Upload document (multipart/form-data) |
| `GET` | `/api/documents/{id}/` | Get document details + parsed blocks |
| `GET` | `/api/documents/{id}/blocks/` | Get parsed blocks (filter: `?type=table`) |
| `POST` | `/api/documents/{id}/reprocess/` | Re-trigger parsing |
| `DELETE` | `/api/documents/{id}/` | Delete document |

### Proposals — `/api/proposals/`

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/proposals/` | List all proposals |
| `POST` | `/api/proposals/generate/` | Create proposal and start generation |
| `GET` | `/api/proposals/{id}/` | Get proposal with all sections |
| `GET` | `/api/proposals/{id}/status/` | Poll generation progress |
| `POST` | `/api/proposals/{id}/export/` | Trigger DOCX export |
| `GET` | `/api/proposals/{id}/download/` | Download DOCX file |
| `PATCH` | `/api/proposals/{id}/review/` | Save reviewer notes and update status |
| `DELETE` | `/api/proposals/{id}/` | Delete proposal |
| `PATCH` | `/api/proposals/sections/{id}/` | Manually edit section content |
| `POST` | `/api/proposals/sections/{id}/regenerate/` | Regenerate section with feedback |

### Organisation Profiles — `/api/proposals/organisations/`

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/proposals/organisations/` | List profiles |
| `POST` | `/api/proposals/organisations/` | Create profile |
| `GET` | `/api/proposals/organisations/{id}/` | Get profile |
| `PATCH` | `/api/proposals/organisations/{id}/` | Update profile |
| `DELETE` | `/api/proposals/organisations/{id}/` | Delete profile |

### Compliance — `/api/compliance/`

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/compliance/{id}/check/` | Run full compliance check |
| `GET` | `/api/compliance/{id}/report/` | Get last compliance report |

### LLM — `/api/llm/`

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/llm/health/` | Check all provider statuses |
| `GET` | `/api/llm/providers/` | List providers and default |
| `GET` | `/api/llm/models/?provider=vertex` | List models for a provider |
| `POST` | `/api/llm/test/` | Test generation with a prompt |

---

## Environment Variables

```env
# ── Django ─────────────────────────────────────────────────────────────
SECRET_KEY=your-secret-key-change-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# ── Database ────────────────────────────────────────────────────────────
DATABASE_URL=postgresql://postgres:password@localhost:5432/grant_proposal_db

# ── LLM Provider ────────────────────────────────────────────────────────
# Options: vertex | ollama | openai | claude
DEFAULT_LLM_PROVIDER=vertex

# Vertex AI / Gemini (HIPAA-eligible, recommended for production)
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-central1
VERTEX_LLM_MODEL=gemini-1.5-pro-002
VERTEX_EMBED_MODEL=text-embedding-004
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# Ollama (local — no key needed)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_LLM_MODEL=llama3.1:8b
OLLAMA_EMBED_MODEL=nomic-embed-text
OLLAMA_TIMEOUT=120

# OpenAI (optional)
OPENAI_API_KEY=sk-your-openai-key
OPENAI_MODEL=gpt-4o

# Anthropic Claude (optional)
ANTHROPIC_API_KEY=sk-ant-your-key
ANTHROPIC_MODEL=claude-opus-4-5

# ── Redis (Celery task queue) ───────────────────────────────────────────
REDIS_URL=redis://localhost:6379/0

# ── File uploads ────────────────────────────────────────────────────────
MEDIA_ROOT=media/
MAX_UPLOAD_SIZE_MB=50

# ── CORS ────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS=["http://localhost:3000"]
```

---

## Database Setup

The project uses PostgreSQL with the pgvector extension for future vector similarity search on document chunks.

```bash
# Docker (easiest — pgvector pre-installed)
docker run -d \
  --name grant_proposal_db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=grant_proposal_db \
  -p 5432:5432 \
  pgvector/pgvector:pg16

# Manual (if using existing Postgres)
psql -U postgres -d grant_proposal_db \
  -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

**Database schema overview:**

| Table | Purpose |
|---|---|
| `documents_uploadeddocument` | Uploaded RFP/grant files with parsing status |
| `documents_parsedblock` | Individual content blocks (text, table, image, metadata) |
| `proposals_organizationprofile` | Health system profiles reused across proposals |
| `proposals_grantproposal` | Proposal drafts with status and LLM provider |
| `proposals_proposalsection` | Individual generated sections with content |

---

## Running Tests

```bash
cd backend
source .venv/bin/activate
pytest apps/ -v
```

All LLM provider calls are mocked — tests run without a live Ollama or Vertex AI connection.

```bash
# Run specific test file
pytest apps/llm/tests/ -v

# Run with coverage report
pytest apps/ --cov=apps --cov-report=term-missing
```

---

## Docker

Run the full stack with Docker Compose:

```bash
# Start all services (Postgres, Redis, Ollama, Django, Celery, React)
docker compose up -d

# Check status
docker compose ps

# View Django logs
docker compose logs backend -f

# Pull Ollama models inside container
docker compose exec ollama ollama pull llama3.1:8b
docker compose exec ollama ollama pull nomic-embed-text

# Stop everything
docker compose down
```

---

## Makefile Commands

```bash
make setup          # First-time setup (venv + npm install)
make migrate        # Run Django migrations
make superuser      # Create Django admin user
make run-backend    # Start Django dev server
make run-frontend   # Start React dev server
make run-celery     # Start Celery worker
make test           # Run test suite
make lint           # Run ruff linter
make pull-models    # Pull Ollama models
make docker-up      # Start Docker Compose stack
make docker-down    # Stop Docker Compose stack
```

---

## System Requirements

| Component | macOS | Linux |
|---|---|---|
| Tesseract OCR | `brew install tesseract tesseract-lang` | `apt install tesseract-ocr` |
| LibreOffice (PDF export) | `brew install --cask libreoffice` | `apt install libreoffice` |
| PostgreSQL | `brew install postgresql@16` | `apt install postgresql-16` |
| Ollama | [ollama.com/download](https://ollama.com/download) | `curl -fsSL https://ollama.com/install.sh \| sh` |
| Google Cloud SDK | `brew install google-cloud-sdk` | [cloud.google.com/sdk](https://cloud.google.com/sdk/docs/install) |
