import os

from fastapi import FastAPI

from core.lua_script.lua_script_manager import LuaScriptManager
from server.routers import task
import dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def pre_load(BASE_DIR):
    dotenv.load_dotenv()
    LuaScriptManager.initialize(BASE_DIR)


pre_load(BASE_DIR)
app = FastAPI(title="AsyncExecutor")

app.include_router(task.task_router)
