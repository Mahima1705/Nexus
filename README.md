# Nexus — AI-Powered Codebase Assistant

Nexus helps developers understand, search, review, and document unfamiliar codebases using Retrieval-Augmented Generation (RAG). Point it at a GitHub repository or upload a ZIP, and it indexes the code into a vector store so you can chat with it, ask "where should I add X?", get an AI code review, decode a stack trace, or generate documentation - all grounded in the actual repository content, not general knowledge.

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Screenshots](#screenshots)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Quick Start with Docker](#quick-start-with-docker-recommended)
  - [Manual Local Setup](#manual-local-setup)
- [Environment Variables](#environment-variables)
- [API Documentation](#api-documentation)
- [Database Schema](#database-schema)
- [Testing](#testing)
- [Security](#security)
- [Build History](#build-history)
- [Known Limitations & Future Improvements](#known-limitations--future-improvements)

## Features

**Repository Ingestion** — Connect a public GitHub URL or upload a `.zip` archive. Nexus clones/extracts it, walks the file tree (skipping `node_modules`, `.git`, `dist`, `build`, `vendor`, `coverage`, `__pycache__`, and friends), splits every file into semantically-grounded chunks, embeds them, and stores the vectors in Qdrant. Progress is visible live (`pending → cloning/extracting → indexing → ready`).

**AI Codebase Chat** — Ask natural-language questions ("How does authentication work?", "Where is the payment flow?") and get answers grounded in retrieved code, with clickable file:line references and streaming (token-by-token) responses.

**Smart Code Search** — Ask where something lives or should be added ("Where should I add Google login?", "Which module creates orders?") and get relevant files with an explanation of the reasoning.

**AI Code Reviewer** — Paste a snippet or upload a file for a structured review: bugs, security issues, code smells, performance suggestions, and best-practice violations, each with severity and line number where known.

**Error & Log Analyzer** — Paste a stack trace or log output for a plain-English explanation, likely cause, relevant repository files (if you attach repo context), debugging suggestions, and possible fixes.

**Documentation Generator** — Generate a README, project overview, folder structure, API summary, installation guide, or environment-variable reference — grounded in the actual repository, not invented.

**Auth & Multi-Repository** — JWT access + refresh tokens (with rotation and revocation), each user manages their own set of repositories.

## Architecture

```
 User
   │
   ▼
 Frontend (Next.js, React, TypeScript)
   │  REST + SSE (streaming chat)
   ▼
 FastAPI Backend
   │
   ├─ Repository Processor  (GitPython clone / ZIP extract, path-traversal & zip-bomb safe)
   │        │
   │        ▼
   ├─ Chunker  (language-aware boundary detection + token-aware sliding window)
   │        │
   │        ▼
   ├─ Embedding Provider  (OpenAI or local BGE — swappable via one config value)
   │        │
   │        ▼
   ├─ Qdrant  (vector storage)
   │        │
   │        ▼
   ├─ Retriever  (query → embed → Qdrant search → top-K chunks)
   │        │
   │        ▼
   ├─ Prompt Builder  (System / Developer / Repository / Context / User prompts)
   │        │
   │        ▼
   └─ LLM Provider  (OpenAI or Claude, via LangChain — swappable via one config value)
            │
            ▼
        Response (with file references)
```

Metadata (users, repositories, chat sessions/messages, embedding pointers, review/doc history) lives in **PostgreSQL**. Vectors live in **Qdrant**. Every AI feature shares the same retrieval pipeline and is instructed to answer only from retrieved repository context — if the context doesn't contain the answer, the model is told to say so rather than guess.

### Backend layering

```
api/v1/endpoints  →  services  →  ai/{providers,embeddings,vector_store,prompts}  →  models (SQLAlchemy)
                              ↘  repository_processor (clone/extract/chunk)
```

Routes contain no business logic — they call a service. Services orchestrate; they never talk to OpenAI/Anthropic/Qdrant SDKs directly, only through the `ai/` wrappers, which is what makes both the LLM provider and the embedding provider swappable with a single environment variable (`LLM_PROVIDER=openai|claude`, `EMBEDDING_PROVIDER=openai|bge`) and zero code changes anywhere else.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16 (App Router), React 18, TypeScript, Tailwind CSS |
| Backend | Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2.0 (async), Alembic |
| AI / RAG | LangChain (`ChatOpenAI`, `ChatAnthropic`, `OpenAIEmbeddings`, `HuggingFaceEmbeddings`) |
| LLM | OpenAI GPT-4o |
| Embeddings | local BGE (sentence-transformers)  |
| Vector DB | Qdrant |
| Database | PostgreSQL |
| Auth | JWT (access + rotating refresh tokens) |
| Repository processing | GitPython, custom semantic chunker |
| Testing | pytest (backend, 169 tests), Vitest + React Testing Library (frontend, 30 tests) |
| Deployment | Docker, Docker Compose |

## Screenshots

> _Add screenshots here once you have a deployment to capture — e.g._
> - `docs/screenshots/dashboard.png` — Dashboard overview
> - `docs/screenshots/chat.png` — AI Codebase Chat with streaming response and file references
> - `docs/screenshots/review.png` — AI Code Reviewer findings
> - `docs/screenshots/dark-mode.png` — Dark mode

## Project Structure

```
nexus/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/       # auth, users, repositories, chat, search, review, errors, docs
│   │   ├── core/                   # config (Pydantic Settings), security, logging, exceptions
│   │   ├── db/                     # SQLAlchemy async engine/session, declarative base
│   │   ├── models/                 # ORM models (9 tables)
│   │   ├── schemas/                # Pydantic request/response schemas
│   │   ├── services/                # business logic — auth, repository, embedding, retriever,
│   │   │                            #   prompt, llm, chat, search, review, error-analysis, docs
│   │   ├── repository_processor/   # github_cloner, zip_extractor, file_filter, chunker
│   │   ├── ai/
│   │   │   ├── providers/          # LLMProvider ABC + OpenAI/Claude implementations
│   │   │   ├── embeddings/         # EmbeddingProvider ABC + OpenAI/BGE implementations
│   │   │   ├── vector_store/       # Qdrant client wrapper
│   │   │   └── prompts/            # System/Developer/Repository/Context/User prompt templates
│   │   ├── middleware/             # rate limiting
│   │   ├── utils/                  # validators, file utils, tokenization, JSON extraction
│   │   └── main.py                 # FastAPI app factory
│   ├── alembic/versions/           # DB migrations
│   ├── tests/{unit,integration}/   # 169 tests
│   ├── requirements.txt            # requirements-bge.txt is optional (local embeddings)
│   ├── Dockerfile
│   └── docker-entrypoint.sh        # runs migrations, then starts uvicorn
├── frontend/
│   └── src/
│       ├── app/
│       │   ├── (auth)/{login,register}/
│       │   └── (dashboard)/
│       │       ├── dashboard/, repositories/, review/, errors/, profile/
│       │       └── repositories/[id]/{chat,search,docs}/
│       ├── components/{ui,layout,chat,repository,review,common}/
│       ├── lib/{api,hooks,store,utils}/
│       ├── types/
│       └── styles/
│   ├── vitest.config.ts            # 30 tests
│   └── Dockerfile                  # Next.js standalone build
├── docker-compose.yml              # postgres + qdrant + backend + frontend
├── .env.example                    # docker-compose variables
└── README.md
```

## Getting Started

### Quick Start with Docker (recommended)

Requires Docker and Docker Compose.

```bash
git clone <this-repo>
cd nexus
cp .env.example .env
# Edit .env and set OPENAI_API_KEY (or ANTHROPIC_API_KEY + LLM_PROVIDER=claude)
docker compose up -d
```

- Frontend: http://localhost:3000
- Backend API docs: http://localhost:8000/api/v1/docs

The backend's entrypoint runs database migrations automatically on startup. Without an API key, everything still works — auth, repository upload, browsing — except the AI features, which fail with a clear error message rather than hanging or crashing.

```bash
docker compose logs -f backend    # tail logs
docker compose down               # stop (keeps data in named volumes)
docker compose down -v            # stop and delete all data
```

### Manual Local Setup

Requires Python 3.11+, Node.js 20+, a running PostgreSQL instance, and a running Qdrant instance (`docker run -p 6333:6333 qdrant/qdrant`).

**Backend:**

```bash
cd backend
python -m venv .venv
./.venv/Scripts/pip install -r requirements.txt   # or .venv/bin/pip on macOS/Linux
cp .env.example .env
# Edit .env: point DATABASE_URL/SYNC_DATABASE_URL at your Postgres, set OPENAI_API_KEY
./.venv/Scripts/alembic upgrade head
./.venv/Scripts/uvicorn app.main:app --reload
```

**Frontend** (separate terminal):

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

## Environment Variables

### Backend (`backend/.env`)

| Variable | Default | Description |
|---|---|---|
| `ENVIRONMENT` | `development` | `development` \| `staging` \| `production` |
| `BACKEND_CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowed origins |
| `DATABASE_URL` | `postgresql+asyncpg://nexus:nexus@localhost:5432/nexus` | Async DB connection (app runtime) |
| `SYNC_DATABASE_URL` | `postgresql+psycopg2://nexus:nexus@localhost:5432/nexus` | Sync DB connection (Alembic) |
| `SECRET_KEY` | __ | JWT signing key. Generate: `openssl rand -hex 32` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token lifetime |
| `QDRANT_URL` | `http://localhost:6333` | Qdrant endpoint |
| `QDRANT_API_KEY` | __ | Only needed for a secured Qdrant instance |
| `LLM_PROVIDER` | `openai` | `openai` \| `claude` |
| `OPENAI_API_KEY` | __ | Required for `LLM_PROVIDER=openai` or `EMBEDDING_PROVIDER=openai` |
| `OPENAI_CHAT_MODEL` | `gpt-4o` | |
| `ANTHROPIC_API_KEY` | __ | Required for `LLM_PROVIDER=claude` |
| `CLAUDE_CHAT_MODEL` | `claude-sonnet-4-20250514` | |
| `EMBEDDING_PROVIDER` | `openai` | `openai` \| `bge` (bge runs locally, no API key, but needs `requirements-bge.txt`) |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | |
| `BGE_MODEL_NAME` | `BAAI/bge-small-en-v1.5` | |
| `MAX_UPLOAD_SIZE_MB` | `200` | ZIP upload limit |
| `MAX_REPO_SIZE_MB` | `500` | Total extracted/cloned repo size limit |
| `RATE_LIMIT_PER_MINUTE` | `60` | Default per-IP rate limit |
| `LOG_LEVEL` | `INFO` | `DEBUG` \| `INFO` \| `WARNING` \| `ERROR` |

See [backend/.env.example](backend/.env.example) for the complete list.

### Frontend (`frontend/.env.local`)

| Variable | Default | Description |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000/api/v1` | Backend URL the **browser** calls — must be reachable from the client, not just the server |

### Docker Compose (root `.env`)

Adds `POSTGRES_USER/PASSWORD/DB`, per-service host ports, and mirrors the backend/frontend variables above for injection into containers. See [.env.example](.env.example).

## API Documentation

Interactive Swagger UI: `http://localhost:8000/api/v1/docs` (ReDoc at `/api/v1/redoc`). Full route table:

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/auth/register` | Create an account |
| POST | `/api/v1/auth/login` | Exchange credentials for access + refresh tokens |
| POST | `/api/v1/auth/refresh` | Rotate a refresh token for a new pair |
| POST | `/api/v1/auth/logout` | Revoke a refresh token |
| GET | `/api/v1/users/me` | Current user profile |
| GET | `/api/v1/repositories` | List your repositories |
| POST | `/api/v1/repositories/github` | Register a repository from a GitHub URL (clones in background) |
| POST | `/api/v1/repositories/upload` | Upload a ZIP (extracts in background) |
| GET | `/api/v1/repositories/{id}` | Repository detail + status |
| DELETE | `/api/v1/repositories/{id}` | Delete a repository and its vectors |
| POST | `/api/v1/repositories/{id}/sessions` | Create a chat session |
| GET | `/api/v1/repositories/{id}/sessions` | List chat sessions |
| GET | `/api/v1/sessions/{id}/messages` | List messages in a session |
| POST | `/api/v1/sessions/{id}/messages` | Ask a question (non-streaming) |
| POST | `/api/v1/sessions/{id}/messages/stream` | Ask a question (Server-Sent Events stream) |
| POST | `/api/v1/repositories/{id}/search` | Smart code search |
| POST | `/api/v1/review/snippet` | Review a pasted code snippet |
| POST | `/api/v1/review/file` | Review an uploaded file |
| POST | `/api/v1/errors/analyze` | Analyze an error/stack trace (optional repository context) |
| POST | `/api/v1/docs/repositories/{id}/generate` | Generate documentation |

Every authenticated route requires `Authorization: Bearer <access_token>`. All errors share one JSON shape: `{"error": {"code": str, "message": str, "details": {...}}}`.

## Database Schema

9 normalized tables (PostgreSQL, managed via Alembic — see `backend/alembic/versions/`):

| Table | Purpose |
|---|---|
| `users` | Accounts |
| `refresh_tokens` | Hashed refresh tokens (rotation + revocation, never stores the raw token) |
| `repositories` | One row per connected/uploaded repository, with live status |
| `repository_files` | Per-file metadata from the indexing walk |
| `embedding_metadata` | Postgres-side mirror of each chunk stored in Qdrant (file, chunk index, line range) |
| `chat_sessions` | One per conversation thread |
| `messages` | Chat messages, with `referenced_files` (JSON) for assistant answers |
| `documentation_history` | Every generated doc, by type |
| `review_history` | Every code review, with structured findings (JSON) |

## Testing

```bash
# Backend (169 tests: unit + live integration against real Qdrant/GitHub)
cd backend
./.venv/Scripts/pytest -v
./.venv/Scripts/pytest --cov=app --cov-report=html   # coverage report → htmlcov/

# Frontend (30 tests)
cd frontend
npm test
npm run test:coverage
npm run type-check
npm run lint
```

The backend suite runs fully offline against SQLite by default; two tests are deliberate live exceptions (a real `git clone` against GitHub, and real Qdrant collection create/upsert/search) and skip themselves cleanly when network/Qdrant aren't reachable.

## Security

- **Passwords**: bcrypt-hashed, never logged or returned in any response.
- **JWT**: short-lived access tokens (30 min default) + rotating refresh tokens (single-use — reusing one is rejected). Only a SHA-256 hash of each refresh token is stored.
- **GitHub URL validation**: scheme and host are strictly anchored (`https://github.com/...` only) to prevent SSRF via a crafted "GitHub URL".
- **ZIP upload safety**: entry count and total uncompressed size are checked *before* extracting a single byte (zip-bomb defense); every resolved path is verified to stay inside the destination directory (zip-slip defense); symlink entries are rejected.
- **Rate limiting**: per-IP limits on auth endpoints (register/login/refresh) via `slowapi`.
- **CORS**: explicit allow-list, not `*`.
- **Input validation**: Pydantic schemas on every request body; password policy enforced (min 8 chars, letter + digit).

## Build History

Built incrementally, milestone by milestone, each one tested and verified (often against a live Docker-based Postgres/Qdrant stack and a real browser session, not just unit tests) before moving to the next:

| # | Milestone |
|---|---|
| 1 | Architecture & folder structure |
| 2 | Backend foundation (FastAPI, config, logging, exceptions) |
| 3 | Database models & Alembic migrations |
| 4 | Authentication (JWT + refresh token rotation) |
| 5 | Repository upload (GitHub clone / ZIP extract) |
| 6 | Repository parser & semantic chunking |
| 7 | Embeddings pipeline (BGE) |
| 8 | Qdrant vector store integration |
| 9 | RAG retrieval pipeline & prompt engineering |
| 10 | AI services (chat, search, review, error analysis, docs) — LangChain-backed |
| 11 | Frontend (Next.js) |
| 12 | Frontend ↔ backend integration (streaming chat, error/loading states) |
| 13 | Docker & deployment |
| 14 | Testing (199 tests total) |
| 15 | Final documentation |

## Known Limitations & Future Improvements

- **Documentation history and review history aren't surfaced in the UI** as a browsable list yet (the backend persists them; the frontend only shows the most recent result per session).
