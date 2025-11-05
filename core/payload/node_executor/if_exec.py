import re
import traceback

from core.customer_script.base import AsyncExecutorVariable, ContextDocument
from core.customer_script.execute import DynamicCodeExecutor
from core.enums.executor import IfModeEnum, AssertionPatternEnum, NodeStatusEnum
from core.executor.core import StepExecutor
from core.payload.utils.tools import search_env
from core.record.utils import IfSuccessProcessObject, IfFailedProcessObject, ExceptionProcessObject
from core.task_object.galobal_mapping import MultiwayTreeNode
from core.task_object.step_mapping import If


class IfRunController(StepExecutor):

    def __init__(self, node: MultiwayTreeNode, in_case=False):
        super().__init__(node)
        self.in_case = in_case

    async def run(self, *args, **kwargs):
        if_info: If = self.node.node.metadata
        result = False
        if if_info.if_mode == IfModeEnum.FAST.value:
            try:
                compare_key = self.replace(if_info.key)
                compare_value = self.replace(if_info.value)
                result = bool(IfAssertionCore(if_info, compare_key, compare_value).assertion())
            except Exception as e:
                raise RuntimeError(ExceptionProcessObject(f"系统错误：If对比出现错误：{e}"))
        elif if_info.if_mode == IfModeEnum.SCRIPT.value:
            try:
                script_code = if_info.script
                env = search_env(self.node)
                variable = AsyncExecutorVariable(self.node, can_set=False)
                context = ContextDocument(variable, self.node.node._print, env_name=env,
                                          dataset_toolkit=None)
                await self.script_notify()
                result = bool(await DynamicCodeExecutor().execute(context, compile_code=script_code))
            except Exception as e:
                traceback.print_exc()
                raise RuntimeError(ExceptionProcessObject(f"系统错误：执行脚本出现错误：{e}"))

        if result:
            self.node.node.status = NodeStatusEnum.RUNNING
            self.node.node.send_step(IfSuccessProcessObject(f"条件分支断言成功，开始执行子步骤"))
        else:
            self.node.node.status = NodeStatusEnum.CONDITIONAL
            self.node.node.send_step(IfFailedProcessObject(f"条件分支断言失败，子步骤将被跳过"))


class IfAssertionCore:

    def __init__(self, if_info: If, compare_key, compare_value):
        self.if_info = if_info
        self.compare_key = compare_key
        self.compare_value = compare_value
        self.result = False
        self.pattern = self.if_info.pattern

    def assertion(self):
        if self.pattern == AssertionPatternEnum.EQ.value:
            self.eq()
        elif self.pattern == AssertionPatternEnum.NEQ.value:
            self.neq()
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
        return self.result

    @classmethod
    def _safe_to_float(cls, value):
        """安全的将值转换为 float，失败则返回 None"""
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def eq(self):
        self.result = str(self.compare_key) == str(self.compare_value)

    def neq(self):
        self.result = str(self.compare_key) != str(self.compare_value)

    def gt(self):
        actual = self._safe_to_float(self.compare_key)
        expected = self._safe_to_float(self.compare_value)
        if actual is not None and expected is not None:
            self.result = actual > expected
        else:
            self.result = False

    def gte(self):
        actual = self._safe_to_float(self.compare_key)
        expected = self._safe_to_float(self.compare_value)
        if actual is not None and expected is not None:
            self.result = actual >= expected
        else:
            self.result = False

    def lt(self):
        actual = self._safe_to_float(self.compare_key)
        expected = self._safe_to_float(self.compare_value)
        if actual is not None and expected is not None:
            self.result = actual < expected
        else:
            self.result = False

    def lte(self):
        actual = self._safe_to_float(self.compare_key)
        expected = self._safe_to_float(self.compare_value)
        if actual is not None and expected is not None:
            self.result = actual <= expected
        else:
            self.result = False

    def contains(self):
        try:
            self.result = str(self.compare_value) in str(self.compare_key)
        except TypeError:
            self.result = False

    def not_contains(self):
        try:
            self.result = str(self.compare_value) not in str(self.compare_key)
        except TypeError:
            self.result = False

    def regex(self):
        try:
            self.result = re.search(str(self.compare_value), str(self.compare_key)) is not None
        except re.error:
            self.result = False
