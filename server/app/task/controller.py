import asyncio
import signal
import time
import traceback

import psutil

from core.global_client.async_redis import close_async_pool
from core.global_client.sync_redis import close_sync_pool
from core.inner_entry import run_task
from global_object.signal import MemoryResourceLimitExceededError


class TaskController:

    def __call__(self, request):
        print(f"request:{request}")
        print(type(request))

        async def main_task():
            await run_task(request['exec'], request['record'])
            await self._inner_process_done_callback()

        self._safe_run(main_task)

    def _safe_run(self, async_func):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        main_task_obj = loop.create_task(async_func())

        def signal_handler_bridge(signum, frame):
            msg = "MEMORY_LIMIT" if signum == signal.SIGUSR1 else "FORCE_STOP"
            loop.call_soon_threadsafe(lambda: main_task_obj.cancel(msg))

        signal.signal(signal.SIGUSR1, signal_handler_bridge)
        signal.signal(signal.SIGUSR2, signal_handler_bridge)

        try:
            print(">>> [Launcher] 启动 Event Loop...", flush=True)
            loop.run_until_complete(main_task_obj)

        except asyncio.CancelledError as e:

            cancel_msg = str(e.args[0]) if e.args else ""

            if cancel_msg == "MEMORY_LIMIT":
                print(">>> [Launcher] 成功捕获：内存超限 (由信号触发)", flush=True)

                traceback.print_exc()
            elif cancel_msg == "FORCE_STOP":
                print(">>> [Launcher] 成功捕获：主动停止", flush=True)
            else:
                print(f">>> [Launcher] 任务被取消，原因未知: {e}", flush=True)

        except MemoryResourceLimitExceededError:
            print(">>> [Launcher] 捕获到同步阶段的内存异常", flush=True)

        except Exception as e:
            print(">>> [Launcher] 捕获到其他异常")
            traceback.print_exc()

        finally:
            print(">>> [Launcher] 关闭 Loop", flush=True)
            signal.signal(signal.SIGUSR1, signal.SIG_DFL)
            signal.signal(signal.SIGUSR2, signal.SIG_DFL)
            # loop.close()

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
