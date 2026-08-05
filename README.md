# 🤖 Multi-Tenant Text-to-SQL and Document Chat Platform

<div align="center">

![Platform Banner](https://img.shields.io/badge/AI%20Platform-Text--to--SQL%20%26%20RAG-8be9fd?style=for-the-badge&logo=openai&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11+-bd93f9?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-50fa7b?style=for-the-badge&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-Vite+TypeScript-ff79c6?style=for-the-badge&logo=react&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-f1fa8c?style=for-the-badge)

**A production-grade, multi-tenant AI platform that lets you chat with your databases using natural language and query your documents with semantic search.**

[Frontend UI](#frontend-ui-port-5173) • [API Docs](#api-documentation-port-8000) • [Celery Flower](#celery-flower-port-5555) • [Architecture](#architecture) • [Setup](#setup-and-installation)

</div>

---

## 🌐 Live Services & Links

| Service | URL | Description |
|---------|-----|-------------|
| 🖥️ **Frontend UI** | [http://localhost:5173](http://localhost:5173) | ✅ React/Vite Chat Interface |
| ⚡ **Backend API** | [http://localhost:8000](http://localhost:8000) | ✅ FastAPI Application |
| 📖 **API Docs (Swagger)** | [http://localhost:8000/docs](http://localhost:8000/docs) | ✅ Interactive OpenAPI documentation |
| 🌸 **Celery Flower** | [http://localhost:5555](http://localhost:5555) | ✅ Task Queue Monitoring Dashboard |
| 🗄️ **MinIO Console** | [http://localhost:9001](http://localhost:9001) | ⚠️ Object Storage *(requires Docker)* |
| 📊 **Prometheus** | [http://localhost:9090](http://localhost:9090) | ⚠️ Metrics collection *(requires Docker)* |
| 📈 **Grafana** | [http://localhost:3000](http://localhost:3000) | ⚠️ Metrics visualization *(requires Docker)* |

> **Note:** The core services (Frontend, Backend, Flower) run natively via Python and Node. The extra services (MinIO, Prometheus, Grafana) require Docker Desktop to be running.

---

## 🔑 Key Features

- 🗣️ **Natural Language to SQL** — Ask questions in plain English, get SQL queries and formatted results
- 📄 **Document Chat (RAG)** — Upload PDFs, CSVs, Word documents and ask questions about them
- 🔀 **Hybrid Chat** — Intelligently routes queries between SQL and RAG based on context
- 🏢 **Multi-Tenancy** — Full tenant isolation: each tenant has separate data, connections, and configs
- 🔐 **JWT Authentication** — Secure Bearer token authentication with role-based access control
- ⚙️ **Schema-Aware AI** — Automatically syncs and caches database schemas for accurate SQL generation
- 🛡️ **SQL Security** — SQLGlot-based query validation prevents injection and dangerous operations
- 🚀 **Async Architecture** — Built on FastAPI + SQLAlchemy async for high throughput
- 📦 **Background Tasks** — Celery workers for document processing and schema sync
- 📊 **Full Observability** — OpenTelemetry, Prometheus metrics, Grafana dashboards

---

## 🖼️ Screenshots

### Frontend Chat Interface (localhost:5173)
> A premium dark-themed UI with glassmorphism effects, featuring the chat interface, database connection modal, document upload, and settings panel.

![Frontend UI](docs/images/frontend_ui.jpg)

**Chat View** — Send natural language queries to your databases or documents:
- Type any question in plain English (e.g. "Show me all orders from last month")
- The AI generates a SQL query, executes it, and returns formatted results
- Switch between SQL mode, RAG mode, or Hybrid mode

**Connect Database Modal** — Connect any database:
- Supports PostgreSQL, MySQL, SQL Server, Oracle
- Automatic schema discovery and caching
- Test connection before saving

**Upload Documents View** — Upload files to build a knowledge base:
- Supports PDF, CSV, DOCX, XLSX formats
- Automatic chunking, embedding, and vector indexing
- Chat with documents using semantic search

**Settings Panel** — Configure the AI:
- Choose LLM provider (OpenAI GPT-4, Anthropic Claude, Local Ollama)
- Set API keys securely
- Customize system prompt behavior

---

### API Documentation (localhost:8000/docs)
> Full interactive OpenAPI/Swagger documentation auto-generated from all 40+ endpoints.

![API Documentation](docs/images/api_docs.jpg)

**Endpoint Groups:**
```
/api/v1/auth/          — Register, login, token refresh, logout
/api/v1/tenants/       — Tenant management and configuration
/api/v1/connections/   — Database connection management
/api/v1/query/         — Text-to-SQL query execution
/api/v1/knowledge/     — Knowledge base and document management
/api/v1/chat/          — Chat sessions (SQL, RAG, Hybrid)
/health                — Health check endpoint
```

---

### Celery Flower Dashboard (localhost:5555)
> Real-time monitoring of background task workers. Shows active tasks, task history, worker status, and task statistics.

![Celery Flower](docs/images/celery_flower.jpg)

**Registered Tasks:**
- `document.process` — Processes uploaded documents (parse → chunk → embed → index)
- `schema.sync` — Syncs database schemas for connected databases

---

### MinIO Object Storage (localhost:9001) — *Requires Docker*
> S3-compatible object storage for uploaded documents. Default credentials: `minioadmin` / `minioadmin`.

![MinIO Console](docs/images/minio_console.jpg)

---

### Prometheus (localhost:9090) — *Requires Docker*
> Collects metrics from the FastAPI backend including request rates, latency histograms, error rates, and custom business metrics.

![Prometheus Dashboard](docs/images/prometheus_dashboard.jpg)

---

### Grafana (localhost:3000) — *Requires Docker*
> Visualizes Prometheus metrics with pre-built dashboards. Default credentials: `admin` / `admin`.

![Grafana Dashboard](docs/images/grafana_dashboard.jpg)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     CLIENT LAYER                                  │
│  React + Vite + TypeScript (localhost:5173)                       │
└──────────────────────────┬──────────────────────────────────────┘
                           │ REST API / JSON
┌──────────────────────────▼──────────────────────────────────────┐
│                     API GATEWAY (FastAPI)                         │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Auth JWT │ Tenant Middleware │ Rate Limiting │ CORS     │    │
│  └─────────────────────────────────────────────────────────┘    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐   │
│  │  /auth   │ │ /query   │ │ /chat    │ │  /knowledge      │   │
│  │ /tenants │ │ /connect │ │ hybrid   │ │  /documents      │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
        ┌──────────────────┼─────────────────────┐
        │                  │                      │
┌───────▼──────┐  ┌────────▼──────┐  ┌──────────▼────────┐
│ Text-to-SQL  │  │   RAG Agent   │  │  Hybrid Agent     │
│   Agent      │  │               │  │                   │
│ (LangGraph)  │  │  (LangGraph)  │  │  (LangGraph)      │
│              │  │               │  │                   │
│ SQLGlot      │  │ Vector Search │  │ Route + Combine   │
│ Validation   │  │ Retrieval     │  │                   │
└───────┬──────┘  └────────┬──────┘  └─────────┬─────────┘
        │                  │                     │
┌───────▼──────────────────▼─────────────────────▼─────────┐
│                    SERVICE LAYER                            │
│  QueryService │ DocumentService │ ChatService              │
└───────┬──────────────────┬──────────────────────┬─────────┘
        │                  │                       │
┌───────▼──────┐  ┌────────▼──────┐  ┌────────────▼────────┐
│  PostgreSQL  │  │    pgvector   │  │   Redis Cache       │
│  (tenants,   │  │ (embeddings,  │  │ (schema cache,      │
│   schemas,   │  │  documents)   │  │  sessions, rate     │
│   sessions)  │  │               │  │  limits)            │
└──────────────┘  └───────────────┘  └─────────────────────┘

                  ┌───────────────────────────────────────┐
                  │        BACKGROUND WORKERS             │
                  │  Celery Workers + Redis Broker        │
                  │  Flower Monitoring (port 5555)        │
                  │  document.process | schema.sync       │
                  └───────────────────────────────────────┘

                  ┌───────────────────────────────────────┐
                  │       OBSERVABILITY STACK             │
                  │  OpenTelemetry │ Prometheus │ Grafana  │
                  └───────────────────────────────────────┘
```

---

## 📂 Project Structure

```
Multi-Tenant-Text-to-SQL-and-Document-Chat-Platform/
│
├── 📁 backend/                     # FastAPI Backend Application
│   ├── 📁 app/
│   │   ├── 📁 api/v1/routers/      # API endpoint handlers
│   │   │   ├── auth.py             # Authentication routes
│   │   │   ├── chat.py             # Chat session routes
│   │   │   ├── connections.py      # DB connection routes
│   │   │   ├── knowledge_bases.py  # Knowledge base routes
│   │   │   ├── queries.py          # Text-to-SQL routes
│   │   │   └── tenants.py          # Tenant management routes
│   │   ├── 📁 agents/
│   │   │   ├── text_to_sql/        # LangGraph SQL Agent
│   │   │   ├── rag/                # LangGraph RAG Agent
│   │   │   └── hybrid/             # LangGraph Hybrid Agent
│   │   ├── 📁 core/
│   │   │   ├── config.py           # Pydantic settings management
│   │   │   ├── logging.py          # Structlog configuration
│   │   │   ├── security.py         # JWT & password hashing
│   │   │   └── exceptions.py       # Custom exception classes
│   │   ├── 📁 models/              # SQLAlchemy ORM models
│   │   ├── 📁 schemas/             # Pydantic request/response models
│   │   ├── 📁 services/            # Business logic layer
│   │   ├── 📁 repositories/        # Database access layer
│   │   ├── 📁 workers/             # Celery task definitions
│   │   ├── 📁 middleware/          # FastAPI middleware
│   │   └── main.py                 # Application factory
│   │
│   ├── 📁 docker/                  # Docker configuration files
│   ├── docker-compose.yml          # Full stack orchestration
│   ├── Dockerfile                  # Backend container definition
│   ├── pyproject.toml              # Python dependencies
│   ├── .env                        # Environment variables (local)
│   └── .env.example                # Example environment template
│
├── 📁 frontend/                    # React/Vite Frontend Application
│   ├── 📁 src/
│   │   ├── App.tsx                 # Main app component with routing
│   │   ├── api.ts                  # API service layer
│   │   ├── App.css                 # App-specific styles
│   │   └── index.css               # Global design system & tokens
│   ├── package.json
│   └── vite.config.ts
│
├── run_project.bat                 # One-click startup script (Windows)
└── README.md                       # This file
```

---

## 🚀 Setup and Installation

### Prerequisites

- Python 3.11+
- Node.js 18+
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) *(required for MinIO, Prometheus, Grafana)*
- Redis *(required for Celery — or use Docker)*

---

### Option A: Quick Start (Frontend + Backend Only)

```bash
# 1. Clone the repository
git clone https://github.com/Toqa10/Multi-Tenant-Text-to-SQL-and-Document-Chat-Platform.git
cd "Multi-Tenant-Text-to-SQL-and-Document-Chat-Platform"

# 2. On Windows, just double-click:
run_project.bat

# OR run manually:

# Terminal 1 — Backend
cd backend
pip install -e .
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 — Celery Flower
cd backend
python -m celery -A app.workers.celery_app flower --port=5555

# Terminal 3 — Frontend
cd frontend
npm install
npm run dev -- --host
```

---

### Option B: Full Stack with Docker (All Services)

```bash
cd backend

# Copy and configure environment
cp .env.example .env
# Edit .env with your OpenAI API key and other settings

# Start ALL services (Postgres, Redis, MinIO, Prometheus, Grafana, Backend, Celery, Flower)
docker compose up -d

# Check status
docker compose ps
```

Once running, all 8 services will be available at the URLs listed above.

---

### Environment Configuration (`.env`)

```env
# Core
APP_ENV=development
SECRET_KEY=your-super-secret-key-here
LOG_LEVEL=INFO

# Database (PostgreSQL)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/aisql

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# OpenAI
OPENAI_API_KEY=sk-your-openai-key-here

# MinIO (Object Storage)
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_NAME=documents
```

---

## 🛠️ API Reference

### Authentication

```http
POST /api/v1/auth/register    # Register new tenant/user
POST /api/v1/auth/login       # Login and get JWT token
POST /api/v1/auth/refresh     # Refresh access token
POST /api/v1/auth/logout      # Logout (invalidate token)
```

### Text-to-SQL

```http
POST /api/v1/query/           # Execute natural language query
GET  /api/v1/connections/     # List database connections
POST /api/v1/connections/     # Add new database connection
GET  /api/v1/connections/{id}/schema  # Get synced schema
```

### Document Chat (RAG)

```http
POST /api/v1/knowledge/       # Create knowledge base
POST /api/v1/knowledge/{id}/documents  # Upload document
GET  /api/v1/knowledge/{id}/documents  # List documents
```

### Chat

```http
POST /api/v1/chat/sql         # SQL-only chat session
POST /api/v1/chat/rag         # RAG-only chat session
POST /api/v1/chat/hybrid      # Hybrid auto-routing chat
GET  /api/v1/chat/sessions    # List chat history
```

### System

```http
GET  /health                  # Health check
GET  /metrics                 # Prometheus metrics
```

---

## 🧰 Technology Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 18, Vite, TypeScript, Lucide Icons |
| **Styling** | Vanilla CSS, CSS Custom Properties, Glassmorphism |
| **Backend** | FastAPI, Python 3.11+, Uvicorn |
| **ORM** | SQLAlchemy 2.0 (async), Alembic migrations |
| **AI Agents** | LangGraph, LangChain, OpenAI GPT-4 |
| **SQL Security** | SQLGlot (query parsing & validation) |
| **Vector DB** | pgvector (PostgreSQL extension) |
| **Task Queue** | Celery + Redis broker |
| **Task Monitoring** | Celery Flower |
| **Object Storage** | MinIO (S3-compatible) |
| **Cache** | Redis (schema cache, rate limiting) |
| **Observability** | OpenTelemetry, Prometheus, Grafana |
| **Logging** | structlog (structured JSON logging) |
| **Auth** | JWT Bearer tokens, bcrypt password hashing |
| **Containerization** | Docker, Docker Compose |
| **Database** | PostgreSQL 15+ with pgvector extension |

---

## 🔒 Security Features

- ✅ **JWT Authentication** with configurable expiry
- ✅ **Tenant Isolation** — all queries scoped to tenant ID
- ✅ **SQL Injection Prevention** — SQLGlot validates all generated queries
- ✅ **Rate Limiting** — Redis-backed per-tenant rate limits
- ✅ **Password Hashing** — bcrypt with salt
- ✅ **CORS Configuration** — whitelist-based origin control
- ✅ **Input Validation** — Pydantic v2 strict validation on all inputs
- ✅ **Dangerous Query Blocking** — DROP, TRUNCATE, ALTER blocked by default

---

## 📊 Monitoring & Observability

### Prometheus Metrics (localhost:9090)
Collected metrics include:
- `http_requests_total` — Request count by method/path/status
- `http_request_duration_seconds` — Latency histograms
- `celery_tasks_total` — Task execution counts
- `db_query_duration_seconds` — Database query latency
- `tenant_active_connections` — Per-tenant active connections

### Grafana Dashboards (localhost:3000)
Pre-configured dashboards for:
- API Performance Overview
- Celery Worker Health
- Database Query Analytics
- Tenant Usage Report

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License.

---

<div align="center">

**Built with ❤️ using FastAPI, LangGraph, and React**

[🔝 Back to top](#-multi-tenant-text-to-sql-and-document-chat-platform)

</div>
