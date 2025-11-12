from __future__ import annotations

from pathlib import Path

from meta_agent.utils import ensure_dir, write_text, log
from meta_agent.llm_interface import BaseLLM
from meta_agent.context_manager import MCPContext


def generate_tests(prompt: str, ctx: MCPContext, out_dir: Path, llm: BaseLLM) -> None:
    """Generate cross-cutting tests (e.g., Python PyTest) and ensure frontend/backend tests exist."""
    tests_dir = out_dir
    ensure_dir(tests_dir)

    test_plan = (
        "import json\nfrom pathlib import Path\n\n\ndef test_plan_dependencies_exist():\n    # Verify that previous artifacts exist (basic integration gate)\n    root = Path(__file__).resolve().parents[3]  # project root\n    assert (root / 'output' / 'frontend' / 'app').exists()\n    assert (root / 'output' / 'backend' / 'app').exists()\n"
    )
    ensure_dir(tests_dir)
    write_text(tests_dir / "test_integration_basic.py", test_plan)

    ctx.add_artifact("testing", tests_dir)
    log.info(f"Testing scaffolding generated at: {tests_dir}")
