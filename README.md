# Multi-Tenant Text-to-SQL and Document Chat Platform (NexusAI)

Production-grade, secure, multi-tenant SaaS platform enabling organizations to query live databases (Text-to-SQL) and unstructured business documents (RAG) through a single AI conversational interface.

---

## Key Features

- 🔒 **Multi-Tenancy & RBAC**: Tenant isolation on every query, role-based access control, table, column, and row-level security (RLS).
- ⚡ **Runtime Database Connections**: Dynamic connections to PostgreSQL, MySQL, SQL Server, and Oracle. Schema metadata caching only—no customer business data is copied.
- 🛡️ **SQL Security Engine**: SQLGlot validation layer blocking destructive statements (`DROP`, `DELETE`, `UPDATE`, `ALTER`, `TRUNCATE`), multi-statements, comments, admin schemas (`pg_catalog`), and enforcing read-only transactions with row-level security filter injection.
- 📄 **Document RAG Pipeline**: Processing for PDF, DOCX, XLSX, CSV, and TXT documents. Automatic chunking, vector embedding generation, pgvector storage with HNSW index, and citation generation.
- 🤖 **LangGraph Hybrid Chat Agent**: Intent classifier, source selector (DB / Document / Hybrid), parallel retrieval, grounded answer generation, and streaming (SSE) support.
- 📊 **Observability & Monitoring**: OpenTelemetry tracing, Prometheus metrics (`/metrics`), Grafana dashboards, and structured JSON logs.

---

## Tech Stack

- **Backend**: Python 3.12+, FastAPI, SQLAlchemy 2.x (Async), Alembic, Pydantic v2
- **Database**: PostgreSQL 16 with `pgvector`
- **Agents & AI**: LangGraph, LangChain, OpenAI (`gpt-4o`, `text-embedding-3-small`), SQLGlot
- **Queue & Cache**: Redis 7, Celery
- **Storage**: MinIO Object Storage
- **Infrastructure**: Docker & Docker Compose

---

## Quick Start (Docker Compose)

### 1. Environment Setup
Copy `.env.example` to `.env` and configure your credentials:
```bash
cp .env.example .env
```

### 2. Start Services
Run the full production stack using Docker Compose:
```bash
docker compose up --build -d
```

Services will be available at:
- **Web UI & Dashboard**: [http://localhost:8000](http://localhost:8000)
- **API Documentation (OpenAPI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Celery Flower Dashboard**: [http://localhost:5555](http://localhost:5555)
- **MinIO Console**: [http://localhost:9001](http://localhost:9001)
- **Prometheus**: [http://localhost:9090](http://localhost:9090)
- **Grafana**: [http://localhost:3000](http://localhost:3000)
**Front/ react** :http://localhost:5173/
---

## Running Database Migrations

Apply Alembic migrations to set up the database schema:
```bash
docker compose exec app alembic upgrade head
```

---

## Running Tests

Execute the complete test suite:
```bash
docker compose exec app pytest tests/ -v --cov=app
```

---

## Architecture Diagram

```
+-------------------------------------------------------------------------+
|                              Web UI / Client                            |
+-------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                  FastAPI Backend (Async Layer & Middleware)              |
|          [Tenant Isolation | JWT Auth | RBAC | Rate Limiter]            |
+-------------------------------------------------------------------------+
                                     |
       +-----------------------------+-----------------------------+
       |                                                           |
       v                                                           v
+-----------------------------+                             +-----------------------------+
|   Text-to-SQL Agent         |                             |    Document RAG Pipeline    |
| - Schema Retriever          |                             | - Document Parser           |
| - SQLGlot Security Validator|                             | - Chunking & Embeddings     |
| - Row Filter Injector (RLS) |                             | - MinIO Storage             |
| - Execution (Read-Only)     |                             | - pgvector HNSW Index       |
+-----------------------------+                             +-----------------------------+
       |                                                           |
       +-----------------------------+-----------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                      LangGraph Hybrid Merger Agent                       |
|               Grounded Response + SQL Results + Citations               |
+-------------------------------------------------------------------------+
```

---

## License

Enterprise Licensed.
