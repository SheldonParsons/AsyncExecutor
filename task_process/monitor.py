import multiprocessing
import os
import signal
import time
import traceback

import psutil

from task_process.runner import task_wrapper


def monitor_and_run_task(
        task_id,
        target_func,
        done_callback,
        request
):
    """
        负责启动并监控一个运行目标任务的子进程。
    """
    process = None
    peak_memory_usage = 0.0
    start_time = time.time()
    try:
        process_args = (target_func, request)

        process = multiprocessing.Process(
            target=task_wrapper,
            args=process_args
        )
        process.start()

        print(f"进程 [监控器 线程 {os.getpid()}] 开始监控任务 {task_id} (子进程 PID: {process.pid})")

        pid = process.pid
        p_info = None

        # 确保我们能获取到进程句柄
        while p_info is None and process.is_alive():
            try:
                p_info = psutil.Process(pid)
            except psutil.NoSuchProcess:
                time.sleep(0.1)  # 进程可能还未完全启动

        if p_info is None:
            print(f"进程 [监控器 线程 {os.getpid()}] 无法获取进程 {pid} 的句柄。")

        while p_info and process.is_alive():
            # 检查内存
            try:
                memory_usage = p_info.memory_info().rss
                peak_memory_usage = max(peak_memory_usage, memory_usage)
                if memory_usage > (int(os.getenv('MULTI_PROCESS_MEMORY_LIMIT')) * 1024 * 1024):
                    print(
                        f"进程 [监控器] 任务 {task_id} 内存超限 ({memory_usage / 1024 / 1024:.2f}MB)，发送 SIGUSR1 (Memory limit)...")
                    os.kill(pid, signal.SIGUSR1)
                    break
            except psutil.NoSuchProcess:
                break

            time.sleep(1)

        # 等待进程退出
        process.join(timeout=int(os.getenv('WAITING_MULTI_PROCESS_TIME')))
        if process.is_alive():
            print(f"进程 [监控器] 进程 {pid} 未能优雅退出，强制 kill。")
            process.kill()

    except Exception as e:
        traceback.print_exc()
        print(f"进程 [监控器] 监控任务 {task_id} 时发生未知错误: {e}")
        if process and process.is_alive():
            process.kill()
    finally:
        print(f"进程 [监控器 线程 {os.getpid()}] 完成监控任务 {task_id}")
        profiling_results = {
            'peak_memory_mb': peak_memory_usage / 1024 / 1024
        }
        if callable(done_callback):
            done_callback(task_id, profiling_results, start_time)
