import traceback

from core.customer_script.base import AsyncExecutorVariable, ContextDocument
from core.customer_script.execute import DynamicCodeExecutor
from core.enums.executor import IfModeEnum, NodeStatusEnum, RaiseErrorTypeEnum
from core.executor.core import StepExecutor
from core.payload.node_executor.if_exec import IfAssertionCore
from core.payload.node_executor.step_public_object.error_target_object import ErrorRaiseTarget
from core.payload.utils.tools import search_env
from core.record.utils import ExceptionProcessObject, ErrorWarningProcessObject
from core.task_object.galobal_mapping import MultiwayTreeNode
from core.task_object.step_mapping import Error


class ErrorRunController(StepExecutor):

    def __init__(self, node: MultiwayTreeNode, in_case=False):
        super().__init__(node)
        self.in_case = in_case

    async def run(self, *args, **kwargs):
        error_info: Error = self.node.node.metadata
        result = False
        script_result = True
        if error_info.error_mode == IfModeEnum.FAST.value:
            try:
                print(f"self.node.parent:{self.node.parent}")
                compare_key = self.replace(error_info.key, real_node=self.node.parent)
                compare_value = self.replace(error_info.value, real_node=self.node.parent)
                result = bool(IfAssertionCore(error_info, compare_key, compare_value).assertion())
            except Exception as e:
                traceback.print_exc()
                raise RuntimeError(ExceptionProcessObject(f"系统错误：断言对比出现错误：{e}"))
        elif error_info.error_mode == IfModeEnum.SCRIPT.value:
            try:
                script_code = error_info.script
                env = search_env(self.node)
                variable = AsyncExecutorVariable(self.node, can_set=False)
                context = ContextDocument(variable, self.node.node._print, env_name=env,
                                          dataset_toolkit=None, error_raise_func=error_raise)
                await self.script_notify()
                dynamic_code_executor = DynamicCodeExecutor().compile(code_str=script_code)
                await dynamic_code_executor.execute(context)
                print(f"error_info:{error_info.__dict__}")
                script_result = False
            except ErrorScriptRaiseObject as e:
                error_target = ErrorRaiseTarget(is_raise_exception=error_info.is_raise_exception,
                                                error_strategy=error_info.error_strategy, target=e.args[0])
                raise RuntimeError(
                    ExceptionProcessObject(f"命中错误：[{error_info.label}]自定义脚本异常：[{e.args[0]}]",
                                           raise_object=error_target, error_type=RaiseErrorTypeEnum.SCRIPT))
            except Exception as e:
                traceback.print_exc()
                raise RuntimeError(ExceptionProcessObject(f"系统错误：执行脚本出现错误：{e}"))
        self.node.node.status = NodeStatusEnum.RUNNING
        if result:
            error_target = ErrorRaiseTarget(is_raise_exception=error_info.is_raise_exception,
                                            error_strategy=error_info.error_strategy,
                                            target=RaiseErrorTypeEnum.FAST.value)
            raise RuntimeError(ExceptionProcessObject(f"抛出错误：[{error_info.label}]快速断言:命中断言，抛出异常",
                                                      error_type=RaiseErrorTypeEnum.FAST, raise_object=error_target))
        elif not script_result:
            self.node.node.send_step(
                ErrorWarningProcessObject(f"异常提示：[{error_info.label}]自定义脚本：未被命中，程序继续"))
        else:
            self.node.node.send_step(
                ErrorWarningProcessObject(f"异常提示：[{error_info.label}]快速断言：未被命中，程序继续"))


class ErrorScriptRaiseObject(Exception):

    def __init__(self, message, source, **kwargs):
        self.message = message
        self.source = source
        for key, value in kwargs.items():
            setattr(self, key, value)


def error_raise(name, **kwargs):
    raise ErrorScriptRaiseObject(name, 'error_raise', **kwargs)
