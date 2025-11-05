"""
内部执行入口
"""
import dotenv
from core.executor.runner import MainExecutor


async def run_task(exec_dict, record):
    dotenv.load_dotenv()
    await MainExecutor().run(exec_dict, record)
