from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from meta_agent.context_manager import MCPContext
from meta_agent.orchestrator import Orchestrator
from meta_agent.utils import log


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="AutoDevOS Orchestrator")
    p.add_argument("--prompt", type=str, help="Natural language prompt to generate an application", required=False)
    p.add_argument("--output", type=str, default="output", help="Output directory for generated artifacts")
    return p.parse_args()


async def amain() -> None:
    args = parse_args()
    prompt = args.prompt or input("Enter a prompt for AutoDevOS: ")
    project_root = Path(__file__).resolve().parent
    output_dir = project_root / args.output

    ctx = MCPContext(project_name="AutoDevOS", storage_dir=output_dir / ".ctx")

    orch = Orchestrator(project_root=project_root, output_dir=output_dir, max_parallel=4, use_dynamic_planning=False)
    summary = await orch.run(prompt, ctx, fail_fast=False)

    ctx.save()
    
    if summary['failed'] > 0:
        log.error(f"Generation completed with errors: {summary['failed']} tasks failed")
    else:
        log.info(f"✓ Generation complete! {summary['completed']}/{summary['total']} tasks succeeded")
    
    log.info("See the output/ directory for generated artifacts.")


if __name__ == "__main__":
    asyncio.run(amain())
