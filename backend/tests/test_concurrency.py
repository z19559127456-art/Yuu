"""
Tests for TaskQueue and RetryHandler.
"""
import pytest
import asyncio
from app.concurrency import TaskQueue, RetryHandler, Priority


class TestTaskQueue:
    @pytest.mark.asyncio
    async def test_enqueue_dequeue(self):
        q = TaskQueue(max_concurrent=5)
        results = []

        async def dummy():
            results.append("done")
            return "ok"

        q.enqueue("task1", dummy)
        await q.start(worker_count=1)
        await asyncio.sleep(0.3)
        await q.stop()
        assert "done" in results

    @pytest.mark.asyncio
    async def test_max_concurrent_respected(self):
        q = TaskQueue(max_concurrent=2)
        running = 0
        max_running = 0

        async def slow_task(n):
            nonlocal running, max_running
            running += 1
            max_running = max(max_running, running)
            await asyncio.sleep(0.2)
            running -= 1
            return n

        for i in range(6):
            q.enqueue(f"task{i}", lambda n=i: slow_task(n))

        await q.start(worker_count=2)
        await asyncio.sleep(1.5)
        await q.stop()
        assert max_running <= 2, f"Expected max 2 concurrent, got {max_running}"

    @pytest.mark.asyncio
    async def test_priority_order(self):
        """PriorityQueue pops lowest value first, so LOW=0 comes first."""
        q = TaskQueue(max_concurrent=1)
        exec_order = []

        async def make_task(n):
            async def _task():
                exec_order.append(n)
            return _task

        q.enqueue("low", await make_task(3), priority=Priority.LOW)  # value 0 → pops first
        q.enqueue("high", await make_task(1), priority=Priority.HIGH)  # value 2 → pops last
        q.enqueue("normal", await make_task(2), priority=Priority.NORMAL)  # value 1 → pops second

        await q.start(worker_count=1)
        await asyncio.sleep(0.5)
        await q.stop()
        assert exec_order == [3, 2, 1], f"Expected [3,2,1] (LOW→NORMAL→HIGH), got {exec_order}"

    @pytest.mark.asyncio
    async def test_timeout_kills_task(self):
        q = TaskQueue(max_concurrent=1)
        task_done = False

        async def hang_forever():
            nonlocal task_done
            await asyncio.sleep(100)
            task_done = True

        q.enqueue("hanging", hang_forever, timeout=0.2)
        await q.start(worker_count=1)
        await asyncio.sleep(0.5)
        await q.stop()
        assert task_done is False, "Task should have been timed out"

    def test_properties(self):
        q = TaskQueue(max_concurrent=3)
        assert q.max_concurrent == 3
        assert q.running_count == 0


class TestRetryHandler:
    @pytest.mark.asyncio
    async def test_success_on_first_try(self):
        handler = RetryHandler(max_retries=3)
        call_count = 0

        async def succeed():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await handler.run(succeed)
        assert result == "ok"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_then_succeed(self):
        handler = RetryHandler(max_retries=3, base_delay=0.01)
        call_count = 0

        async def fail_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("not yet")
            return "finally ok"

        result = await handler.run(fail_twice)
        assert result == "finally ok"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_exhaust_retries(self):
        handler = RetryHandler(max_retries=2, base_delay=0.01)
        call_count = 0

        async def always_fail():
            nonlocal call_count
            call_count += 1
            raise ValueError("always fail")

        with pytest.raises(ValueError, match="always fail"):
            await handler.run(always_fail)
        assert call_count == 3  # original + 2 retries

    @pytest.mark.asyncio
    async def test_non_retriable_exception(self):
        handler = RetryHandler(max_retries=3, base_delay=0.01)

        async def fail():
            raise KeyError("not retriable")

        with pytest.raises(KeyError):
            await handler.run(fail, is_retriable=lambda e: isinstance(e, ValueError))

    def test_backoff_increases(self):
        handler = RetryHandler(base_delay=1.0, backoff_factor=2.0, jitter=False)
        d0 = handler._backoff(0)
        d1 = handler._backoff(1)
        d2 = handler._backoff(2)
        assert d0 == 1.0
        assert d1 == 2.0
        assert d2 == 4.0

    def test_backoff_capped(self):
        handler = RetryHandler(base_delay=1.0, backoff_factor=10.0, max_delay=5.0, jitter=False)
        d = handler._backoff(3)
        assert d == 5.0  # capped at max_delay
