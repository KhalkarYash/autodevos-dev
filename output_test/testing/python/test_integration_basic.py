import json
from pathlib import Path


def test_plan_dependencies_exist():
    # Verify that previous artifacts exist (basic integration gate)
    root = Path(__file__).resolve().parents[3]  # project root
    assert (root / 'output' / 'frontend' / 'app').exists()
    assert (root / 'output' / 'backend' / 'app').exists()
