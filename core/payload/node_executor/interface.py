import copy
import json
import traceback
import uuid
from urllib.parse import parse_qsl

from multidict import MultiDict

from core.enums.executor import RedisDetailTypeEnum
from core.executor.core import StepExecutor
from core.payload.node_executor.interface_utils.action_hook import dispatch_hook
from core.payload.node_executor.interface_utils.cover_interface_hook import CoverInterfaceController
from core.payload.node_executor.interface_utils.params_maker import ParamsMaker
from core.payload.node_executor.interface_utils.sender import HttpSender
from core.payload.utils.tools import get_current_ms
from core.payload.variables_controller.variable import VariableToller
from core.record.utils import ExceptionProcessObject, StepDetail, \
    InterfaceSuccessFinishProcessObject, InterfaceExceptionProcessObject, InterfaceErrorFinishProcessObject, \
    CoreExecReturn, InterfaceWarningProcessObject
from core.task_object.galobal_mapping import MultiwayTreeNode
from core.utils.py_variable_parser import ExchangeToller, ChangeModeEnum


class InterfaceRunController(StepExecutor):

    def __init__(self, node: MultiwayTreeNode, in_case=False):
        super().__init__(node)
        self.request_details = None
        self.response_details = None
        self.error_details = None
        self.return_list = None
        self.in_case = in_case
        self.has_raise = False
        self.start_time = None
        self.has_cover_body = False
        self.has_cover_url = False
        self.has_cover_url_params = False
        self.has_cover_headers = False

    async def run(self, *args, **kwargs):
        try:
            pm = ParamsMaker(self.node)
            # 获取cache接口信息
            interface_info = copy.deepcopy(pm.get_interface_info())
            # 获取服务URL前缀
            prefix = pm.get_server_prefix(interface_info)
        except Exception as e:
            traceback.print_exc()
            raise await self.throw(e, backup_desc='系统错误：获取请求信息及服务前缀失败')
        try:
            request_tools = CoverInterfaceController(interface_info, self, pm, self.node.node.global_option)
            # 执行前置操作
            await self.run_pre_actions(interface_info, request_tools=request_tools)
        except Exception as e:
            traceback.print_exc()
            raise await self.throw(e, backup_desc='系统错误：接口前置操作执行出错')
        try:
            # 获取接口参数：临时参数>环境参数>全局参数
            variable_mapping = VariableToller.get_variable_mapping(self.node)
            # helper code：提取请求参数从cache中
            core_interface_info = interface_info.get('interface', {})
            # 通过变量替换参数、构造body请求体
            method = core_interface_info.get('method', 'get')
            body = await pm.generate_body(core_interface_info.get('body', None),
                                          core_interface_info.get('body_type', 'none'),
                                          variable_mapping)
            if self.has_cover_url:
                url = core_interface_info.get('url', '')
                url = ExchangeToller(url, variable_mapping, ChangeModeEnum.CHANGE_EVERY_TIME).replace()
            else:
                pre_url = pm.combine_url(prefix, core_interface_info.get('url', ''))
                url = ExchangeToller(pre_url, variable_mapping, ChangeModeEnum.CHANGE_EVERY_TIME).replace()
            headers = core_interface_info.get('headers', '{}')
            headers = ExchangeToller(headers, variable_mapping, ChangeModeEnum.CHANGE_EVERY_TIME).replace()
            headers = json.loads(headers) if isinstance(headers, str) else headers
            params = core_interface_info.get('params', '')
            params = ExchangeToller(params, variable_mapping, ChangeModeEnum.CHANGE_EVERY_TIME).replace()
            params_dict = self.get_params_dict(params)
            self.request_details: str = self._get_request_details(method, url, headers, body, params_dict)
        except Exception as e:
            traceback.print_exc()
            raise await self.throw(e, backup_desc='系统错误：请求提取参数异常')
        try:
            self.start_time = get_current_ms()
            # 发送请求
            await HttpSender(method, url, body, params_dict, headers, self.node.node.global_option.http_session,
                             self.finish_callback, self.exception_callback)()
        except Exception as e:
            traceback.print_exc()
            await self.throw(e, backup_desc='系统错误', backup_class=InterfaceExceptionProcessObject)
        try:
            # 执行后置操作
            await self.run_after_actions(interface_info)
        except Exception as e:
            traceback.print_exc()
            raise await self.throw(e, backup_desc='系统错误：接口后置操作执行出错')
        return self.return_list

    @classmethod
    def get_params_dict(cls, params):
        params_dict = MultiDict()
        for key, value in parse_qsl(params[1:]):
            params_dict.add(key, value)
        return params_dict

    async def finish_callback(self, response_details: str, timing, process):
        self.response_details = response_details
        should_raise = self.node.node.metadata.should_raise
        if should_raise:
            try:
                raise_code = int(self.node.node.metadata.raise_code)
            except ValueError:
                process_object = InterfaceWarningProcessObject(desc=f"警告：异常响应码解析失败，已自动转为：500")
                await self.send_step(process_object)
                raise_code = 500
            response_code = int(json.loads(response_details)['status'])
            if response_code == raise_code:
                self.has_raise = True
                data = {
                    "request": self.request_details,
                    "response": self.response_details,
                    "error": json.dumps({
                        "type": "CustomerError",
                        "info": "用户自定义错误",
                        "waste_time": get_current_ms() - self.start_time,
                        "time": get_current_ms()
                    }),
                    "timing": timing.to_json(),
                    "process": process.to_json(),
                    "result": 'customer_failed'
                }
                step_detail = await self.make_interface_object_to_redis(type=RedisDetailTypeEnum.INTERFACE_ERROR.value,
                                                                        data=data)
                self.node.interface_detail_index = f"{self.node.node.record.redis_index}:{step_detail.type}_detail:{step_detail.index}"
                self.node.parent.interface_last_node = self.node
                self.node.parent.interface_last_node_result = True
                error_object = InterfaceErrorFinishProcessObject(
                    f"接口发送异常：[{self.node.node.metadata.label}]，错误响应码：{response_code}", detail=step_detail)
                # await self.send_step(error_object)
                raise RuntimeError(error_object)
        data = {
            "request": self.request_details,
            "response": self.response_details,
            "timing": timing.to_json(),
            "process": process.to_json(),
            "result": 'success'
        }
        step_detail = await self.make_interface_object_to_redis(type=RedisDetailTypeEnum.INTERFACE_SUCCESS.value,
                                                                data=data)
        self.node.interface_detail_index = f"{self.node.node.record.redis_index}:{step_detail.type}_detail:{step_detail.index}"
        self.node.parent.interface_last_node = self.node
        self.node.parent.interface_last_node_result = True
        process_object = InterfaceSuccessFinishProcessObject(
            f"接口发送完成：[{self.node.node.metadata.label}]", detail=step_detail)
        await self.send_step(process_object)
        self.return_list = CoreExecReturn([process_object], [process_object], [process_object], None)

    async def exception_callback(self, error_details: str, timing, process):
        if not self.has_raise:
            self.error_details = error_details
            data = {
                "request": self.request_details,
                "response": '{}',
                "error": self.error_details or {},
                "timing": timing.to_json(),
                "process": process.to_json(),
                "result": 'failed'
            }
            print(f"data:{data}")
            step_detail: StepDetail = await self.make_interface_object_to_redis(
                type=RedisDetailTypeEnum.INTERFACE_ERROR.value,
                data=data)
            self.node.parent.interface_last_node_result = False
            process_object = InterfaceErrorFinishProcessObject(
                f"接口发送异常：[{self.node.node.metadata.label}]", detail=step_detail)
            raise RuntimeError(process_object)

    async def make_interface_object_to_redis(self, type, data):
        step_detail = StepDetail(type=type, index=uuid.uuid4().hex, data=data)
        await self.node.node.batch_add_detail(step_detail)
        return step_detail

    async def run_pre_actions(self, interface_info, request_tools=None):
        pre_actions = interface_info.get('pre_actions', None)
        if pre_actions is None:
            raise RuntimeError(ExceptionProcessObject("系统错误：没有找到接口的前置操作"))
        if len(pre_actions) > 0:
            await self.send_system_notice_step(f"开始前置操作...")
        for pre_action in pre_actions:
            await dispatch_hook(pre_action['t'])(self.node).run(pre_action, request_tools=request_tools)

    async def run_after_actions(self, interface_info):
        after_actions = interface_info.get('after_actions', None)
        if after_actions is None:
            raise RuntimeError(ExceptionProcessObject("系统错误：没有找到接口的后置操作"))
        if len(after_actions) > 0:
            await self.send_system_notice_step(f"开始后置操作...")
        for after_action in after_actions:
            await dispatch_hook(after_action['t'])(self.node).run(after_action, has_response=True,
                                                                  response_details=self.response_details,
                                                                  error_details=self.error_details)

    @classmethod
    def _get_request_details(cls, method, url, headers, body, params):
        # 处理请求体
        body_info = None
        try:
            if body:
                content_type = headers.get('Content-Type', '')
                # 处理 multipart/form-data
                if 'multipart/form-data' in content_type:
                    body_info = "multipart/form-data (content hidden)"
                # 处理 JSON
                elif 'application/json' in content_type:
                    if isinstance(body, bytes):
                        body_info = body.decode('utf-8')
                    else:
                        body_info = body
                else:
                    if isinstance(body, bytes):
                        body_info = body.decode('utf-8', errors='replace')
                    else:
                        body_info = body
        except Exception as e:
            body_info = f"Error reading body: {str(e)}"

        def url_params_multi_dict_to_string(multi_params):
            prefix = "?"
            group = []
            for key, value in multi_params.items():
                group.append(f"{key}={value}")
            if len(group) > 0:
                return f"{prefix}{'&'.join(group)}"
            else:
                return ''

        return json.dumps({
            "method": method,
            "url": str(url),
            "headers": headers,
            "query_params": url_params_multi_dict_to_string(params),
            "body": body_info,
            "time": get_current_ms()
        }, ensure_ascii=False)
