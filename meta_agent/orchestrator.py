from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Awaitable, Callable, Dict, List

from .context_manager import MCPContext
from .llm_interface import BaseLLM, make_llm
from .utils import ensure_dir, log

# Agent imports
from agents.frontend_agent.generate_ui import generate_ui
from agents.backend_agent.generate_api import generate_api
from agents.testing_agent.generate_tests import generate_tests
from agents.documentation_agent.generate_docs import generate_docs


AgentFn = Callable[[str, MCPContext, Path, BaseLLM], Awaitable[None] | None]


@dataclass
class Task:
    id: str
    name: str
    agent: str
    fn: AgentFn
    depends_on: List[str] = field(default_factory=list)


class Orchestrator:
    def __init__(self, project_root: Path, output_dir: Path, llm: BaseLLM | None = None) -> None:
        self.project_root = project_root
        self.output_dir = ensure_dir(output_dir)
        self.llm = llm or make_llm()

    def plan(self, prompt: str) -> List[Task]:
        # Simple static plan with clear dependencies
        tasks = [
            Task(id="frontend", name="Generate Frontend", agent="frontend", fn=self._wrap_sync(generate_ui)),
            Task(id="backend", name="Generate Backend", agent="backend", fn=self._wrap_sync(generate_api)),
            Task(id="tests", name="Generate Tests", agent="testing", fn=self._wrap_sync(generate_tests), depends_on=["frontend", "backend"]),
            Task(id="docs", name="Generate Documentation", agent="documentation", fn=self._wrap_sync(generate_docs), depends_on=["frontend", "backend", "tests"]),
        ]
        log.info("Planned tasks: " + ", ".join(t.id for t in tasks))
        return tasks

    def _wrap_sync(self, fn: Callable[[str, MCPContext, Path, BaseLLM], None]) -> AgentFn:
        async def run(prompt: str, ctx: MCPContext, out: Path, llm: BaseLLM) -> None:
            await asyncio.to_thread(fn, prompt, ctx, out, llm)
        return run

    async def run(self, prompt: str, ctx: MCPContext) -> None:
        tasks = self.plan(prompt)
        # Build simple levels based on dependencies
        level0 = [t for t in tasks if not t.depends_on]  # frontend, backend
        level1 = [t for t in tasks if set(t.depends_on) == {"frontend", "backend"}]  # tests
        level2 = [t for t in tasks if set(t.depends_on) == {"frontend", "backend", "tests"}]  # docs

        async def exec_task(t: Task):
            log.info(f"Starting task: {t.name}")
            agent_dir = self.output_dir / t.agent
            ensure_dir(agent_dir)
            await t.fn(prompt, ctx, agent_dir, self.llm)
            ctx.append_event("task_complete", {"task": t.id})

        # Execute with defined parallelism
        await asyncio.gather(*(exec_task(t) for t in level0))
        await asyncio.gather(*(exec_task(t) for t in level1))
        await asyncio.gather(*(exec_task(t) for t in level2))

        log.info("All tasks completed.")
