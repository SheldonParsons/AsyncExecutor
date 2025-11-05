import os
import random
import string
from typing import Union, TypeVar, Generic

import aiofiles
from io import BytesIO

from core.task_object.generate_object import GlobalOption

FileLikeObjectType = TypeVar("FileLikeObjectType", BytesIO, None)
GlobalOptionType = TypeVar("GlobalOptionType", GlobalOption, None)


class AstFile(Generic[FileLikeObjectType, GlobalOptionType]):

    def __init__(self, global_option):
        self.file: FileLikeObjectType = None
        self.filepath: Union[str, os.PathLike[str]] = ""
        self.filename = None
        self.cover_file = False
        self.global_option: GlobalOptionType = global_option

        self._is_load = False
        self._is_save_to_temp = False
        self._is_system_file = False

    def close(self):
        """
        delete file bytes in memory
        Returns:
        """
        self.file = None

    async def save(self, file: FileLikeObjectType) -> str:
        """
        cover old file and save new file to temp dir if needed
        Returns: file unique key in global AstFile mapping
        """
        self.file = file
        self._is_save_to_temp = True
        # 创建一个当前文件唯一ID，绑定当前对象到global_option里面去，最后需要返回这个唯一ID，用于全局上下文里面找到这个对象
        object_unique_key = f"{self._generate_suffix_key()}-{self.filename}"
        self.global_option.add_temp_ast_file(object_unique_key, self)
        # 如果是系统文件，需要判断需不需要cover原始文件
        if self._is_system_file:
            # 如果需要cover原始文件，覆盖系统文件中原始文件，不需要更改filepath
            if self.cover_file:
                self.global_option.temp_ast_file_manager.replace_file_content(self.filepath, file)
                return object_unique_key
        # 如果不需要cover原始文件，创建临时文件夹，将新文件保存进去，获取临时文件路径，更新filepath
        # 如果不是系统文件，创建临时文件夹，将新文件保存进去，获取临时文件路径，更新filepath
        self.filepath = await self.global_option.temp_ast_file_manager.add(file)
        return object_unique_key

    def get_filepath(self, filename: str):
        self._is_save_to_temp = True
        object_unique_key = f"{self._generate_suffix_key()}-{self.filename}"
        self.global_option.add_temp_ast_file(object_unique_key, self)
        if self._is_system_file:
            if self.cover_file:
                return self.filepath, object_unique_key
        self.filepath = self.global_option.temp_ast_file_manager.generate_unique_filepath(filename)
        return self.filepath, object_unique_key

    def load(self, file: FileLikeObjectType, filename: str):
        self.file = file
        self.file.name = filename
        self._is_load = True
        self.filename = filename
        self._is_system_file = False

    async def load_from_system(self, filename: str, cover_file=False):
        """
        generate file like object, it will cover current object param self.file
        Args:
            filename: file name in AsyncExecutor
            cover_file: is cover system original file
        Returns: self

        """
        self._is_system_file = True
        self.cover_file = cover_file
        self.filename = filename
        self.filepath = self._search_system_file(filename)
        if not self.filepath:
            raise RuntimeError(f"系统中找不到该文件：{filename}")
        self.file = await self._get_file(self.filepath)

        self._is_load = True
        return self

    def _search_system_file(self, filename) -> Union[str, None]:
        """
        search file in system by global_option
        Args:
            filename: original filename
        Returns: file path
        """
        file_mapping: dict = self.global_option.global_cache.origin_file_mapping
        for full_name, path_dict in file_mapping.items():
            if filename in full_name:
                return path_dict.get('exec_path')
        return None

    @classmethod
    async def _get_file(cls, filepath: str):
        async with aiofiles.open(filepath, 'rb') as f:
            origin_file = await f.read()
            file_like_object = BytesIO(origin_file)
            file_like_object.name = os.path.basename(filepath)

            return file_like_object

    @classmethod
    def _generate_suffix_key(cls, length=8) -> str:
        characters = string.ascii_letters + string.digits
        random_list = random.choices(characters, k=length)
        return "".join(random_list)
