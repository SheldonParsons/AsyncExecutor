import asyncio
import time

from core.global_client.async_redis import close_async_pool
from core.global_client.sync_redis import close_sync_pool
from core.inner_entry import run_task


class TaskController:

    def __call__(self, request):
        print(f"request:{request}")
        print(type(request))

        async def main_task():
            await run_task(request['exec'], request['record'])
            await self._inner_process_done_callback()

        asyncio.run(main_task())

    @staticmethod
    async def _inner_process_done_callback():
        await close_async_pool()
        close_sync_pool()

    @classmethod
    def done_callback(cls, task_id, results, start_time):
        print(
            f"CALLBACK: 任务 {task_id} 已完成。峰值内存: {results['peak_memory_mb']:.2f} MB，耗时:{time.time() - start_time:.2f}秒")
