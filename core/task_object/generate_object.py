import asyncio
import os
import shutil
import tempfile
import uuid
from io import BytesIO
from typing import Union, Any, Optional

import aiofiles
import aiohttp
from aiohttp import ClientSession

from core.task_object.case_list import CaseList
from core.task_object.child_case_list import ChildCaseList
from core.task_object.database_client import DatabaseController
from core.task_object.global_cache import GlobalCache
from core.task_object.record import Record
from core.task_object.step_mapping import StepMapping
from core.task_object.task_info import TaskInfo


class AstTempFileController:
    def __init__(self):
        self._base_temp_path: Optional[str] = tempfile.mkdtemp(prefix="async_manager_")

    async def add(self, file_like_object: Union[aiohttp.ClientResponse, BytesIO], special_filename=None) -> str:
        if not self._base_temp_path:
            raise RuntimeError("管理器已被关闭，无法创建新文件。")

        # 1. 从 file-like-object 中获取文件名，提供一个默认值以防万一
        filename = special_filename or getattr(file_like_object, 'name', 'unnamed_file.bin')

        # 2. 创建一个唯一的下级目录来存放文件
        unique_subdir = os.path.join(self._base_temp_path, str(uuid.uuid4()))
        os.makedirs(unique_subdir)

        # 3. 构建文件的完整存储路径
        full_file_path = os.path.join(unique_subdir, filename)

        # 4. 异步写入文件
        try:

            if isinstance(file_like_object, aiohttp.ClientResponse):
                await self._stream_http_response_to_file(file_like_object, full_file_path)
            else:
                # 确保从头读取 file-like-object
                file_like_object.seek(0)
                content = file_like_object.read()
                async with aiofiles.open(full_file_path, 'wb') as f:
                    await f.write(content)

        except Exception as e:
            shutil.rmtree(unique_subdir)
            raise e

        # 5. 返回创建的文件的绝对路径
        return os.path.abspath(full_file_path)

    @staticmethod
    async def _stream_http_response_to_file(response: aiohttp.ClientResponse, save_path: str):
        """流式写入文件"""
        async with aiofiles.open(save_path, "wb") as f:
            async for chunk in response.content.iter_chunked(1024 * 16):
                await f.write(chunk)

    def generate_unique_filepath(self, filename: str) -> str:
        if not self._base_temp_path:
            raise RuntimeError("管理器已被关闭，无法生成新路径。")
        unique_subdir_name = str(uuid.uuid4())
        full_file_path = os.path.join(self._base_temp_path, unique_subdir_name, filename)
        return os.path.abspath(full_file_path)

    @classmethod
    async def replace_file_content(cls, absolute_path: str, new_content_object: BytesIO) -> bool:
        if not os.path.exists(absolute_path):
            raise FileNotFoundError(f"错误：目标文件不存在于 '{absolute_path}'")

        try:
            new_content_object.seek(0)
            new_content = new_content_object.read()
            async with aiofiles.open(absolute_path, 'wb') as f:
                await f.write(new_content)

            return True

        except Exception as e:
            raise e

    async def close(self):
        if self._base_temp_path and os.path.exists(self._base_temp_path):
            await asyncio.to_thread(shutil.rmtree, self._base_temp_path)
            print("清理AstTempFileController完成。")
            self._base_temp_path = None  # 标记为已清理
        else:
            print("临时文件夹不存在或已被清理，无需操作。")


class GlobalOption:

    def __init__(self, task_info=None, case_list=None, child_case_list=None, step_mapping=None,
                 global_cache=None, record=None, main_executor=None, case_steps_snapshot=None):
        self.task_info = TaskInfo(**task_info)
        self.case_list = CaseList(case_list)
        self.child_case_list = ChildCaseList(child_case_list)
        self.step_mapping = StepMapping(step_mapping)
        self.global_cache = GlobalCache(**global_cache)
        self.record = Record(**record)
        self.main_executor = main_executor
        self.case_steps_snapshot = case_steps_snapshot
        self.http_session: Union[None, ClientSession] = None
        self.database_controller = DatabaseController()
        self.temp_ast_file_mapping = {}
        self.temp_ast_file_manager = AstTempFileController()

    def set_session(self, session: ClientSession):
        self.http_session = session

    def add_temp_ast_file(self, key: str, ast_file: Any):
        self.temp_ast_file_mapping[key] = ast_file


def generate(exec_dict, record, main_executor):
    return GlobalOption(**exec_dict, record=record, main_executor=main_executor)
