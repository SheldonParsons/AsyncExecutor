import traceback

from core.ast_file.core import AstFile
from core.customer_script.base import AsyncExecutorVariable, ContextDocument
from core.customer_script.execute import DynamicCodeExecutor
from core.excel_controller.core import AsyncExcel
from core.executor.core import StepExecutor
from core.payload.utils.tools import search_env
from core.record.utils import ExceptionProcessObject
from core.task_object.galobal_mapping import MultiwayTreeNode
from core.task_object.step_mapping import Script


class ScriptRunController(StepExecutor):

    def __init__(self, node: MultiwayTreeNode, in_case=False):
        super().__init__(node)
        self.in_case = in_case

    async def run(self, *args, **kwargs):
        script_info: Script = self.node.node.metadata
        try:
            env = search_env(self.node)
            script_code = script_info.script

            variable = AsyncExecutorVariable(self.node)

            def get_ast_file():
                return AstFile(self.node.node.global_option)

            def get_ast_excel():
                return AsyncExcel(self.node.node.global_option)

            context = ContextDocument(variable, self.node.node._print, env_name=env, dataset_toolkit=None,
                                      ast_file_callback=get_ast_file, ast_excel_callback=get_ast_excel)
            await self.script_notify()
            dynamic_code_executor = DynamicCodeExecutor().compile(code_str=script_code)
            await dynamic_code_executor.execute(context)
        except Exception as e:
            traceback.print_exc()
            raise RuntimeError(ExceptionProcessObject(f"系统错误：执行脚本出现错误：{e}"))
