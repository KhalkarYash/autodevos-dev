from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Awaitable, Callable, Dict, List, Any

from .context_manager import MCPContext
from .llm_interface import BaseLLM, make_llm
from .dag_scheduler import DAGScheduler, DAGTask
from .utils import ensure_dir, log

# Agent imports
from agents.frontend_agent.generate_ui import generate_ui
from agents.backend_agent.generate_api import generate_api
from agents.testing_agent.generate_tests import generate_tests
from agents.documentation_agent.generate_docs import generate_docs


class Orchestrator:
    """Dynamic orchestrator with LLM-based planning and DAG execution."""
    
    def __init__(self, project_root: Path, output_dir: Path, llm: BaseLLM | None = None, 
                 max_parallel: int = 4, use_dynamic_planning: bool = True) -> None:
        self.project_root = project_root
        self.output_dir = ensure_dir(output_dir)
        self.llm = llm or make_llm()
        self.max_parallel = max_parallel
        self.use_dynamic_planning = use_dynamic_planning
        
        # Agent registry
        self.agent_registry = {
            "frontend": generate_ui,
            "backend": generate_api,
            "testing": generate_tests,
            "documentation": generate_docs,
        }

    def _parse_prompt_to_plan(self, prompt: str) -> List[Dict[str, Any]]:
        """
        Use LLM to dynamically parse user prompt into a task plan.
        Returns a list of task specifications.
        """
        planning_prompt = f"""
You are a software architecture planner. Given a user request, identify what components need to be built.

Available agents:
- frontend: React + TypeScript UI (always include for web apps)
- backend: Node.js + Express API (include if API/server needed)
- testing: Integration tests (include after frontend/backend)
- documentation: Project documentation (include last)

User Request: {prompt}

Return a JSON array of tasks with this structure:
{{
  "tasks": [
    {{"id": "frontend", "name": "Generate React Frontend", "depends_on": []}},
    {{"id": "backend", "name": "Generate Express Backend", "depends_on": []}},
    {{"id": "testing", "name": "Generate Tests", "depends_on": ["frontend", "backend"]}},
    {{"id": "documentation", "name": "Generate Docs", "depends_on": ["frontend", "backend", "testing"]}}
  ]
}}

Important:
- Only include relevant components (e.g., skip frontend for CLI tools)
- Set dependencies correctly (testing comes after code generation, docs come last)
- Use only available agent IDs

Return ONLY the JSON, no other text.
"""
        
        try:
            response = self.llm.generate_code(planning_prompt, temperature=0.3, max_tokens=1024)
            
            # Extract JSON from response
            json_match = re.search(r'\{[\s\S]*"tasks"[\s\S]*\}', response)
            if json_match:
                plan_data = json.loads(json_match.group())
                tasks = plan_data.get("tasks", [])
                log.info(f"LLM planned {len(tasks)} tasks")
                return tasks
            else:
                log.warning("Failed to parse LLM plan, using default")
                return self._default_plan()
                
        except Exception as e:
            log.error(f"Error in dynamic planning: {e}, using default plan")
            return self._default_plan()
    
    def _default_plan(self) -> List[Dict[str, Any]]:
        """Fallback static plan."""
        return [
            {"id": "frontend", "name": "Generate Frontend", "depends_on": []},
            {"id": "backend", "name": "Generate Backend", "depends_on": []},
            {"id": "testing", "name": "Generate Tests", "depends_on": ["frontend", "backend"]},
            {"id": "documentation", "name": "Generate Documentation", "depends_on": ["frontend", "backend", "testing"]}
        ]
    
    def plan(self, prompt: str) -> List[Dict[str, Any]]:
        """Create execution plan from prompt."""
        if self.use_dynamic_planning:
            log.info("Using dynamic LLM-based planning")
            return self._parse_prompt_to_plan(prompt)
        else:
            log.info("Using static planning")
            return self._default_plan()

    async def run(self, prompt: str, ctx: MCPContext, fail_fast: bool = False) -> Dict[str, Any]:
        """Execute orchestrated workflow using DAG scheduler."""
        ctx.append_event("orchestration_start", {"prompt": prompt})
        
        # Get task plan
        task_specs = self.plan(prompt)
        log.info(f"Planned tasks: {[t['id'] for t in task_specs]}")
        
        # Create DAG scheduler
        scheduler = DAGScheduler(max_parallel=self.max_parallel)
        
        # Build DAG tasks
        for spec in task_specs:
            task_id = spec["id"]
            
            if task_id not in self.agent_registry:
                log.warning(f"Unknown agent {task_id}, skipping")
                continue
            
            agent_fn = self.agent_registry[task_id]
            agent_dir = self.output_dir / task_id
            
            async def make_task_fn(agent_fn=agent_fn, agent_dir=agent_dir, task_id=task_id):
                ensure_dir(agent_dir)
                await asyncio.to_thread(agent_fn, prompt, ctx, agent_dir, self.llm)
                ctx.append_event("task_complete", {"task": task_id})
            
            dag_task = DAGTask(
                id=task_id,
                name=spec.get("name", f"Generate {task_id}"),
                fn=make_task_fn,
                depends_on=spec.get("depends_on", []),
                max_retries=2
            )
            scheduler.add_task(dag_task)
        
        # Execute with DAG scheduler
        ctx.append_event("execution_start", {"task_count": len(scheduler.tasks)})
        summary = await scheduler.run(fail_fast=fail_fast)
        ctx.append_event("execution_complete", summary)
        
        log.info(f"Orchestration complete: {summary['completed']}/{summary['total']} tasks succeeded")
        return summary
