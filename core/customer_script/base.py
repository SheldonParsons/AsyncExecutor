import json
from collections import deque
from tkinter.font import names
from types import SimpleNamespace

from core.customer_script._exception import ForbiddenCallException
from core.customer_script.dataset_object import DataSet
from core.payload.variables_controller.variable import GlobalVariable, EnvVariable, TempVariable
from core.utils.line_calling import MockFuncGenerator
from core.utils.pipeline_func import PipelineFuncStaticFuncsMixin

FORBIDDEN_MODULES = [
    'os', 'sys', 'subprocess', 'shutil', 'socket',
    'multiprocessing', 'threading', 'inspect', 'ctypes',
    'cffi', 'pickle', 'marshal', 'resource', 'gc',
    'django', 'rest_framework'
]

FORBIDDEN_FUNCTIONS = ['open']

DEFAULT_RECURSION_LIMIT = 100
DEFAULT_TIMEOUT = 6
PROXY_ASYNC_FUNCTION = "__async_dynamic_main__"


class NoneObject:
    pass


class ForbiddenFunction:

    def __init__(self, name):
        self.name = name

    def __call__(self, *args, **kwargs):
        raise ForbiddenCallException(f"该类禁止调用:{self.name}")


class AsyncExecutorVariable:
    def __init__(self, node, can_set=True):
        self.env = EnvVariable(node, can_set=can_set)
        self.gv = GlobalVariable(node, can_set=can_set)
        self.temp = TempVariable(node, can_set=can_set)
        self.node = node


class ContextDocument:

    def __init__(self, at, _print, env_name, dataset_toolkit=DataSet, has_response=False, response_details=None,
                 error_details=None, database_result=None, error_raise_func=None,
                 request_tools=None, ast_file_callback=None, ast_excel_callback=None, **kwargs):
        self.at = at
        self.print = _print
        self.at.func = MockFuncGenerator()
        self.at.DataSet = dataset_toolkit
        self.at.pipeline = PipelineFuncStaticFuncsMixin
        self.at.env_name = env_name
        self.at.raise_error = error_raise_func
        self.at.database = self.DatabaseResult(database_result)
        self.at.get_position = self.get_position_callback
        self.at.get_main_case_index = self.get_main_case_index_callback
        self.at.request = request_tools
        self.at.AstFile = ast_file_callback
        self.at.AstExcel = ast_excel_callback
        self.at.response = self.get_response_object(response_details, error_details) if has_response else None
        for k, v in kwargs.items():
            self.__dict__[k] = v
        for forbidden_function in FORBIDDEN_FUNCTIONS:
            self.__dict__[forbidden_function] = ForbiddenFunction(forbidden_function)

    def get_main_case_index_callback(self):
        index = -1

        def search_index(_node):
            if _node.parent is None:
                return None
            else:
                metadata = _node.node.metadata
                if metadata.type == "child_case":
                    nonlocal index
                    index = metadata.index_in_global_list
                    return None
                else:
                    return search_index(_node.parent)

        search_index(self.at.node)
        return index

    def get_position_callback(self):

        position_array = deque()

        class _Position:

            def __init__(self, position, name, _type):
                self.position = position
                self.name = name
                self.type = _type

            def to_dict(self):
                return self.__dict__

        def insert_position(_node):

            if _node.parent is None:
                return None
            else:
                metadata = _node.node.metadata
                if metadata.type == "if":
                    position_array.appendleft(_Position(0, metadata.label, metadata.type).to_dict())
                elif metadata.type == "group":
                    position_array.appendleft(_Position(0, metadata.label, metadata.type).to_dict())
                elif metadata.type == "child_multitasker":
                    parent_metadata = _node.parent.node.metadata
                    position_array.appendleft(
                        _Position(metadata.id, parent_metadata.label, parent_metadata.type).to_dict())
                elif metadata.type == "child_step_case":
                    parent_metadata = _node.parent.node.metadata
                    position_array.appendleft(
                        _Position(metadata.id, parent_metadata.label, parent_metadata.type).to_dict())
                    return None
                elif metadata.type == "child_case":
                    parent_metadata = _node.parent.node.metadata
                    position_array.appendleft(
                        _Position(metadata.index_in_global_list, parent_metadata.label, parent_metadata.type).to_dict())
                    return None

            return insert_position(_node.parent)

        insert_position(self.at.node)
        return list(position_array)

    class DatabaseResult:

        def __init__(self, result):
            self.result = result

        def get_result(self):
            return self.result

    def get_response_object(self, response_details, error_details):

        class Response:

            def __init__(self, rd, ed):
                self._body = None
                self._headers = None
                self._code = None
                self._time = None
                self._error = None
                self._has_get = False
                self.is_error = False
                self._rd = rd
                self._ed = ed

            @property
            async def async_body(self):
                if not self._has_get:
                    await self._get_response()
                return self._body

            @property
            async def async_headers(self):
                if not self._has_get:
                    await self._get_response()
                return self._headers

            @property
            async def async_code(self):
                if not self._has_get:
                    await self._get_response()
                return self._code

            @property
            async def async_time(self):
                if not self._has_get:
                    await self._get_response()
                return self._time

            @property
            async def async_error(self):
                if not self._has_get:
                    await self._get_response()
                return self._error

            async def _get_response(self):
                if self._rd is None:
                    self.is_error = True
                    self._error = json.loads(self._ed)
                else:
                    response = SimpleNamespace(**json.loads(self._rd))
                    self._body = response.body
                    self._headers = response.headers
                    self._code = response.status
                    self._time = response.waste_time
                self._has_get = True

            async def get_response(self):
                if not self._has_get:
                    await self._get_response()
                if not self.is_error:
                    return self
                else:
                    return self._error

            async def async_json(self):
                if not self._has_get:
                    await self._get_response()
                try:
                    return json.loads(self._body)
                except json.decoder.JSONDecodeError:
                    return None

            async def async_text(self):
                if not self._has_get:
                    await self._get_response()
                return str(self.async_body)

        return Response(response_details, error_details)

    def to_dict(self):
        return self.__dict__

    def set(self, key, value):
        self.__dict__[key] = value
