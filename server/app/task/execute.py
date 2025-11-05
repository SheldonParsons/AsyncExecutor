import os
import uuid

from fastapi import BackgroundTasks, Request

from core.record.redis_client import AsyncRedisClient
from server.app.task.controller import TaskController
from server.routers.task import task_router
from task_process.monitor import monitor_and_run_task


@task_router.post("/execute")
async def execute(background_tasks: BackgroundTasks, request: Request):
    task_id = f"task-{uuid.uuid4().hex[:8]}"
    print(f"API [主线程 {os.getpid()}]: 收到请求，启动任务 {task_id}")
    # Uvicorn单独运行
    background_tasks.add_task(
        monitor_and_run_task,
        task_id=task_id,
        target_func=TaskController(),
        done_callback=TaskController.done_callback,
        request=await request.json()
    )

    return {"message": "任务已提交", "task_id": task_id}


@task_router.post("/restore_record")
async def restore_record(request: Request):
    data = await request.json()
    record_backup_index = data['record_backup_index']
    try:
        AsyncRedisClient.sync_import_from_file(record_backup_index)
        return {"message": "已恢复"}
    except Exception as e:
        return {"message": f"恢复异常：{e}"}
