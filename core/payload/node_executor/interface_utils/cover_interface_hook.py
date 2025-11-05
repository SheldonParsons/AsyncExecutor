import json
from json import JSONDecodeError
from typing import Union

import aiohttp

from core.payload.node_executor.interface_utils.params_maker import ParamsMaker
from core.payload.variables_controller.variable import VariableToller
from core.utils.py_variable_parser import ExchangeToller, ChangeModeEnum


class CoverInterfaceController:

    def __init__(self, interface_info, interface_run_controller, params_maker, global_option):
        self.interface_info = interface_info
        self.interface_run_controller = interface_run_controller
        self.params_maker: ParamsMaker = params_maker
        self.global_option = global_option

    def get_core_variable(self, field, default=None):
        return self.interface_info.setdefault(field, default)

    def get_variable_mapping(self):
        return VariableToller.get_variable_mapping(self.interface_run_controller.node)

    async def async_generate_body(self):
        variable_mapping = self.get_variable_mapping()
        core_interface_info = self.get_core_variable("interface", default={})
        self.interface_run_controller.has_cover_body = True
        old_body = core_interface_info.get('body', None)
        body_type = core_interface_info.get('body_type', 'none')
        core_interface_info['body'] = await self.params_maker.generate_body(old_body, body_type, variable_mapping)
        return core_interface_info['body']

    def cover_body(self, new_body: Union[aiohttp.FormData, str, None]):
        if not isinstance(new_body, (aiohttp.FormData, str, None)):
            raise RuntimeError(f"cover_body 函数发生错误，body的值只能为：[aiohttp.FormData、str、None]")
        self.interface_run_controller.has_cover_body = True
        core_interface_info: dict = self.get_core_variable("interface", default={})
        core_interface_info['body'] = new_body

    async def async_update_body_file(self, field_name, file_object_unique_key, cover_index=0, cover_name=True):
        """
        更新form-data结构的请求体中的文件
        Args:
            field_name: 需要更新的字段
            file_object_unique_key: 需要查找的文件唯一标识
            cover_index: -1：更新字段下所有文件，正整数：更新对应顺序下标，超出下标：不更新
            cover_name: 是否更新文件名
        Returns: None
        """
        core_interface_info = self.get_core_variable("interface", default={})
        body_type = core_interface_info.get('body_type', 'none')
        if body_type != 'form-data':
            return
        body = core_interface_info.get('body', None)
        variable_mapping = self.get_variable_mapping()
        file_object_unique_key = ExchangeToller(file_object_unique_key, variable_mapping,
                                                ChangeModeEnum.CHANGE_EVERY_TIME).replace()

        def search_filepath_callback(_field_name: str, _field_index: int, file_name: str, filepath):
            if _field_name != field_name:
                return filepath, file_name
            else:
                if cover_index == -1 or cover_index == _field_index:
                    ast_file = self.global_option.temp_ast_file_mapping.get(file_object_unique_key, None)
                    if not ast_file:
                        return filepath, file_name
                    else:
                        if cover_name:
                            _file_name = ast_file.filename
                        else:
                            _file_name = file_name
                        return ast_file.filepath, _file_name
                else:
                    return filepath, file_name

        core_interface_info['body'] = await self.params_maker.generate_body(body, body_type, variable_mapping,
                                                                            search_file_callback=search_filepath_callback)
        return core_interface_info['body']

    def generate_url(self):
        core_interface_info: dict = self.get_core_variable("interface", default={})
        variable_mapping = self.get_variable_mapping()
        if self.interface_run_controller.has_cover_url:
            core_interface_info['url'] = ExchangeToller(core_interface_info.get('url', ''), variable_mapping,
                                                        ChangeModeEnum.CHANGE_EVERY_TIME).replace()
            return core_interface_info['url']
        else:
            self.interface_run_controller.has_cover_url = True
            prefix = self.params_maker.get_server_prefix(self.interface_info)
            old_url = core_interface_info.get('url', '')
            generated_url = self.params_maker.combine_url(prefix, old_url)
            core_interface_info['url'] = ExchangeToller(generated_url, variable_mapping,
                                                        ChangeModeEnum.CHANGE_EVERY_TIME).replace()
            return core_interface_info['url']

    def cover_url(self, new_url):
        self.interface_run_controller.has_cover_url = True
        core_interface_info: dict = self.get_core_variable("interface", default={})
        core_interface_info['url'] = new_url

    def generate_url_params(self):
        self.interface_run_controller.has_cover_url_params = True
        core_interface_info: dict = self.get_core_variable("interface", default={})
        pre_params = core_interface_info.get('params', '')
        variable_mapping = self.get_variable_mapping()
        core_interface_info['params'] = ExchangeToller(pre_params, variable_mapping,
                                                       ChangeModeEnum.CHANGE_EVERY_TIME).replace()
        return core_interface_info['params']

    def cover_url_params(self, new_url_params):
        """
        Args:
            new_url_params:可以接收两种类型
                1、无需处理的字符串 eg.:?name=sheldon&age=18&jk=jk1&jk=jk2&jk=3
                2、元组为元素的list:[('name', 'sheldon'), ('age',18)]，将转换为：?name=sheldon&age=18
        Returns:
        """
        if not isinstance(new_url_params, (list, str)):
            raise RuntimeError(f"cover_url_params 函数发生错误，url_params的值只能为：[str,list]")
        if isinstance(new_url_params, list):
            url_params_string_prefix = '?'
            url_params_group = []
            for name, value, *_ in new_url_params:
                url_params_group.append(f"{name}={value}")
            new_url_params = f"{url_params_string_prefix}{'&'.join(url_params_group)}"
        self.interface_run_controller.has_cover_url_params = True
        core_interface_info: dict = self.get_core_variable("interface", default={})
        core_interface_info['params'] = new_url_params

    def generate_headers(self):
        self.interface_run_controller.has_cover_headers = True
        core_interface_info: dict = self.get_core_variable("interface", default={})
        pre_headers = core_interface_info.get('headers', '{}')
        variable_mapping = self.get_variable_mapping()
        headers = ExchangeToller(pre_headers, variable_mapping, ChangeModeEnum.CHANGE_EVERY_TIME).replace()
        core_interface_info['headers'] = headers if isinstance(headers, str) else json.dumps(headers)
        return json.loads(core_interface_info['headers'])

    def cover_headers(self, new_headers):
        if not isinstance(new_headers, (dict, str)):
            raise RuntimeError(f"cover_headers 函数发生错误，headers的值只能为：[str,dict]")
        if isinstance(new_headers, dict):
            try:
                new_headers = json.dumps(new_headers)
            except JSONDecodeError:
                raise RuntimeError(f"cover_headers 函数发生错误，headers无法转换为合法的json字符串")
        self.interface_run_controller.has_cover_headers = True
        core_interface_info: dict = self.get_core_variable("interface", default={})
        core_interface_info['headers'] = new_headers
