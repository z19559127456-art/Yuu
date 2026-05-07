"""
Task queue with concurrency control and retry handler.
"""
import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class Priority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass(order=True)
class TaskItem:
    priority: int
    enqueued_at: float
    task_id: str = field(compare=False)
    coro: Callable = field(compare=False)
    timeout: float = field(compare=False, default=60.0)


class TaskQueue:
    """Async task queue with priority and max concurrency."""

    def __init__(self, max_concurrent: int = 5):
        self._max_concurrent = max_concurrent
        self._queue: asyncio.PriorityQueue[TaskItem] = asyncio.PriorityQueue()
        self._running: set[str] = set()
        self._semaphore: asyncio.Semaphore = asyncio.Semaphore(max_concurrent)
        self._workers: list[asyncio.Task] = []
        self._active = False

    @property
    def running_count(self) -> int:
        return len(self._running)

    @property
    def max_concurrent(self) -> int:
        return self._max_concurrent

    def enqueue(
        self,
        task_id: str,
        coro: Callable,
        priority: Priority = Priority.NORMAL,
        timeout: float = 60.0,
    ):
        """Add a task to the queue."""
        self._queue.put_nowait(TaskItem(
            priority=priority.value,
            enqueued_at=time.time(),
            task_id=task_id,
            coro=coro,
            timeout=timeout,
        ))

    async def start(self, worker_count: int = 1):
        """Start background workers that drain the queue."""
        if self._active:
            return
        self._active = True
        self._workers = [
            asyncio.create_task(self._worker_loop(), name=f"taskq-worker-{i}")
            for i in range(worker_count)
        ]

    async def stop(self, wait: bool = True):
        """Stop all workers."""
        self._active = False
        if wait:
            await asyncio.gather(*self._workers, return_exceptions=True)
        else:
            for w in self._workers:
                w.cancel()
        self._workers.clear()
        self._running.clear()

    async def join(self):
        """Wait until the queue is empty and all tasks complete."""
        while not self._queue.empty() or self._running:
            await asyncio.sleep(0.1)

    async def _worker_loop(self):
        while self._active:
            try:
                item = await asyncio.wait_for(
                    self._queue.get(), timeout=1.0
                )
            except asyncio.TimeoutError:
                continue

            async with self._semaphore:
                self._running.add(item.task_id)
                try:
                    await asyncio.wait_for(item.coro(), timeout=item.timeout)
                except asyncio.TimeoutError:
                    logger.warning("Task %s timed out after %ss", item.task_id, item.timeout)
                except Exception:
                    logger.exception("Task %s failed", item.task_id)
                finally:
                    self._running.discard(item.task_id)
                    self._queue.task_done()


class RetryHandler:
    """Retry with exponential backoff and jitter."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        jitter: bool = True,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter

    async def run(
        self,
        fn: Callable,
        *args,
        is_retriable: Optional[Callable[[Exception], bool]] = None,
        **kwargs,
    ) -> Any:
        """Execute fn with retry logic. Raises last exception on exhaustion."""
        last_exc = None
        for attempt in range(self.max_retries + 1):
            try:
                return await fn(*args, **kwargs)
            except Exception as e:
                last_exc = e
                if is_retriable and not is_retriable(e):
                    raise
                if attempt < self.max_retries:
                    delay = self._backoff(attempt)
                    logger.warning(
                        "Attempt %d/%d failed: %s. Retrying in %.1fs...",
                        attempt + 1, self.max_retries + 1, e, delay,
                    )
                    await asyncio.sleep(delay)
        raise last_exc  # type: ignore[misc]

    def _backoff(self, attempt: int) -> float:
        import random
        delay = min(self.base_delay * (self.backoff_factor ** attempt), self.max_delay)
        if self.jitter:
            delay *= 0.5 + random.random() * 0.5
        return delay
