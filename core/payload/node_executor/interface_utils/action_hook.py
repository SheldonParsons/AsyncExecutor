import asyncio
import json
import re
import traceback
from json import JSONDecodeError
from types import SimpleNamespace
from jsonpath_ng import parse
from lxml import etree

from core.customer_script.base import AsyncExecutorVariable, ContextDocument
from core.customer_script.execute import DynamicCodeExecutor
from core.enums.executor import ExtractSourceType, RangeType, ExtractVariableType
from core.executor.core import Executor, StepExecutor
from core.payload.utils.tools import search_env
from core.payload.variables_controller.variable import VariableToller
from core.record.utils import ExceptionProcessObject
from core.utils.py_variable_parser import ExchangeToller, ChangeModeEnum

SLEEP_HOOK_MAX_TIME = 60


class EmptyHook(Executor):

    def __init__(self, *args, **kwargs):
        pass

    async def run(self, *args, **kwargs):
        pass


class ScriptHook(StepExecutor):

    async def run(self, data, has_response=False, response_details=None, error_details=None, request_tools=None,
                  *args, **kwargs):
        try:
            action = SimpleNamespace(**data)
            script_code = action.data['code']
            env = search_env(self.node)
            variable = AsyncExecutorVariable(self.node)
            context = ContextDocument(variable, self.node.node._print, has_response=has_response, env_name=env,
                                      dataset_toolkit=None, response_details=response_details,
                                      error_details=error_details, request_tools=request_tools)
            await self.script_notify()
            await DynamicCodeExecutor().execute(context, compile_code=script_code)
        except Exception as e:
            traceback.print_exc()
            raise RuntimeError(ExceptionProcessObject(f"系统错误：执行脚本出现错误：{e}"))


class TimeHook(StepExecutor):
    async def run(self, data, response_details=None, *args, **kwargs):
        action = SimpleNamespace(**data)
        sleep_time = action.data['time']
        try:
            sleep_time = int(sleep_time)
            await self.sleep_notify(sleep_time)
            await asyncio.sleep(min(sleep_time / 1000, SLEEP_HOOK_MAX_TIME))
        except ValueError as e:
            raise RuntimeError(ExceptionProcessObject(f"系统错误：等待时间转义错误：{sleep_time}"))
        except Exception as e:
            raise RuntimeError(ExceptionProcessObject(f"系统错误：等待时间时出现错误：{e}"))


