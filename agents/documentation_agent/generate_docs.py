from __future__ import annotations

from pathlib import Path

from meta_agent.utils import ensure_dir, write_text, log
from meta_agent.llm_interface import BaseLLM
from meta_agent.context_manager import MCPContext


def generate_docs(prompt: str, ctx: MCPContext, out_dir: Path, llm: BaseLLM) -> None:
    docs_dir = out_dir / "docs"
    ensure_dir(docs_dir)

    summary = f"""
# AutoDevOS – Generated Project Documentation

This project was generated from the prompt:

> {prompt}

## Structure

- output/frontend/app: React + TypeScript app (Vite + Tailwind + Jest)
- output/backend/app: Node.js + Express + TypeScript API (Jest)
- agents/testing_agent/python: PyTest integration tests

## Running locally

- Frontend: npm install && npm run dev (in output/frontend/app)
- Backend: npm install && npm run dev (in output/backend/app)

## API

- GET /api/health -> {{ status: 'ok' }}
- GET /api/items -> []
- POST /api/items {{ name }} -> created item
"""

    write_text(docs_dir / "README.md", summary)

    ctx.add_artifact("documentation", docs_dir)
    log.info(f"Documentation generated at: {docs_dir}")
