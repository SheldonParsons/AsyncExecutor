import asyncio
from collections import deque
from dataclasses import dataclass
from typing import Coroutine, Any, Optional, Tuple

from core.enums.executor import RunningModeEnum
from core.executor.core import RunnerExecutor
from core.utils.tools import SkippedStepResult


@dataclass
class _TaskInfo:
    """用来封装一个协程及其元数据"""
    coro: Coroutine
    metadata: Any = None


class AsyncContext:
    def __init__(self, max_concurrency: Optional[int] = None):
        """
        :param max_concurrency: 最大并发任务数
        """
        self.tasks = []
        self.semaphore = asyncio.Semaphore(max_concurrency) if max_concurrency else None

    async def _run_task(
            self,
            task: RunnerExecutor
    ) -> Any:
        """执行单个任务并处理回调"""
        try:
            before_result = await task.before_callback()
        except Exception as e:
            await task.error_callback(e)
        else:
            try:
                before_result = before_result if isinstance(before_result, Tuple) else (before_result,)
                async with self.semaphore:
                    result = await task.run(*before_result)
                if isinstance(result, SkippedStepResult):
                    await task.skipped_callback(result, *before_result)
                else:
                    await task.after_callback(result, *before_result)
                return result
            except Exception as e:
                await task.error_callback(e, *before_result)

    def run_concurrently(
            self,
            subtasks: deque[RunnerExecutor]
    ) -> asyncio.Task:
        """并发地启动一组任务"""
        task_group = []
        while subtasks:
            task_executor = subtasks.popleft()
            task_obj = asyncio.create_task(
                self._run_task(task_executor))
            self.tasks.append(task_obj)
            task_group.append(task_obj)

        async def wait_group():
            return await asyncio.gather(*task_group)

        return asyncio.create_task(wait_group())

    async def run_sequentially(
            self,
            subtasks: deque[RunnerExecutor]
    ):
        """按顺序逐个执行一组任务"""
        while subtasks:
            await self._run_task(subtasks.popleft())


class TaskRunner:
    def __init__(self, max_concurrency: Optional[int] = None):
        """
        :param max_concurrency: 最大并发任务数
        """
        self.context = AsyncContext(max_concurrency)
        self.max_concurrency = max_concurrency

    async def run(self, *tasks: Coroutine, mode: RunningModeEnum = RunningModeEnum.CONCURRENTLY):
        """
        运行任务
        :param tasks: 要执行的异步任务
        :param mode: 'concurrent' 或 'sequential'
        """
        # 创建顶级任务
        top_level_tasks = []
        for task in tasks:
            task_obj = asyncio.create_task(task)
            top_level_tasks.append(task_obj)

        if mode == RunningModeEnum.CONCURRENTLY:
            await asyncio.gather(*top_level_tasks)
        elif mode == RunningModeEnum.SEQUENTIALLY:
            for task in top_level_tasks:
                await task
        else:
            raise ValueError("Invalid mode. Use 'concurrent' or 'sequential'")

        # 确保所有动态添加的任务都完成
        await self.wait_for_dynamic_tasks()

    async def wait_for_dynamic_tasks(self):
        """等待所有动态添加的任务完成"""
        if self.context.tasks:
            await asyncio.gather(*self.context.tasks)

    def get_running_tasks(self) -> int:
        """获取当前正在运行的任务数"""
        if not self.max_concurrency:
            return 1
        return self.max_concurrency - self.context.semaphore._value
