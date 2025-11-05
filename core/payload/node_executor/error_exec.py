import traceback

from core.customer_script.base import AsyncExecutorVariable, ContextDocument
from core.customer_script.execute import DynamicCodeExecutor
from core.enums.executor import IfModeEnum, NodeStatusEnum
from core.executor.core import StepExecutor
from core.payload.node_executor.if_exec import IfAssertionCore
from core.payload.utils.tools import search_env
from core.record.utils import ExceptionProcessObject, ErrorFailedProcessObject
from core.task_object.galobal_mapping import MultiwayTreeNode
from core.task_object.step_mapping import Error


class ErrorRunController(StepExecutor):

    def __init__(self, node: MultiwayTreeNode, in_case=False):
        super().__init__(node)
        self.in_case = in_case

    async def run(self, *args, **kwargs):
        error_info: Error = self.node.node.metadata
        result = False
        if error_info.error_mode == IfModeEnum.FAST.value:
            try:
                compare_key = self.replace(error_info.key)
                compare_value = self.replace(error_info.value)
                result = bool(IfAssertionCore(error_info, compare_key, compare_value).assertion())
            except Exception as e:
                raise RuntimeError(ExceptionProcessObject(f"系统错误：If对比出现错误：{e}"))
        elif error_info.error_mode == IfModeEnum.SCRIPT.value:
            try:
                script_code = error_info.script
                env = search_env(self.node)
                variable = AsyncExecutorVariable(self.node, can_set=False)
                context = ContextDocument(variable, self.node.node._print, env_name=env,
                                          dataset_toolkit=None, error_raise_func=error_raise)
                await self.script_notify()
                result = bool(await DynamicCodeExecutor().execute(context, compile_code=script_code))
            except ErrorScriptRaiseObject as e:
                raise RuntimeError(
                    ExceptionProcessObject(f"抛出错误：[{error_info.label}]，自定义脚本，成功", raise_object=e))
            except Exception as e:
                traceback.print_exc()
                raise RuntimeError(ExceptionProcessObject(f"系统错误：执行脚本出现错误：{e}"))
        self.node.node.status = NodeStatusEnum.RUNNING
        if result:
            raise RuntimeError(ExceptionProcessObject(f"抛出错误：[{error_info.label}]，快速断言，成功"))
        else:
            self.node.node.send_step(ErrorFailedProcessObject(f"抛出错误：[{error_info.label}]，失败，程序继续"))


class ErrorScriptRaiseObject(Exception):

    def __init__(self, message, source, **kwargs):
        self.message = message
        self.source = source
        for key, value in kwargs.items():
            setattr(self, key, value)


def error_raise(name, **kwargs):
    raise ErrorScriptRaiseObject(name, 'error_raise', **kwargs)
