import pytest
import tempfile
from pathlib import Path
import threading
import time

from meta_agent.context_manager import MCPContext


def test_context_creation():
    """Test basic context creation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ctx = MCPContext(project_name="test", storage_dir=Path(tmpdir))
        assert ctx.project_name == "test"
        assert ctx.version == 1
        assert len(ctx.data) == 0
        assert len(ctx.events) == 0


def test_context_set_get():
    """Test setting and getting context data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ctx = MCPContext(project_name="test", storage_dir=Path(tmpdir))
        
        ctx.set("key1", "value1")
        assert ctx.get("key1") == "value1"
        assert ctx.version == 2  # Version incremented
        
        ctx.set("key2", {"nested": "data"})
        assert ctx.get("key2") == {"nested": "data"}
        assert ctx.version == 3


def test_context_events():
    """Test event logging."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ctx = MCPContext(project_name="test", storage_dir=Path(tmpdir))
        
        ctx.append_event("test_event", {"data": "test"})
        assert len(ctx.events) == 1
        assert ctx.events[0]["kind"] == "test_event"
        assert ctx.events[0]["payload"] == {"data": "test"}
        assert "timestamp" in ctx.events[0]


def test_context_artifacts():
    """Test artifact registration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ctx = MCPContext(project_name="test", storage_dir=Path(tmpdir))
        
        ctx.add_artifact("frontend", Path("/tmp/test"))
        artifacts = ctx.get("artifacts")
        assert len(artifacts) == 1
        assert artifacts[0]["agent"] == "frontend"
        assert artifacts[0]["path"] == "/tmp/test"


def test_context_save_load():
    """Test context persistence."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_dir = Path(tmpdir)
        
        # Create and save context
        ctx1 = MCPContext(project_name="test", storage_dir=storage_dir)
        ctx1.set("key", "value")
        ctx1.append_event("event1", {"data": 1})
        ctx1.save()
        
        # Load context
        ctx2 = MCPContext.load("test", storage_dir)
        assert ctx2.get("key") == "value"
        assert len(ctx2.events) == 1
        assert ctx2.version == ctx1.version


def test_context_thread_safety():
    """Test thread-safe operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ctx = MCPContext(project_name="test", storage_dir=Path(tmpdir))
        results = []
        
        def set_value(i):
            ctx.set(f"key{i}", f"value{i}")
            results.append(i)
        
        threads = [threading.Thread(target=set_value, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(results) == 10
        assert ctx.version == 11  # 1 + 10 sets


def test_context_atomic_update():
    """Test atomic update function."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ctx = MCPContext(project_name="test", storage_dir=Path(tmpdir))
        
        def updater(ctx):
            ctx.set("counter", ctx.get("counter", 0) + 1)
            return ctx.get("counter")
        
        result = ctx.atomic_update(updater)
        assert result == 1
        assert ctx.get("counter") == 1
