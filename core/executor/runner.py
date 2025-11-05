import asyncio
import json
import os
import shutil
import traceback
from functools import partial
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlparse

import aiohttp

from core.enums.executor import ExecType
from core.executor.core import Executor
from core.global_client.async_redis import close_async_pool
from core.payload.core import PayloadExecutor
from core.payload.node_executor.interface_utils.http_client import HttpClient
from core.record.task_record import TaskRecord
from core.signals.django_sync import DjangoSyncSignal
from core.task_object.generate_object import generate, GlobalOption


class MainExecutor(Executor):

    def __init__(self, exec_type=ExecType.DJANGO):
        self.exec_type = exec_type

    async def run(self, exec_dict, record):
        global_options: GlobalOption = generate(exec_dict, record, self)
        self.exec_type = ExecType(global_options.task_info.rpc_method)
        # 创建record对象
        task_record = TaskRecord(global_options)
        try:
            async with HttpClient().get_session() as session:
                global_options.set_session(session)
                await PreActionExecutor().run(global_options)
                await TaskExecutor().run(global_options, task_record)
        except Exception as e:
            traceback.print_exc()
        await PostActionExecutor().run(global_options, task_record)


class PreActionExecutor(Executor):

    async def run(self, global_options):

        # 缓存文件，这个步骤会为origin_file_mapping下的元素添加exec_path缓存地址
        await self.cache_file(global_options)
        # rpc：开始任务
        await DjangoSyncSignal.start_task_rcp(global_options.task_info.id, global_options.record.id,
                                              global_options.main_executor.exec_type)

    async def cache_file(self, global_options):
        current_dir = Path(__file__).resolve().parent
        parent_dir = current_dir.parent
        target_dir = parent_dir / "static" / "task_temp" / str(global_options.task_info.id)
        target_dir.mkdir(parents=True, exist_ok=True)
        if global_options.main_executor.exec_type == ExecType.DJANGO:
            await self._cache_file_by_local(global_options, target_dir)
        elif global_options.main_executor.exec_type == ExecType.REMOTE:
            await self._cache_file_by_remote(global_options)

    @classmethod
    async def _cache_file_by_local(cls, global_options, target_dir):
        loop = asyncio.get_running_loop()
        tasks = []
        for file_name, path_dict in global_options.global_cache.origin_file_mapping.items():
            path_object = SimpleNamespace(**path_dict)
            get_file_path = path_object.local
            target_file_path = f"{target_dir}/{file_name}"
            blocking_copy = partial(shutil.copy, get_file_path, target_file_path)
            task = loop.run_in_executor(None, blocking_copy)
            tasks.append(task)
            path_dict['exec_path'] = target_file_path
        await asyncio.gather(*tasks)

    @classmethod
    async def _cache_file_by_remote(cls, global_options):
        for file_name, path_dict in global_options.global_cache.origin_file_mapping.items():
            path_object = SimpleNamespace(**path_dict)
            remote_url = path_object.remote
            async with aiohttp.ClientSession() as session:
                async with session.get(remote_url) as response:
                    response.raise_for_status()
                    path = urlparse(remote_url).path
                    filename = os.path.basename(path)
                    target_file_path = await global_options.temp_ast_file_manager.add(response,
                                                                                      special_filename=filename)
                    path_dict['exec_path'] = target_file_path


class TaskExecutor(Executor):
    async def run(self, global_options: GlobalOption, task_record):
        await PayloadExecutor(global_options, task_record).run()


class PostActionExecutor(Executor):
    async def run(self, global_options: GlobalOption, task_record: TaskRecord):
        # rpc：结束任务
        current_record_list = await DjangoSyncSignal.end_task_rcp(global_options.task_info.id, global_options.record.id,
                                                                  global_options.main_executor.exec_type)
        await self._clean_temp_file(global_options.task_info.id)
        # 缓存redis内容
        await self._save_redis_cache(task_record, global_options.record.record_backup_index, current_record_list)
        # 关闭资源
        await global_options.http_session.close()
        await global_options.database_controller.close()
        await global_options.temp_ast_file_manager.close()
        await close_async_pool()

    @classmethod
    async def _save_redis_cache(cls, task_record, record_key, current_record_list):
        current_dir = Path(__file__).resolve().parent
        parent_dir = current_dir.parent
        target_dir = parent_dir / "static" / "record_redis_backup"
        await cls.sync_record_file_from_ast(current_record_list, target_dir, record_key)
        await task_record.cache_redis_record(record_key, target_dir)

    @classmethod
    async def _clean_temp_file(cls, task_id=None):
        try:
            current_dir = Path(__file__).resolve().parent
            parent_dir = current_dir.parent
            target_dir = parent_dir / "static" / "task_temp" / str(task_id)
            loop = asyncio.get_running_loop()
            blocking_func = partial(shutil.rmtree, target_dir)
            await loop.run_in_executor(None, blocking_func)
        except Exception as e:
            # TODO: 捕获错误
            traceback.print_exc()

    @classmethod
    async def sync_record_file_from_ast(cls, file_list_no_suffix, directory, record_key: str):
        file_prefix = record_key.split(":record:")[0].replace(":", "_")
        if not os.path.isdir(directory):
            return

        keep_set = {name.replace(':', '_') + '.json' for name in json.loads(file_list_no_suffix)}
        loop = asyncio.get_running_loop()

        def find_files_to_delete():
            files_to_delete = []
            try:
                for filename in os.listdir(directory):
                    if filename.startswith(file_prefix) and filename.endswith('.json') and filename not in keep_set:
                        files_to_delete.append(os.path.join(directory, filename))
            except OSError as e:
                print(f"Error accessing directory {directory}: {e}")
            return files_to_delete

        files_to_delete = await loop.run_in_executor(None, find_files_to_delete)
        if not files_to_delete:
            return
        delete_tasks = [
            loop.run_in_executor(None, partial(os.remove, filepath))
            for filepath in files_to_delete
        ]

        results = await asyncio.gather(*delete_tasks, return_exceptions=True)
        if len(results) == 0:
            print("Nothing to delete")

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Failed to delete {files_to_delete[i]}: {result}")
            else:
                print(f"Successfully deleted: {files_to_delete[i]}")
