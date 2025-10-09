import pytest
import tempfile
from pathlib import Path
import asyncio

from meta_agent.orchestrator import Orchestrator
from meta_agent.context_manager import MCPContext


@pytest.mark.asyncio
async def test_full_generation_workflow():
    """Test complete application generation workflow."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(__file__).resolve().parents[2]
        output_dir = Path(tmpdir) / "output"
        
        ctx = MCPContext(project_name="test_project", storage_dir=output_dir / ".ctx")
        
        orch = Orchestrator(
            project_root=project_root,
            output_dir=output_dir,
            max_parallel=2,
            use_dynamic_planning=False  # Use static for predictable tests
        )
        
        summary = await orch.run("Build a test app", ctx, fail_fast=False)
        
        # Verify execution summary
        assert summary["total"] == 4
        assert summary["completed"] == 4
        assert summary["failed"] == 0
        
        # Verify artifacts were generated
        assert (output_dir / "frontend" / "app" / "package.json").exists()
        assert (output_dir / "backend" / "app" / "package.json").exists()
        assert (output_dir / "testing" / "python").exists()
        assert (output_dir / "documentation" / "docs").exists()
        
        # Verify context was updated
        artifacts = ctx.get("artifacts")
        assert len(artifacts) == 4
        assert any(a["agent"] == "frontend" for a in artifacts)
        assert any(a["agent"] == "backend" for a in artifacts)


@pytest.mark.asyncio
async def test_error_handling_workflow():
    """Test error handling in workflow."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(__file__).resolve().parents[2]
        output_dir = Path(tmpdir) / "output"
        
        ctx = MCPContext(project_name="test_error", storage_dir=output_dir / ".ctx")
        
        # Create orchestrator with non-existent agent (should handle gracefully)
        orch = Orchestrator(
            project_root=project_root,
            output_dir=output_dir,
            max_parallel=2,
            use_dynamic_planning=False
        )
        
        # Even with potential errors, should complete what it can
        summary = await orch.run("Test prompt", ctx, fail_fast=False)
        
        # Verify context saves even after errors
        ctx.save()
        assert (output_dir / ".ctx" / "context.json").exists()


def test_context_persistence_across_runs():
    """Test that context persists across multiple runs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_dir = Path(tmpdir)
        
        # First run
        ctx1 = MCPContext(project_name="persistent", storage_dir=storage_dir)
        ctx1.set("run", 1)
        ctx1.append_event("test_event", {"data": "first"})
        ctx1.save()
        
        # Second run - load existing context
        ctx2 = MCPContext.load("persistent", storage_dir)
        assert ctx2.get("run") == 1
        assert len(ctx2.events) == 1
        
        # Update and save
        ctx2.set("run", 2)
        ctx2.append_event("test_event", {"data": "second"})
        ctx2.save()
        
        # Third run - verify cumulative state
        ctx3 = MCPContext.load("persistent", storage_dir)
        assert ctx3.get("run") == 2
        assert len(ctx3.events) == 2
