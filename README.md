# AutoDevOS – Autonomous Multi-Agent Software Development Platform

AutoDevOS is an AI-driven platform that autonomously generates complete applications from high-level natural language prompts. It demonstrates multi-agent orchestration, meta-agent task decomposition, and AI-powered code generation with a production-quality, modular, maintainable, and scalable architecture.

## Quickstart

1. Python and Node are required locally (or use Docker below).
2. Optional: export GEMINI_API_KEY to use Gemini; otherwise a Mock LLM is used.
3. Run the orchestrator:

```bash
python3 main.py --prompt "Build a Todo app with list and create APIs"
```

This generates code in `output/`:
- `output/frontend/app` – React + TypeScript (Vite + Tailwind + Jest)
- `output/backend/app` – Node.js + Express + TypeScript (Jest)

Install and run both:

```bash
npm --prefix output/backend/app ci && npm --prefix output/backend/app run dev
npm --prefix output/frontend/app ci && npm --prefix output/frontend/app run dev
```

Or run both concurrently from root:

```bash
npm run dev
```

## Docker

Build and run with Docker:

```bash
docker build -t autodevos:latest -f docker/Dockerfile .
docker run -e DEMO_PROMPT="Build a Todo app" -p 3000:3000 -p 5173:5173 autodevos:latest
```

## Architecture

- `meta_agent/` – Orchestration with DAG scheduler, thread-safe context, robust LLM interface
- `agents/` – Specialized agents (React+TS frontend, Express+Prisma+JWT backend, PyTest testing, documentation)
- `tests/` – Comprehensive unit and integration tests
- `docker/` – Multi-stage Dockerfile with non-root user
- `.github/workflows/` – Full CI/CD pipeline with security scanning
- `scripts/` – End-to-end demo and utility scripts

Agents collaborate through a thread-safe MCP-based context with version tracking and atomic persistence.

## Key Features

### Core Platform
- ✅ **Dynamic DAG Orchestration** - LLM-based task planning with dependency resolution
- ✅ **Parallel Execution** - Independent tasks run concurrently with configurable limits
- ✅ **Robust Error Handling** - Retry policies, exponential backoff, graceful degradation
- ✅ **Thread-Safe Context** - MCP protocol with atomic updates and versioning
- ✅ **Production Logging** - Rich console output with structured event tracking

### Generated Applications
- ✅ **React + TypeScript Frontend** - Vite, Tailwind CSS, Jest testing
- ✅ **Express + TypeScript Backend** - Prisma ORM, SQLite/PostgreSQL, JWT auth
- ✅ **User Authentication** - Registration, login, password hashing (bcrypt)
- ✅ **Database Integration** - Prisma schema, migrations, type-safe queries
- ✅ **API Security** - JWT middleware, protected routes, CORS enabled
- ✅ **Comprehensive Tests** - Jest for frontend/backend, PyTest for integration
- ✅ **Auto-Generated Docs** - README, API documentation, setup instructions

### DevOps & Quality
- ✅ **Multi-Stage Docker** - Optimized builds, non-root user, healthchecks
- ✅ **GitHub Actions CI/CD** - Testing, linting, security scanning, deployment
- ✅ **Security Scanning** - Trivy, Safety, SARIF output to GitHub Security
- ✅ **Code Quality Tools** - Black, Flake8, MyPy, pytest with coverage
- ✅ **End-to-End Demo** - Complete workflow from prompt to running app

## LLM Integration

AutoDevOS uses a modular LLM interface. By default, it tries Gemini via `google-generativeai`. If `GEMINI_API_KEY` is not provided, it falls back to a deterministic MockLLM for offline use.

## Testing

- Backend: Jest tests under `output/backend/app/tests`
- Frontend: Jest tests under `output/frontend/app/src/*.test.tsx`
- Root: PyTest integration tests under `output/testing/python`

## Configuration

- `.env.example` shows environment variables
- `config.yaml` holds orchestrator configuration (placeholder)

## Security and Notes

- Secrets should be provided via environment variables. Do not commit production secrets.
- This repository is intended for local development and demonstration; production hardening (auth, persistence, CI/CD) can be layered on.
