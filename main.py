from __future__ import annotations

from pathlib import Path

from meta_agent.context_manager import MCPContext
from meta_agent.orchestrator import Orchestrator
from meta_agent.utils import log

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import logging

app = FastAPI(
    title="AutoDevOS API",
    description="AI-powered application generation service",
    version="1.0.0"
)


class GenerateRequest(BaseModel):
    prompt: str
    output_dir: str = "output"


class GenerateResponse(BaseModel):
    success: bool
    message: str
    summary: dict


async def run_generation(prompt: str, output_dir: str = "output"):
    """Run the AutoDevOS generation pipeline."""
    try: 
        project_root = Path(__file__).resolve().parent
        output_path = project_root / output_dir

        ctx = MCPContext(project_name="AutoDevOS", storage_dir=output_path / ".ctx")

        orch = Orchestrator(
            project_root=project_root, 
            output_dir=output_path, 
            max_parallel=4, 
            use_dynamic_planning=False
        )
        summary = await orch.run(prompt, ctx, fail_fast=False)

        ctx.save()
        
        if summary['failed'] > 0:
            log.error("Generation completed with errors: %d tasks failed", summary['failed'])
            return {
                "success": False,
                "message": f"Generation completed with errors: {summary['failed']} tasks failed",
                "summary": summary
            }
        else:
            log.info("✓ Generation complete! %d/%d tasks succeeded", summary['completed'], summary['total'])
            return {
                "success": True,
                "message": f"Generation complete! {summary['completed']}/{summary['total']} tasks succeeded",
                "summary": summary
            }
        
    except Exception as e:
        logging.error("Error during generation: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get('/health')
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "AutoDevOS"}


@app.post('/generate', response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    """Generate application from natural language prompt."""
    result = await run_generation(prompt=request.prompt, output_dir=request.output_dir)
    return result

# if __name__ == "__main__":
#     asyncio.run(amain())
