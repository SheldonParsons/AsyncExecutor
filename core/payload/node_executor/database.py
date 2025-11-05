import traceback
from types import SimpleNamespace

from jsonpath_ng import parse

from core.customer_script.base import AsyncExecutorVariable, ContextDocument
from core.customer_script.execute import DynamicCodeExecutor
from core.executor.core import StepExecutor
from core.payload.utils.tools import search_env
from core.record.utils import ExceptionProcessObject, DatabaseExceptionProcessObject
from core.task_object.database_client import DatabaseController
from core.task_object.galobal_mapping import MultiwayTreeNode
from core.task_object.step_mapping import Database


class DatabaseRunController(StepExecutor):

    def __init__(self, node: MultiwayTreeNode, in_case=False):
        super().__init__(node)
        self.in_case = in_case

    async def run(self, *args, **kwargs):
        database_info: Database = self.node.node.metadata
        # 获取数据库信息
        env = search_env(self.node)
        try:
            database_env_mapping = self.node.node.global_option.global_cache.origin_database_mapping.get(
                str(database_info.database_id))
            target_config = database_env_mapping.get(env).get('config')
            database_type = database_env_mapping.get('$_ast_database_type')
            if target_config.get('source') == 0:
                target_config = self.get_default_config(database_env_mapping)
                if not target_config:
                    raise RuntimeError(ExceptionProcessObject(desc="系统错误：获取数据库配置信息错误"))
        except Exception as e:
            raise await self.throw(e, backup_desc="系统错误：获取数据库配置信息错误")
        sql = None
        try:
            sql = self.replace(database_info.sql)
            database_controller: DatabaseController = self.node.node.global_option.database_controller
            result = await database_controller.get_result(database_type=database_type, sql=sql,
                                                          **target_config)
        except Exception as e:
            raise await self.throw(e, backup_desc=f"系统错误：执行sql异常：SQL:{sql}")

        try:
            if database_info.params_mode == 'kv':
                params = database_info.params
                variable = AsyncExecutorVariable(self.node)
                for param in params:
                    info = SimpleNamespace(**param)
                    name = info.name
                    range = info.range
                    expr = self.replace(info.pattern)
                    value = self.get_result_by_jsonpath(result, expr)
                    if range == 'temp':
                        variable.temp.set(name, value)
                    elif range == 'env':
                        variable.env.set(name, value)
                    elif range == 'global':
                        variable.gv.set(name, value)
            elif database_info.params_mode == 'script':
                try:
                    script_code = database_info.script
                    variable = AsyncExecutorVariable(self.node)
                    context = ContextDocument(variable, self.node.node._print, env_name=env, dataset_toolkit=None,
                                              database_result=result)
                    await self.script_notify()
                    dynamic_code_executor = DynamicCodeExecutor().compile(code_str=script_code)
                    await dynamic_code_executor.execute(context)
                except Exception as e:
                    traceback.print_exc()
                    raise RuntimeError(ExceptionProcessObject(f"系统错误：执行脚本出现错误：{e}"))
        except Exception as e:
            raise await self.throw(e, backup_desc=f"系统错误：提取变量异常")

    @classmethod
    def get_result_by_jsonpath(cls, result: list, expr: str):
        expr = parse(expr)
        matches = expr.find(result)
        if matches:
            if matches[0].value is True:
                compare_key = 'true'
            elif matches[0].value is False:
                compare_key = 'false'
            else:
                compare_key = matches[0].value
            return compare_key
        else:
            raise RuntimeError(DatabaseExceptionProcessObject(desc="数据库设置参数错误：jsonpath没有找到对应的值"))

    @classmethod
    def get_default_config(cls, database_env_mapping):
        for env_info in database_env_mapping.values():
            if isinstance(env_info, dict):
                if env_info.get('is_default') == 1:
                    return env_info.get('config')
        return None
