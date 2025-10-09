import pytest
import asyncio

from meta_agent.dag_scheduler import DAGScheduler, DAGTask, TaskStatus


@pytest.mark.asyncio
async def test_simple_task_execution():
    """Test simple task execution without dependencies."""
    scheduler = DAGScheduler(max_parallel=2)
    results = []
    
    async def task1():
        results.append("task1")
    
    async def task2():
        results.append("task2")
    
    scheduler.add_task(DAGTask(id="t1", name="Task 1", fn=task1))
    scheduler.add_task(DAGTask(id="t2", name="Task 2", fn=task2))
    
    summary = await scheduler.run()
    
    assert summary["completed"] == 2
    assert summary["failed"] == 0
    assert len(results) == 2
    assert set(results) == {"task1", "task2"}


@pytest.mark.asyncio
async def test_dag_with_dependencies():
    """Test DAG execution with dependencies."""
    scheduler = DAGScheduler(max_parallel=4)
    order = []
    
    async def task_a():
        order.append("a")
        await asyncio.sleep(0.01)
    
    async def task_b():
        order.append("b")
        await asyncio.sleep(0.01)
    
    async def task_c():
        order.append("c")
    
    scheduler.add_task(DAGTask(id="a", name="Task A", fn=task_a))
    scheduler.add_task(DAGTask(id="b", name="Task B", fn=task_b))
    scheduler.add_task(DAGTask(id="c", name="Task C", fn=task_c, depends_on=["a", "b"]))
    
    summary = await scheduler.run()
    
    assert summary["completed"] == 3
    # Task C should run after A and B
    assert order.index("c") > order.index("a")
    assert order.index("c") > order.index("b")


@pytest.mark.asyncio
async def test_task_retry_on_failure():
    """Test task retry logic."""
    scheduler = DAGScheduler()
    attempt_count = 0
    
    async def failing_task():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 2:
            raise ValueError("Task failed")
        return "success"
    
    task = DAGTask(id="retry_test", name="Retry Test", fn=failing_task, max_retries=2)
    scheduler.add_task(task)
    
    summary = await scheduler.run()
    
    assert attempt_count == 2
    assert summary["completed"] == 1
    assert task.status == TaskStatus.COMPLETED


@pytest.mark.asyncio
async def test_task_failure_propagation():
    """Test that dependent tasks are skipped when dependency fails."""
    scheduler = DAGScheduler()
    
    async def failing_task():
        raise ValueError("Task failed")
    
    async def dependent_task():
        return "should not run"
    
    scheduler.add_task(DAGTask(id="fail", name="Failing Task", fn=failing_task, max_retries=0))
    scheduler.add_task(DAGTask(id="dep", name="Dependent Task", fn=dependent_task, depends_on=["fail"]))
    
    summary = await scheduler.run()
    
    assert summary["failed"] == 1
    assert summary["skipped"] == 1


@pytest.mark.asyncio
async def test_cycle_detection():
    """Test that cycle detection works."""
    scheduler = DAGScheduler()
    
    async def dummy():
        pass
    
    scheduler.add_task(DAGTask(id="a", name="A", fn=dummy, depends_on=["b"]))
    scheduler.add_task(DAGTask(id="b", name="B", fn=dummy, depends_on=["a"]))
    
    with pytest.raises(ValueError, match="Invalid DAG"):
        await scheduler.run()


@pytest.mark.asyncio
async def test_parallel_execution():
    """Test that independent tasks run in parallel."""
    scheduler = DAGScheduler(max_parallel=3)
    start_times = {}
    
    async def task(name):
        start_times[name] = asyncio.get_event_loop().time()
        await asyncio.sleep(0.1)
    
    scheduler.add_task(DAGTask(id="p1", name="P1", fn=lambda: task("p1")))
    scheduler.add_task(DAGTask(id="p2", name="P2", fn=lambda: task("p2")))
    scheduler.add_task(DAGTask(id="p3", name="P3", fn=lambda: task("p3")))
    
    summary = await scheduler.run()
    
    assert summary["completed"] == 3
    # All tasks should start roughly at the same time (parallel execution)
    times = list(start_times.values())
    assert max(times) - min(times) < 0.05  # Within 50ms


@pytest.mark.asyncio
async def test_fail_fast_mode():
    """Test fail-fast mode stops execution on first failure."""
    scheduler = DAGScheduler()
    executed = []
    
    async def task(name):
        executed.append(name)
        if name == "fail":
            raise ValueError("Task failed")
    
    scheduler.add_task(DAGTask(id="t1", name="T1", fn=lambda: task("t1")))
    scheduler.add_task(DAGTask(id="fail", name="Fail", fn=lambda: task("fail"), max_retries=0))
    scheduler.add_task(DAGTask(id="t2", name="T2", fn=lambda: task("t2"), depends_on=["t1", "fail"]))
    
    summary = await scheduler.run(fail_fast=True)
    
    assert summary["failed"] >= 1
    # T2 should not execute due to fail-fast
    assert "t2" not in executed
