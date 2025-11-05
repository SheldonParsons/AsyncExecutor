import json
import traceback
from types import SimpleNamespace
from typing import Callable, Union

import aiofiles
import aiohttp

from core.enums.executor import InterfaceDataTypeEnum, BodyCurrentType
from core.payload.variables_controller.variable import Variable
from core.record.utils import ExceptionProcessObject
from core.task_object.galobal_mapping import MultiwayTreeNode
from core.utils.py_variable_parser import ChangeModeEnum, ExchangeToller


class ParamsMaker:

    def __init__(self, node):
        self.node: MultiwayTreeNode = node

    async def generate_body(self, body, body_type, variable_mapping,
                            search_file_callback: Union[None, Callable[[str, int, str, str], tuple[str, str]]] = None):
        try:
            if body_type == BodyCurrentType.NONE.value:
                return None
            elif body_type == BodyCurrentType.RAW.value:
                if len(body) == 0:
                    return ""
                else:
                    return ExchangeToller(body, variable_mapping, ChangeModeEnum.CHANGE_EVERY_TIME).replace()
            elif body_type == BodyCurrentType.JSON.value:
                def replace_hook(s):
                    return ExchangeToller(s, variable_mapping, ChangeModeEnum.CHANGE_EVERY_TIME).replace()

                dict_body = self.transform_interface_data(self.dict_to_object(body.get('data')), replace_hook)
                if dict_body is None:
                    return None
                else:
                    return json.dumps(dict_body, ensure_ascii=False)
            elif body_type == BodyCurrentType.X_WWW_FORM_URLENCODED:
                return ExchangeToller(body, variable_mapping, ChangeModeEnum.CHANGE_EVERY_TIME).replace()
            elif body_type == BodyCurrentType.FORM_DATA.value:
                return await self.make_form_data_body(body, variable_mapping, search_file_callback)
        except Exception as e:
            raise RuntimeError(f"系统错误：获取请求体失败：\n{traceback.format_exc()}")
        raise RuntimeError(f"系统错误：获取请求体失败[1]：\n{traceback.format_exc()}")

    def get_server_prefix(self, interface_info):
        project_id, env = Variable._gpe(self.node)
        env_mapping = self.node.node.global_option.global_cache.origin_project_env_server_mapping.get(str(project_id),
                                                                                                      None)
        if env_mapping is None:
            raise RuntimeError(ExceptionProcessObject("系统错误：没有找到对应的环境信息"))
        server_mapping = env_mapping.get(env, None)
        if server_mapping is None:
            raise RuntimeError(ExceptionProcessObject("系统错误：无法找到接口对应的环境信息"))
        server = interface_info.get("interface", {}).get('server', None)
        if server is None:
            raise RuntimeError(ExceptionProcessObject("系统错误：获取接口服务失败"))
        server_info = server_mapping.get(server, None)
        if server_info is None:
            raise RuntimeError(ExceptionProcessObject("系统错误：获取接口服务信息失败"))
        prefix = server_info.get("prefix", None)
        if prefix is None:
            raise RuntimeError(ExceptionProcessObject("系统错误：获取服务信息前缀失败"))
        return prefix

    def get_interface_info(self):
        interface_info = self.node.node.global_option.global_cache.origin_interface_mapping.get(
            str(self.node.node.metadata.interface), None)
        if interface_info is None:
            raise RuntimeError(ExceptionProcessObject("系统错误：没有找到对应的接口信息"))
        return interface_info

    @staticmethod
    def combine_url(domain: str, path: str):
        """
        将domain和path组合成合法的URL，正确处理斜杠问题
        """
        # 处理空值情况
        domain = domain.strip() if domain else ""
        path = path.strip() if path else ""

        if not domain:
            return path
        if not path:
            return domain.rstrip('/')

        # 规范化domain：确保不以斜杠结尾
        if domain.endswith('/'):
            domain = domain.rstrip('/')

        # 规范化path：确保以斜杠开头
        if not path.startswith('/'):
            path = '/' + path

        return domain + path

    @classmethod
    def transform_interface_data(cls, interface_data, replace_vars_func):
        """转换InterfaceJsonData对象为最终数据"""
        # 阶段1: 构建原始数据结构和类型映射
        data_tree, type_tree = cls._build_data_and_type_trees(interface_data)
        if data_tree is None:
            return None
        # 阶段2: 全局变量替换
        json_str = json.dumps(data_tree)
        replaced_str = replace_vars_func(json_str)
        replaced_data = json.loads(replaced_str)

        # 阶段3: 类型转换
        return cls._convert_data_types(replaced_data, type_tree)

    @classmethod
    def _build_data_and_type_trees(cls, node):
        """递归构建数据树和类型树"""
        if node is None:
            return None, None
        if node.t == InterfaceDataTypeEnum.OBJECT.value:
            data_obj = {}
            type_obj = {}
            for child in node.children:
                child_data, child_type = cls._build_data_and_type_trees(child)
                data_obj[child.name] = child_data
                type_obj[child.name] = child_type
            return data_obj, type_obj

        elif node.t == InterfaceDataTypeEnum.ARRAY.value:
            data_list = []
            type_list = []
            for child in node.children:
                child_data, child_type = cls._build_data_and_type_trees(child)
                data_list.append(child_data)
                type_list.append(child_type)
            return data_list, type_list

        else:  # 基本类型
            return node.default, node.t

    @classmethod
    def _convert_data_types(cls, data, type_info):
        """根据类型信息转换数据类型"""
        if isinstance(type_info, dict):  # 对象类型
            return {k: cls._convert_data_types(data.get(k), v) for k, v in type_info.items()}

        elif isinstance(type_info, list):  # 数组类型
            return [cls._convert_data_types(data[i], type_info[i]) for i in range(len(type_info))]

        else:  # 基本类型
            return cls._convert_primitive_value(data, type_info)

    @classmethod
    def _convert_primitive_value(cls, value, data_type):
        """转换基本类型值"""
        if value is None:
            return cls._default_for_type(data_type)

        try:
            if data_type == InterfaceDataTypeEnum.INTEGER.value:
                return int(value)
            elif data_type == InterfaceDataTypeEnum.NUMBER.value:
                return float(value)
            elif data_type == InterfaceDataTypeEnum.BOOLEAN.value:
                if isinstance(value, bool):
                    return value
                return str(value).lower() in ("true", "1", "yes")
            elif data_type == InterfaceDataTypeEnum.STRING.value:
                return str(value)
            elif data_type == InterfaceDataTypeEnum.NULL.value:
                return None
        except (TypeError, ValueError):
            pass

        return cls._default_for_type(data_type)

    @classmethod
    def _default_for_type(cls, data_type):
        """获取各类型的默认值"""
        return {
            InterfaceDataTypeEnum.INTEGER.value: 0,
            InterfaceDataTypeEnum.NUMBER.value: 0.0,
            InterfaceDataTypeEnum.BOOLEAN.value: True,
            InterfaceDataTypeEnum.STRING.value: "",
            InterfaceDataTypeEnum.NULL.value: None
        }.get(data_type, None)

    @classmethod
    def dict_to_object(cls, d):
        """
        递归地将字典转换为 SimpleNamespace 对象。

        Args:
            d (dict): 要转换的字典。

        Returns:
            SimpleNamespace: 转换后的对象。
        """
        if isinstance(d, dict):
            # 递归地处理字典中的每个值
            return SimpleNamespace(**{k: cls.dict_to_object(v) for k, v in d.items()})
        elif isinstance(d, list):
            # 如果值是列表，则递归处理列表中的每个元素
            return [cls.dict_to_object(item) for item in d]
        else:
            # 如果值既不是字典也不是列表，直接返回它
            return d

    async def make_form_data_body(self, origin_body, variable_mapping,
                                  search_file_callback=Union[None, Callable[[str, int, str, str], tuple[str, str]]]):
        form_data = aiohttp.FormData()
        if isinstance(origin_body, aiohttp.FormData):
            return await self.make_new_form_data_body(origin_body, variable_mapping, search_file_callback)
        for field in origin_body['data']:
            if field['t'] != InterfaceDataTypeEnum.FILES.value:
                if field['t'] == InterfaceDataTypeEnum.ARRAY.value:
                    for child_value in field['child_list']:
                        if isinstance(child_value, str):
                            new_child_value = ExchangeToller(child_value, variable_mapping,
                                                             ChangeModeEnum.CHANGE_EVERY_TIME).replace()
                        else:
                            new_child_value = child_value
                        form_data.add_field(name=field['name'], value=new_child_value,
                                            content_type=field['content_type'])
                else:
                    if isinstance(field['default'], str):
                        new_value = ExchangeToller(field['default'], variable_mapping,
                                                   ChangeModeEnum.CHANGE_EVERY_TIME).replace()
                    else:
                        new_value = field['default']
                    form_data.add_field(name=field['name'], value=new_value, content_type=field['content_type'])
            else:
                file_index = 0
                for file in field['file_list']:
                    path = self.node.node.global_option.global_cache.origin_file_mapping.get(
                        file.get('index_name')).get('exec_path')
                    if search_file_callback is not None:
                        path, file_name = search_file_callback(field['name'], file_index, file['name'], path)
                    else:
                        file_name = file['name']
                    async with aiofiles.open(path, mode="rb") as f:
                        content = await f.read()
                        form_data.add_field(name=field['name'], value=content, content_type=field['content_type'],
                                            filename=file_name)
                    file_index += 1
        return form_data

    @classmethod
    async def make_new_form_data_body(cls, origin_body: aiohttp.FormData, variable_mapping, search_file_callback=Union[
        None, Callable[[str, int, str, str], tuple[str, str]]]):
        new_form_data = aiohttp.FormData()
        file_index = 0
        file_name_cache = []
        for filed_name, content_type, value, *_ in origin_body._fields:
            filename = filed_name.get('filename', None)
            name = filed_name.get('name', '')
            file_name_cache.append(name)
            content_type = content_type.get('Content-Type', 'text/plain')
            if filename is None:
                new_value = ExchangeToller(value, variable_mapping, ChangeModeEnum.CHANGE_EVERY_TIME).replace()
                new_form_data.add_field(name=name, value=new_value, content_type=content_type)
            else:
                if search_file_callback is not None:
                    path, filename = search_file_callback(name, file_index, filename, None)
                    if path is not None:
                        async with aiofiles.open(path, mode="rb") as f:
                            value = await f.read()
                new_form_data.add_field(name=name, value=value, content_type=content_type,
                                        filename=filename)
            if name in file_name_cache:
                file_index += 1
        return new_form_data