class ExtractHook(StepExecutor):
    async def run(self, data, response_details: str = None, *args, **kwargs):
        action_data = SimpleNamespace(**data["data"])
        try:
            variable_name = action_data.name
            if response_details is None:
                await self.warning_notify(f"警告：响应内容获取失败，无法进行参数提取：{variable_name}，已停止提取")
                return
            else:
                response = json.loads(response_details)
            source = action_data.source
            extract_range = action_data.extract_range
            regexp = action_data.regexp
            jsonpath = action_data.jsonpath
            xpath = action_data.xpath
            header_name: str = action_data.header_name
            cookie_name: str = action_data.cookie_name
            waste_time_unit: bool = action_data.waste_time_unit
            t = action_data.t
            is_success_extract = True
            value = "空"
        except Exception as e:
            raise RuntimeError(ExceptionProcessObject(f"系统错误：提取参数获取信息失败：{e}"))
        try:
            extract_tag = ""
            if source == ExtractSourceType.RESPONSE_HEADER.value:
                headers = response["headers"]
                if not isinstance(headers, dict):
                    headers = json.loads(headers)
                extract_tag = header_name
                header_value = headers.get(header_name, None)
                if header_value is None:
                    is_success_extract = False
                else:
                    value = header_value
            elif source == ExtractSourceType.RESPONSE_COOKIE.value:
                def get_cookie_value(cookie_str: str, key: str) -> str | None:
                    cookies = cookie_str.split(';')
                    for item in cookies:
                        if '=' in item:
                            k, v = item.strip().split('=', 1)
                            if k.strip() == key:
                                return v.strip()
                    return None

                headers = response["headers"]
                if not isinstance(headers, dict):
                    headers = json.loads(headers)
                cookie_str = None
                for key, value in headers.items():
                    if key.lower() == 'set-cookie' or key.lower() == 'cookie':
                        cookie_str = value
                        break
                if cookie_str is None:
                    is_success_extract = False
                else:
                    extract_tag = cookie_name
                    cookie_value = get_cookie_value(cookie_str, cookie_name)
                    if cookie_value is None:
                        is_success_extract = False
                    else:
                        value = cookie_value
            elif source == ExtractSourceType.WASTE_TIME.value:
                extract_tag = "响应时间"
                if waste_time_unit:
                    value = float(response["waste_time"])
                else:
                    value = float(response["waste_time"] * 1000)

            elif source == ExtractSourceType.RESPONSE_BODY.value:
                body = response["body"]
                if extract_range == RangeType.WHOLE_BODY.value:
                    value = body
                    extract_tag = "响应整体数据"
                elif extract_range == RangeType.JSONPATH.value:
                    variable_mapping = VariableToller.get_variable_mapping(self.node)
                    _expression = ExchangeToller(jsonpath['expression'], variable_mapping,
                                                 ChangeModeEnum.CHANGE_EVERY_TIME).replace()
                    extract_tag = _expression
                    expr = parse(_expression)
                    if isinstance(body, dict) is False:
                        try:
                            body = json.loads(body)
                        except JSONDecodeError:
                            raise RuntimeError("响应体不是json")
                    matches = expr.find(body)
                    if matches:
                        if matches[0].value is True:
                            value = 'true'
                        elif matches[0].value is False:
                            value = 'false'
                        else:
                            value = matches[0].value
                    else:
                        await self.warning_notify(f"警告：参数替换失败，jsonpath匹配失败：{variable_name}")
                        is_success_extract = False
                elif extract_range == RangeType.XPATH.value:
                    if not isinstance(body, str):
                        body = str(body)
                    tree = etree.HTML(body)
                    extract_tag = xpath['expression']
                    items = tree.xpath(extract_tag)
                    if len(items) > 0:
                        if isinstance(items[0], str):
                            value = items[0]
                        else:
                            value = items[0].text
                    else:
                        await self.warning_notify(f"警告：参数替换失败，Xpath查询失败：{variable_name}")
                        is_success_extract = False
                elif extract_range == RangeType.REGEXP.value:
                    if not isinstance(body, str):
                        body = str(body)
                    extract_tag = regexp['expression']
                    match = re.search(extract_tag, body)
                    _index = int(regexp['template'][1:])
                    if match:
                        try:
                            value = match.group(_index - 1)
                        except (IndexError, ValueError):
                            await self.warning_notify(f"警告：参数替换失败，正则匹配失败，下标越界：{variable_name}")
                            is_success_extract = False
                    else:
                        await self.warning_notify(f"警告：参数替换失败，正则匹配失败：{variable_name}")
                        is_success_extract = False

            variables = AsyncExecutorVariable(self.node)
            if is_success_extract:
                if t == ExtractVariableType.GLOBAL.value:
                    variables.gv.set(variable_name, value)
                elif t == ExtractVariableType.TEMP.value:
                    variables.temp.set(variable_name, value)
                elif t == ExtractVariableType.ENV.value:
                    variables.env.set(variable_name, value)
                await self.extract_notify({
                    "name": variable_name,
                    "save_type": t,
                    "source": source,
                    "extract_range": extract_range,
                    "extract_value": value,
                    "extract_tag": extract_tag
                })
        except Exception as e:
            traceback.print_exc()
            raise RuntimeError(ExceptionProcessObject(f"系统错误：提取参数失败：{e}"))


dispatch_hook = (
    lambda t: (
        {
            1: ScriptHook,
            2: TimeHook,
            4: ExtractHook
        }.get(int(t), EmptyHook)
    )
)
