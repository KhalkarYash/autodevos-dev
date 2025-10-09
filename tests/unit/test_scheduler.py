"""Unit tests for DAGScheduler."""
import pytest
import asyncio
from meta_agent.dag_scheduler import DAGScheduler, DAGTask, TaskStatus


class TestDAGTask:
    """Test DAGTask dataclass."""
    
    def test_task_initialization(self):
        """Test task initializes with correct defaults."""
        async def dummy_fn():
            return "result"
        
        task = DAGTask(
            id="test_task",
            name="Test Task",
            fn=dummy_fn
        )
        
        assert task.id == "test_task"
        assert task.name == "Test Task"
        assert task.status == TaskStatus.PENDING
        assert task.max_retries == 3
        assert task.retry_count == 0
        assert task.error is None
        assert task.result is None


class TestDAGScheduler:
    """Test DAGScheduler class."""
    
    @pytest.fixture
    def scheduler(self):
        """Create scheduler instance for testing."""
        return DAGScheduler(max_parallel=2)
    
    def test_initialization(self, scheduler):
        """Test scheduler initializes correctly."""
        assert scheduler.max_parallel == 2
        assert len(scheduler.tasks) == 0
    
    @pytest.mark.asyncio
    async def test_add_task(self, scheduler):
        """Test adding tasks to scheduler."""
        async def task_fn():
            return "done"
        
        task = DAGTask(id="task1", name="Task 1", fn=task_fn)
        scheduler.add_task(task)
        
        assert "task1" in scheduler.tasks
        assert scheduler.tasks["task1"].name == "Task 1"
    
    @pytest.mark.asyncio
    async def test_simple_execution(self, scheduler):
        """Test simple task execution without dependencies."""
        results = []
        
        async def task_fn(task_id):
            results.append(task_id)
            return f"result_{task_id}"
        
        task1 = DAGTask(id="task1", name="Task 1", fn=task_fn, args=("task1",))
        task2 = DAGTask(id="task2", name="Task 2", fn=task_fn, args=("task2",))
        
        scheduler.add_task(task1)
        scheduler.add_task(task2)
        
        summary = await scheduler.run()
        
        assert summary["completed"] == 2
        assert summary["failed"] == 0
        assert len(results) == 2
        assert "task1" in results
        assert "task2" in results
    
    @pytest.mark.asyncio
    async def test_dependency_execution(self, scheduler):
        """Test tasks execute in dependency order."""
        execution_order = []
        
        async def task_fn(task_id):
            execution_order.append(task_id)
            await asyncio.sleep(0.01)
            return f"result_{task_id}"
        
        task1 = DAGTask(id="task1", name="Task 1", fn=task_fn, args=("task1",))
        task2 = DAGTask(id="task2", name="Task 2", fn=task_fn, args=("task2",), depends_on=["task1"])
        task3 = DAGTask(id="task3", name="Task 3", fn=task_fn, args=("task3",), depends_on=["task2"])
        
        scheduler.add_task(task1)
        scheduler.add_task(task2)
        scheduler.add_task(task3)
        
        summary = await scheduler.run()
        
        assert summary["completed"] == 3
        assert execution_order == ["task1", "task2", "task3"]
    
    @pytest.mark.asyncio
    async def test_parallel_execution(self, scheduler):
        """Test independent tasks execute in parallel."""
        start_times = {}
        end_times = {}
        
        async def task_fn(task_id):
            start_times[task_id] = asyncio.get_event_loop().time()
            await asyncio.sleep(0.1)
            end_times[task_id] = asyncio.get_event_loop().time()
            return f"result_{task_id}"
        
        task1 = DAGTask(id="task1", name="Task 1", fn=task_fn, args=("task1",))
        task2 = DAGTask(id="task2", name="Task 2", fn=task_fn, args=("task2",))
        
        scheduler.add_task(task1)
        scheduler.add_task(task2)
        
        summary = await scheduler.run()
        
        assert summary["completed"] == 2
        
        # Check tasks ran in parallel (overlapping time windows)
        assert start_times["task2"] < end_times["task1"]
    
    @pytest.mark.asyncio
    async def test_retry_on_failure(self, scheduler):
        """Test task retry on failure."""
        attempt_count = {"count": 0}
        
        async def failing_task():
            attempt_count["count"] += 1
            if attempt_count["count"] < 3:
                raise RuntimeError("Temporary failure")
            return "success"
        
        task = DAGTask(id="retry_task", name="Retry Task", fn=failing_task, max_retries=3)
        scheduler.add_task(task)
        
        summary = await scheduler.run()
        
        assert summary["completed"] == 1
        assert attempt_count["count"] == 3
        assert task.result == "success"
    
    @pytest.mark.asyncio
    async def test_task_timeout(self, scheduler):
        """Test task timeout handling."""
        async def slow_task():
            await asyncio.sleep(10)
            return "should not complete"
        
        task = DAGTask(id="slow", name="Slow Task", fn=slow_task, timeout=0.1, max_retries=0)
        scheduler.add_task(task)
        
        summary = await scheduler.run()
        
        assert summary["failed"] == 1
        assert task.status == TaskStatus.FAILED
    
    @pytest.mark.asyncio
    async def test_fail_fast(self, scheduler):
        """Test fail-fast mode stops on first failure."""
        async def failing_task():
            raise RuntimeError("Task failed")
        
        async def normal_task():
            return "success"
        
        task1 = DAGTask(id="fail", name="Failing Task", fn=failing_task, max_retries=0)
        task2 = DAGTask(id="normal", name="Normal Task", fn=normal_task, depends_on=["fail"])
        
        scheduler.add_task(task1)
        scheduler.add_task(task2)
        
        summary = await scheduler.run(fail_fast=True)
        
        assert summary["failed"] == 1
        assert summary["skipped"] == 1
    
    @pytest.mark.asyncio
    async def test_backoff_calculation(self, scheduler):
        """Test exponential backoff calculation."""
        task = DAGTask(id="test", name="Test", fn=lambda: None)
        
        backoff_0 = scheduler._calculate_backoff(task, 0)
        backoff_1 = scheduler._calculate_backoff(task, 1)
        backoff_2 = scheduler._calculate_backoff(task, 2)
        
        # Verify exponential growth
        assert backoff_0 < backoff_1 < backoff_2
        assert backoff_0 >= 2.0  # base_backoff
        
    def test_dag_validation_cycle_detection(self, scheduler):
        """Test DAG validates and detects cycles."""
        async def dummy():
            return None
        
        # Create cycle: A -> B -> C -> A
        taskA = DAGTask(id="A", name="A", fn=dummy, depends_on=["C"])
        taskB = DAGTask(id="B", name="B", fn=dummy, depends_on=["A"])
        taskC = DAGTask(id="C", name="C", fn=dummy, depends_on=["B"])
        
        scheduler.add_task(taskA)
        scheduler.add_task(taskB)
        scheduler.add_task(taskC)
        
        assert scheduler._validate_dag() is False
    
    def test_topological_levels(self, scheduler):
        """Test topological level computation."""
        async def dummy():
            return None
        
        # Create diamond dependency: A, B -> C, D -> E
        taskA = DAGTask(id="A", name="A", fn=dummy)
        taskB = DAGTask(id="B", name="B", fn=dummy)
        taskC = DAGTask(id="C", name="C", fn=dummy, depends_on=["A", "B"])
        taskD = DAGTask(id="D", name="D", fn=dummy, depends_on=["A", "B"])
        taskE = DAGTask(id="E", name="E", fn=dummy, depends_on=["C", "D"])
        
        scheduler.add_task(taskA)
        scheduler.add_task(taskB)
        scheduler.add_task(taskC)
        scheduler.add_task(taskD)
        scheduler.add_task(taskE)
        
        levels = scheduler._topological_levels()
        
        # Level 0: A, B
        assert set(levels[0]) == {"A", "B"}
        # Level 1: C, D
        assert set(levels[1]) == {"C", "D"}
        # Level 2: E
        assert levels[2] == ["E"]
