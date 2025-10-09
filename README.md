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

- `meta_agent/` – Orchestration, context manager, and LLM interface
- `agents/` – Specialized agents (frontend, backend, testing, documentation)
- `output/` – Generated artifacts
- `docker/` – Dockerfile for local deployment

Agents collaborate through an MCP-like shared context and run in parallel where possible.

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
