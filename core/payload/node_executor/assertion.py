import json
import re
import traceback

from jsonpath_ng import parse

from core.customer_script.base import AsyncExecutorVariable, ContextDocument
from core.customer_script.execute import DynamicCodeExecutor
from core.enums.executor import AssertionModeEnum, AssertionInterfaceRangeEnum, AssertionPatternEnum
from core.executor.core import StepExecutor
from core.payload.utils.tools import search_env
from core.record.utils import AssertionExceptionProcessObject, AssertionSuccessProcessObject, \
    AssertionFailedProcessObject, ExceptionProcessObject, CoreExecReturn
from core.task_object.galobal_mapping import MultiwayTreeNode
from core.task_object.step_mapping import Assertion


class AssertionRunController(StepExecutor):

    def __init__(self, node: MultiwayTreeNode, in_case=False):
        super().__init__(node)
        self.assertion_result = False
        self.in_case = in_case

    async def run(self, *args, **kwargs):
        assertion_info: Assertion = self.node.node.metadata
        ASSERT_MODE_DESC = {
            'interface': '上一个接口',
            'fast': '快速断言',
            'script': '自定义脚本'
        }.get(assertion_info.assert_mode)
        assert_desc = f"[{assertion_info.label}]通过 [{ASSERT_MODE_DESC}] 进行断言。"
        if assertion_info.assert_mode == AssertionModeEnum.LAST_INTERFACE.value:
            response = await self.get_last_interface_response()
            if assertion_info.interface_range == AssertionInterfaceRangeEnum.BODY.value:
                assert_desc += f"断言区域：[响应体]，"
                body = response['body']
                if assertion_info.interface_body_range == 'all':
                    assert_desc += '提取方式：[所有内容]，'
                    compare_key = body
                    assert_desc = await self.assertion_core(assertion_info, compare_key, assert_desc,
                                                            assertion_info.interface_body_value, t='all')
                elif assertion_info.interface_body_range == 'pattern':
                    assert_desc += '提取方式：[Jsonpath匹配]，'
                    try:
                        body = json.loads(body)
                    except Exception as e:
                        raise await self.throw(e, backup_desc='断言错误：Jsonpath提取方式无法解析响应体',
                                               backup_class=AssertionExceptionProcessObject)
                    expr = parse(self.replace(assertion_info.interface_body_jsonpath))
                    assert_desc += f'Jsonpath表达式：[{expr}]，'
                    matches = expr.find(body)
                    compare_key = None
                    if matches:
                        if matches[0].value is True:
                            compare_key = 'true'
                        elif matches[0].value is False:
                            compare_key = 'false'
                        else:
                            compare_key = matches[0].value
                    else:
                        if assertion_info.interface_body_pattern == AssertionPatternEnum.NO_EXIST.value:
                            compare_value = self.replace(assertion_info.interface_body_value)
                            assert_desc += f"断言值：[{compare_value}]，"
                            assert_desc += f"断言方式：[不存在]，"
                            self.assertion_result = True
                            assert_desc += f"断言结果：[成功]"
                        else:
                            raise await self.throw(None, backup_desc=f'断言错误：Jsonpath提取失败：[{expr}]',
                                                   backup_class=AssertionExceptionProcessObject)
                    if assertion_info.interface_body_pattern != AssertionPatternEnum.NO_EXIST.value:
                        assert_desc = await self.assertion_core(assertion_info, compare_key, assert_desc,
                                                                assertion_info.interface_body_value)
            elif assertion_info.interface_range == AssertionInterfaceRangeEnum.HEADER.value:
                assert_desc += f"断言区域：[响应头]，"
                headers = response['headers']
                if not isinstance(headers, dict):
                    headers = json.loads(headers)
                header_key = self.replace(assertion_info.interface_header_key)
                assert_desc += f'header键：[{header_key}]，'
                compare_key = headers.get(header_key, None)
                assert_desc += f'比较键：[{compare_key}]，'
                if assertion_info.interface_header_pattern == AssertionPatternEnum.NO_EXIST.value:
                    compare_value = self.replace(assertion_info.interface_header_value)
                    assert_desc += f"断言值：[{compare_value}]，"
                    assert_desc += f"断言方式：[不存在]，"
                    self.assertion_result = compare_key is None
                    assert_desc += f"断言结果：[{'成功' if self.assertion_result else '失败'}]"
                elif assertion_info.interface_header_pattern == AssertionPatternEnum.EXIST.value:
                    compare_value = self.replace(assertion_info.interface_header_value)
                    assert_desc += f"断言值：[{compare_value}]，"
                    assert_desc += f"断言方式：[存在]，"
                    self.assertion_result = compare_key is not None
                    assert_desc += f"断言结果：[{'成功' if self.assertion_result else '失败'}]"
                else:
                    assert_desc = await self.assertion_core(assertion_info, compare_key, assert_desc,
                                                            assertion_info.interface_header_value, t='header')
            elif assertion_info.interface_range == AssertionInterfaceRangeEnum.CODE.value:
                assert_desc += f"断言区域：[响应码]，"
                compare_key = response['status']
                assert_desc = await self.assertion_core(assertion_info, compare_key, assert_desc,
                                                        assertion_info.interface_code_value, t='code')
        elif assertion_info.assert_mode == AssertionModeEnum.FAST.value:
            compare_key = self.replace(assertion_info.key)
            assert_desc += f"断言键：[{compare_key}]，"
            assert_desc = await self.assertion_core(assertion_info, compare_key, assert_desc,
                                                    assertion_info.value, t='fast')
        elif assertion_info.assert_mode == AssertionModeEnum.SCRIPT.value:
            try:
                script_code = assertion_info.script
                env = search_env(self.node)
                variable = AsyncExecutorVariable(self.node, can_set=False)
                context = ContextDocument(variable, self.node.node._print, env_name=env,
                                          dataset_toolkit=None)
                await self.script_notify()
                self.assertion_result = bool(await DynamicCodeExecutor().compile(script_code).execute(context))
            except Exception as e:
                traceback.print_exc()
                raise RuntimeError(ExceptionProcessObject(f"系统错误：执行脚本出现错误：{e}"))
        if self.assertion_result:
            # 断言成功
            data = {
                "result": 'success',
                'desc': assert_desc
            }
            process_object = AssertionSuccessProcessObject(json.dumps(data, ensure_ascii=False))
            await self.send_step(process_object)
            return CoreExecReturn([process_object], [process_object], [process_object], None)
        else:
            data = {
                "result": 'failed',
                'desc': assert_desc
            }
            raise RuntimeError(AssertionFailedProcessObject(f"断言失败：{assert_desc}"))

    # 断言失败

    async def get_last_interface_response(self):
        try:
            last_interface = self.node.parent.interface_last_node
            if not last_interface:
                raise await self.throw(None, backup_desc='断言错误：无法获取到上一个请求',
                                       backup_class=AssertionExceptionProcessObject)
            last_interface_result = self.node.parent.interface_last_node_result
            if not last_interface_result:
                raise await self.throw(None, backup_desc='断言错误：上一个接口发生异常，无法断言',
                                       backup_class=AssertionExceptionProcessObject)
            last_interface_response_index = f"{last_interface.interface_detail_index}:response"
            result = await self.node.node.record.get_value(last_interface_response_index)
            return json.loads(result)
        except RuntimeError as e:
            raise e
        except Exception as e:
            raise await self.throw(e, backup_desc='系统错误：解析上一个请求体发生错误')

    async def assertion_core(self, assertion_info: Assertion, compare_key, assert_desc: str, compare_value,
                             t='jsonpath'):
        compare_value = self.replace(compare_value)
        assert_desc += f"断言值：[{compare_value}]，"
        if t == 'jsonpath':
            assertion_core = AssertionJsonpathCore(assertion_info, compare_key, compare_value, assert_desc)
        elif t == 'all':
            assertion_core = AssertionAllCore(assertion_info, compare_key, compare_value, assert_desc)
        elif t == 'header':
            assertion_core = AssertionHeaderCore(assertion_info, compare_key, compare_value, assert_desc)
        elif t == 'code':
            assertion_core = AssertionCodeCore(assertion_info, compare_key, compare_value, assert_desc)
        else:
            assertion_core = AssertionFastCore(assertion_info, compare_key, compare_value, assert_desc)
        assertion_core.assertion()
        self.assertion_result = assertion_core.result
        return assertion_core.assert_desc


