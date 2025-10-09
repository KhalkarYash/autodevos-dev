from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Set, Awaitable, Any, Optional
from enum import Enum

from .utils import log


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class DAGTask:
    """Represents a task in the dependency graph."""
    id: str
    name: str
    fn: Callable[..., Awaitable[Any]]
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3
    timeout: Optional[float] = 300.0  # Default 5 minute timeout per task
    base_backoff: float = 2.0  # Base backoff in seconds
    max_backoff: float = 60.0  # Max backoff in seconds
    status: TaskStatus = TaskStatus.PENDING
    error: Exception | None = None
    result: Any = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None


class DAGScheduler:
    """
    DAG-aware async task scheduler with:
    - Topological sorting
    - Parallel execution of independent tasks
    - Dependency resolution
    - Error handling and retry logic
    - Progress tracking
    """
    
    def __init__(self, max_parallel: int = 4):
        self.max_parallel = max_parallel
        self.tasks: Dict[str, DAGTask] = {}
        self.graph: Dict[str, List[str]] = defaultdict(list)
        self.reverse_graph: Dict[str, Set[str]] = defaultdict(set)
        
    def add_task(self, task: DAGTask) -> None:
        """Add a task to the scheduler."""
        self.tasks[task.id] = task
        
        # Build dependency graph
        for dep in task.depends_on:
            self.graph[dep].append(task.id)
            self.reverse_graph[task.id].add(dep)
        
        log.debug(f"Added task {task.id} with dependencies: {task.depends_on}")
    
    def _validate_dag(self) -> bool:
        """Validate that the graph is a valid DAG (no cycles)."""
        visited = set()
        rec_stack = set()
        
        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in self.graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for task_id in self.tasks:
            if task_id not in visited:
                if has_cycle(task_id):
                    log.error(f"Cycle detected in task graph involving {task_id}")
                    return False
        
        return True
    
    def _topological_levels(self) -> List[List[str]]:
        """
        Compute topological levels for parallel execution.
        Returns a list of task ID lists where each inner list can run in parallel.
        """
        in_degree = {task_id: len(self.reverse_graph.get(task_id, set())) 
                     for task_id in self.tasks}
        
        levels = []
        queue = deque([task_id for task_id, degree in in_degree.items() if degree == 0])
        
        while queue:
            level = []
            level_size = len(queue)
            
            for _ in range(level_size):
                task_id = queue.popleft()
                level.append(task_id)
                
                # Reduce in-degree for dependents
                for dependent in self.graph.get(task_id, []):
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)
            
            if level:
                levels.append(level)
        
        # Verify all tasks are scheduled
        scheduled = sum(len(level) for level in levels)
        if scheduled != len(self.tasks):
            missing = set(self.tasks.keys()) - {tid for level in levels for tid in level}
            log.error(f"Not all tasks scheduled. Missing: {missing}")
        
        return levels
    
    async def _execute_task(self, task: DAGTask) -> bool:
        """Execute a single task with retry logic, exponential backoff, and timeout. Returns True if successful."""
        task.status = TaskStatus.RUNNING
        task.start_time = time.time()
        
        log.info(f"Executing task: {task.name} (attempt {task.retry_count + 1}/{task.max_retries + 1})")
        
        try:
            # Execute with timeout if specified
            if task.timeout and task.timeout > 0:
                task.result = await asyncio.wait_for(
                    task.fn(*task.args, **task.kwargs),
                    timeout=task.timeout
                )
            else:
                task.result = await task.fn(*task.args, **task.kwargs)
            
            task.status = TaskStatus.COMPLETED
            task.end_time = time.time()
            elapsed = task.end_time - task.start_time
            log.info(f"✓ Task completed: {task.name} (took {elapsed:.2f}s)")
            return True
            
        except asyncio.TimeoutError as e:
            task.error = e
            task.retry_count += 1
            elapsed = time.time() - task.start_time
            
            if task.retry_count <= task.max_retries:
                backoff = self._calculate_backoff(task, task.retry_count - 1)
                log.warning(f"Task {task.name} timed out after {elapsed:.2f}s "
                           f"(attempt {task.retry_count}/{task.max_retries + 1}). "
                           f"Retrying in {backoff:.2f}s...")
                await asyncio.sleep(backoff)
                task.status = TaskStatus.PENDING
                return False
            else:
                task.status = TaskStatus.FAILED
                task.end_time = time.time()
                log.error(f"✗ Task failed after {task.retry_count} timeout attempts: {task.name}")
                return False
                
        except Exception as e:
            task.error = e
            task.retry_count += 1
            elapsed = time.time() - task.start_time if task.start_time else 0
            
            if task.retry_count <= task.max_retries:
                backoff = self._calculate_backoff(task, task.retry_count - 1)
                log.warning(f"Task {task.name} failed after {elapsed:.2f}s "
                           f"(attempt {task.retry_count}/{task.max_retries + 1}): {e}. "
                           f"Retrying in {backoff:.2f}s...")
                await asyncio.sleep(backoff)
                task.status = TaskStatus.PENDING
                return False
            else:
                task.status = TaskStatus.FAILED
                task.end_time = time.time()
                log.error(f"✗ Task failed after {task.retry_count} attempts: {task.name} - {e}")
                return False
    
    def _calculate_backoff(self, task: DAGTask, attempt: int) -> float:
        """Calculate exponential backoff with jitter for retry delays."""
        backoff = min(task.base_backoff * (2 ** attempt), task.max_backoff)
        jitter = (time.time() % 1) * 0.1 * backoff  # Add 0-10% jitter
        return backoff + jitter
    
    async def run(self, fail_fast: bool = False) -> Dict[str, Any]:
        """
        Execute all tasks respecting dependencies.
        
        Args:
            fail_fast: If True, stop execution on first failure
        
        Returns:
            Dict with execution summary
        """
        if not self._validate_dag():
            raise ValueError("Invalid DAG: contains cycles")
        
        levels = self._topological_levels()
        log.info(f"Execution plan: {len(levels)} levels, {len(self.tasks)} total tasks")
        
        failed_tasks = set()
        skipped_tasks = set()
        
        for level_idx, level in enumerate(levels):
            log.info(f"Level {level_idx + 1}/{len(levels)}: {len(level)} task(s) - {[self.tasks[tid].name for tid in level]}")
            
            # Check if any dependencies failed
            tasks_to_run = []
            for task_id in level:
                task = self.tasks[task_id]
                
                # Check if any dependency failed
                deps_failed = any(dep in failed_tasks for dep in task.depends_on)
                if deps_failed:
                    task.status = TaskStatus.SKIPPED
                    skipped_tasks.add(task_id)
                    log.warning(f"Skipping task {task.name} due to failed dependencies")
                    continue
                
                tasks_to_run.append(task)
            
            if not tasks_to_run:
                continue
            
            # Execute tasks in parallel (respecting max_parallel limit)
            semaphore = asyncio.Semaphore(self.max_parallel)
            
            async def run_with_semaphore(task: DAGTask):
                async with semaphore:
                    return await self._execute_task(task)
            
            results = await asyncio.gather(*[run_with_semaphore(task) for task in tasks_to_run])
            
            # Track failures
            for task, success in zip(tasks_to_run, results):
                if not success:
                    failed_tasks.add(task.id)
                    if fail_fast:
                        log.error(f"Fail-fast enabled, stopping execution due to {task.name} failure")
                        return self._create_summary(failed_tasks, skipped_tasks)
        
        return self._create_summary(failed_tasks, skipped_tasks)
    
    def _create_summary(self, failed_tasks: Set[str], skipped_tasks: Set[str]) -> Dict[str, Any]:
        """Create execution summary."""
        completed = [t for t in self.tasks.values() if t.status == TaskStatus.COMPLETED]
        failed = [t for t in self.tasks.values() if t.status == TaskStatus.FAILED]
        skipped = [t for t in self.tasks.values() if t.status == TaskStatus.SKIPPED]
        
        summary = {
            "total": len(self.tasks),
            "completed": len(completed),
            "failed": len(failed),
            "skipped": len(skipped),
            "success_rate": len(completed) / len(self.tasks) if self.tasks else 0,
            "tasks": {
                "completed": [{"id": t.id, "name": t.name} for t in completed],
                "failed": [{"id": t.id, "name": t.name, "error": str(t.error)} for t in failed],
                "skipped": [{"id": t.id, "name": t.name} for t in skipped],
            }
        }
        
        log.info(f"Execution summary: {len(completed)}/{len(self.tasks)} completed, "
                f"{len(failed)} failed, {len(skipped)} skipped")
        
        return summary
