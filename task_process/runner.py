import os
import signal
import traceback

from global_object.signal import MemoryResourceLimitExceededError, TimeResourceLimitExceededError, \
    ResourceLimitExceededError


def task_wrapper(target_func, request):
    """
    设置信号处理程序，以便父进程（监控器）可以发送信号
    来优雅地终止它。
    """

    def signal_handler(signum, frame):
        if signum == signal.SIGUSR1:
            print(f"PID {os.getpid()}: 收到 SIGUSR1 (内存超限)，正在退出...")
            raise MemoryResourceLimitExceededError("Memory limit exceeded")
        elif signum == signal.SIGUSR2:
            print(f"PID {os.getpid()}: 收到 SIGUSR2 (超时)，正在退出...")
            raise TimeResourceLimitExceededError("Time limit exceeded")

    # 注册进程信号
    signal.signal(signal.SIGUSR1, signal_handler)
    signal.signal(signal.SIGUSR2, signal_handler)

    try:
        print(f"--- 子进程 {os.getpid()} 开始执行任务 ---")
        target_func(request)
        print(f"--- 子进程 {os.getpid()} 任务执行完毕 ---")
    except ResourceLimitExceededError as e:
        print(f"--- 子进程 {os.getpid()} 因资源限制而终止: {e} ---")
        # 这里可以执行特定的清理回调
    except Exception as e:
        traceback.print_exc()
        print(f"--- 子进程 {os.getpid()} 任务执行出错: {e} ---")
        # 这里可以执行特定的清理回调
    finally:
        print(f"--- 子进程 {os.getpid()} 退出 ---")