class AssertionCore:

    def __init__(self, assertion_info: Assertion, compare_key, compare_value, assert_desc: str, t='jsonpath'):
        self.assertion_info = assertion_info
        self.compare_key = compare_key
        self.compare_value = compare_value
        self.assert_desc = assert_desc
        self.result = False
        self.pattern = {
            'jsonpath': self.assertion_info.interface_body_pattern,
            'all': self.assertion_info.interface_body_pattern,
            'header': self.assertion_info.interface_header_pattern,
            'code': self.assertion_info.interface_code_pattern,
            'fast': self.assertion_info.pattern
        }.get(t)

    def assertion(self):
        if self.pattern == AssertionPatternEnum.EQ.value:
            self.eq()
        elif self.pattern == AssertionPatternEnum.NEQ.value:
            self.neq()
        elif self.pattern == AssertionPatternEnum.EXIST.value:
            self.exist()
        elif self.pattern == AssertionPatternEnum.NO_EXIST.value:
            self.no_exist()
        elif self.pattern == AssertionPatternEnum.GT.value:
            self.gt()
        elif self.pattern == AssertionPatternEnum.GTE.value:
            self.gte()
        elif self.pattern == AssertionPatternEnum.LT.value:
            self.lt()
        elif self.pattern == AssertionPatternEnum.LTE.value:
            self.lte()
        elif self.pattern == AssertionPatternEnum.CONTAINS.value:
            self.contains()
        elif self.pattern == AssertionPatternEnum.NOT_CONTAINS.value:
            self.not_contains()
        elif self.pattern == AssertionPatternEnum.REGEX.value:
            self.regex()
        elif self.pattern == AssertionPatternEnum.INSET.value:
            self.inset()
        elif self.pattern == AssertionPatternEnum.UN_INSET.value:
            self.un_inset()

    @classmethod
    def _safe_to_float(cls, value):
        """安全的将值转换为 float，失败则返回 None"""
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def eq(self):
        self.assert_desc += f"断言方式：[等于]，"
        self.result = str(self.compare_key) == str(self.compare_value)
        self.assert_desc += f"断言结果：[{'成功' if self.result else '失败'}]。"

    def neq(self):
        self.assert_desc += f"断言方式：[不等于]，"
        self.result = str(self.compare_key) != str(self.compare_value)
        self.assert_desc += f"断言结果：[{'成功' if self.result else '失败'}]"

    def exist(self):
        self.assert_desc += f"断言方式：[存在]，"

    def no_exist(self):
        self.assert_desc += f"断言方式：[不存在]，"

    def gt(self):
        self.assert_desc += f"断言方式：[大于]，"
        actual = self._safe_to_float(self.compare_key)
        expected = self._safe_to_float(self.compare_value)
        if actual is not None and expected is not None:
            self.result = actual > expected
        else:
            self.result = False
            self.assert_desc += "类型错误：无法比较非数字类型，"
        self.assert_desc += f"断言结果：[{'成功' if self.result else '失败'}]"

    def gte(self):
        self.assert_desc += f"断言方式：[大于等于]，"
        actual = self._safe_to_float(self.compare_key)
        expected = self._safe_to_float(self.compare_value)
        if actual is not None and expected is not None:
            self.result = actual >= expected
        else:
            self.result = False
            self.assert_desc += "类型错误：无法比较非数字类型，"
        self.assert_desc += f"断言结果：[{'成功' if self.result else '失败'}]"

    def lt(self):
        self.assert_desc += f"断言方式：[小于]，"
        actual = self._safe_to_float(self.compare_key)
        expected = self._safe_to_float(self.compare_value)
        if actual is not None and expected is not None:
            self.result = actual < expected
        else:
            self.result = False
            self.assert_desc += "类型错误：无法比较非数字类型，"
        self.assert_desc += f"断言结果：[{'成功' if self.result else '失败'}]"

    def lte(self):
        self.assert_desc += f"断言方式：[小于等于]，"
        actual = self._safe_to_float(self.compare_key)
        expected = self._safe_to_float(self.compare_value)
        if actual is not None and expected is not None:
            self.result = actual <= expected
        else:
            self.result = False
            self.assert_desc += "类型错误：无法比较非数字类型，"
        self.assert_desc += f"断言结果：[{'成功' if self.result else '失败'}]"

    def contains(self):
        self.assert_desc += f"断言方式：[包含]，"
        try:
            self.result = str(self.compare_value) in str(self.compare_key)
        except TypeError:
            self.result = False
        self.assert_desc += f"断言结果：[{'成功' if self.result else '失败'}]"

    def not_contains(self):
        self.assert_desc += f"断言方式：[不包含]，"
        try:
            self.result = str(self.compare_value) not in str(self.compare_key)
        except TypeError:
            self.result = False
        self.assert_desc += f"断言结果：[{'成功' if self.result else '失败'}]"

    def regex(self):
        self.assert_desc += f"断言方式：[正则匹配]，"
        try:
            self.result = re.search(str(self.compare_value), str(self.compare_key)) is not None
        except re.error:
            self.result = False
            self.assert_desc += f"正则表达式错误：'{self.compare_value}' 无效，"
        self.assert_desc += f"断言结果：[{'成功' if self.result else '失败'}]"

    def inset(self):
        self.assert_desc += f"断言方式：[属于集合]，"
        collection = self.compare_value
        # 如果期望值是字符串，按逗号分割成列表
        if isinstance(collection, str):
            collection = [item.strip() for item in collection.split(',')]

        try:
            self.result = str(self.compare_key) in collection
        except TypeError:  # 如果 collection 不是可迭代对象
            self.result = False
            self.assert_desc += f"类型错误：期望值不是一个有效的集合，"
        self.assert_desc += f"断言结果：[{'成功' if self.result else '失败'}]"

    def un_inset(self):
        self.assert_desc += f"断言方式：[不属于集合]，"
        collection = self.compare_value
        if isinstance(collection, str):
            collection = [item.strip() for item in collection.split(',')]

        try:
            self.result = str(self.compare_key) not in collection
        except TypeError:
            self.result = False
            self.assert_desc += f"类型错误：期望值不是一个有效的集合，"
        self.assert_desc += f"断言结果：[{'成功' if self.result else '失败'}]"


class AssertionJsonpathCore(AssertionCore):

    def exist(self):
        self.assert_desc += f"断言方式：[存在]，"
        self.result = True
        self.assert_desc += f"断言结果：[成功]"

    def no_exist(self):
        self.assert_desc += f"断言方式：[不存在]，"
        self.result = False
        self.assert_desc += f"断言结果：[失败]"


class AssertionAllCore(AssertionCore):

    def exist(self):
        self.assert_desc += f"断言方式：[存在]，"
        self.result = len(str(self.compare_key)) > 0
        self.assert_desc += f"断言结果：[{'成功' if self.result else '失败'}]"

    def no_exist(self):
        self.assert_desc += f"断言方式：[不存在]，"
        self.result = len(str(self.compare_key)) == 0
        self.assert_desc += f"断言结果：[成功]"


class AssertionHeaderCore(AssertionCore):
    def __init__(self, *args, **kwargs):
        super().__init__(t='header', *args, **kwargs)


class AssertionFastCore(AssertionCore):
    def __init__(self, *args, **kwargs):
        super().__init__(t='fast', *args, **kwargs)


class AssertionCodeCore(AssertionCore):
    def __init__(self, *args, **kwargs):
        super().__init__(t='code', *args, **kwargs)
