import asyncio
import time

import psutil

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


class ServerSourceInfo:

    def __init__(self):
        self.memory_total = None
        self.memory_available = None
        self.memory_used = None

    def get_info(self):
        mem = psutil.virtual_memory()
        self.memory_total = round(mem.total / 1024 / 1024, 2)
        self.memory_available = round(mem.available / 1024 / 1024, 2)
        self.memory_used = round(mem.used / 1024 / 1024, 2)
        return self.__dict__
