"""Unit tests for Orchestrator."""
import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from meta_agent.orchestrator import Orchestrator, PlanValidationError
from meta_agent.context_manager import MCPContext
from meta_agent.llm_interface import MockLLM


class TestOrchestrator:
    """Test Orchestrator class."""
    
    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create temporary directory for tests."""
        return tmp_path
    
    @pytest.fixture
    def orchestrator(self, temp_dir):
        """Create orchestrator instance for testing."""
        project_root = temp_dir / "project"
        output_dir = temp_dir / "output"
        llm = MockLLM()
        return Orchestrator(project_root, output_dir, llm=llm, use_dynamic_planning=False)
    
    def test_initialization(self, orchestrator):
        """Test orchestrator initializes correctly."""
        assert orchestrator.llm is not None
        assert len(orchestrator.agent_registry) == 4
        assert "frontend" in orchestrator.agent_registry
        assert "backend" in orchestrator.agent_registry
        assert "testing" in orchestrator.agent_registry
        assert "documentation" in orchestrator.agent_registry
    
    def test_default_plan(self, orchestrator):
        """Test default plan generation."""
        plan = orchestrator._default_plan()
        
        assert len(plan) == 4
        assert plan[0]["id"] == "frontend"
        assert plan[1]["id"] == "backend"
        assert plan[2]["id"] == "testing"
        assert plan[3]["id"] == "documentation"
        
        # Check dependencies
        assert plan[2]["depends_on"] == ["frontend", "backend"]
        assert plan[3]["depends_on"] == ["frontend", "backend", "testing"]
    
    def test_validate_task_spec_valid(self, orchestrator):
        """Test task spec validation with valid input."""
        valid_spec = {
            "id": "frontend",
            "name": "Generate Frontend",
            "depends_on": ["backend"]
        }
        assert orchestrator._validate_task_spec(valid_spec) is True
    
    def test_validate_task_spec_missing_fields(self, orchestrator):
        """Test task spec validation with missing fields."""
        invalid_spec = {"name": "Generate Frontend"}
        assert orchestrator._validate_task_spec(invalid_spec) is False
    
    def test_validate_task_spec_unknown_agent(self, orchestrator):
        """Test task spec validation with unknown agent ID."""
        invalid_spec = {
            "id": "unknown_agent",
            "name": "Unknown Agent"
        }
        assert orchestrator._validate_task_spec(invalid_spec) is False
    
    def test_validate_plan_valid(self, orchestrator):
        """Test plan validation with valid plan."""
        valid_plan = [
            {"id": "frontend", "name": "Frontend", "depends_on": []},
            {"id": "backend", "name": "Backend", "depends_on": []},
        ]
        
        validated = orchestrator._validate_plan(valid_plan)
        assert len(validated) == 2
        assert validated[0]["id"] == "frontend"
        assert validated[1]["id"] == "backend"
    
    def test_validate_plan_empty(self, orchestrator):
        """Test plan validation with empty plan."""
        with pytest.raises(PlanValidationError):
            orchestrator._validate_plan([])
    
    def test_validate_plan_duplicate_ids(self, orchestrator):
        """Test plan validation removes duplicates."""
        plan_with_dupes = [
            {"id": "frontend", "name": "Frontend 1", "depends_on": []},
            {"id": "frontend", "name": "Frontend 2", "depends_on": []},
        ]
        
        validated = orchestrator._validate_plan(plan_with_dupes)
        assert len(validated) == 1
    
    def test_validate_plan_invalid_dependencies(self, orchestrator):
        """Test plan validation cleans invalid dependencies."""
        plan = [
            {"id": "frontend", "name": "Frontend", "depends_on": ["nonexistent"]},
        ]
        
        validated = orchestrator._validate_plan(plan)
        assert len(validated) == 1
        assert validated[0]["depends_on"] == []
    
    def test_static_planning(self, orchestrator):
        """Test static planning mode."""
        plan = orchestrator.plan("create a web app")
        
        # Should return default plan in static mode
        assert len(plan) == 4
        assert plan[0]["id"] == "frontend"
    
    @pytest.mark.asyncio
    async def test_run_execution(self, orchestrator, temp_dir):
        """Test orchestrator run execution."""
        ctx = MCPContext(
            project_name="test_project",
            storage_dir=temp_dir / "context"
        )
        
        # Mock agent functions to avoid actual file generation
        with patch('agents.frontend_agent.generate_ui.generate_ui'):
            with patch('agents.backend_agent.generate_api.generate_api'):
                with patch('agents.testing_agent.generate_tests.generate_tests'):
                    with patch('agents.documentation_agent.generate_docs.generate_docs'):
                        summary = await orchestrator.run("create app", ctx, fail_fast=False)
                        
                        assert "total" in summary
                        assert "completed" in summary
                        assert summary["total"] >= 0
