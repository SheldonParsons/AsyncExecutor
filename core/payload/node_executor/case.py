from core.customer_script.base import AsyncExecutorVariable, ContextDocument
from core.customer_script.execute import DynamicCodeExecutor
from core.executor.core import Executor, StepExecutor
from core.payload.utils.tools import search_env, process_script_value
from core.record.utils import ExceptionProcessObject, CaseProcessObject
from core.task_object.galobal_mapping import MultiwayTreeNode
from core.task_object.step_mapping import Case, ChildStepCase


class CaseRunController(StepExecutor):

    def __init__(self, node: MultiwayTreeNode, in_case=False):
        super().__init__(node)
        self.in_case = in_case

    async def run(self, *args, **kwargs):
        pass

    async def make_child_node(self):
        case_info: Case = self.node.node.metadata
        drive_strategy = case_info.drive_strategy
        loop_data = None
        if drive_strategy == 'times':
            try:
                loop_data = int(case_info.times)
            except Exception as e:
                raise await self.throw(e, backup_desc='系统错误：通过固定次数获取用例驱动次数失败')
        elif drive_strategy == 'dataset':
            try:
                env = search_env(self.node)
                dataset_env_mapping: dict = self.node.node.global_option.global_cache.origin_dataset_mapping.get(
                    str(case_info.dataset), Executor.EmptyObject())
                if isinstance(dataset_env_mapping, Executor.EmptyObject):
                    raise await self.throw(None,
                                           backup_desc=f'系统错误：无法找到用例[{self.node.node.metadata.label}]对应数据集')
                else:
                    loop_data = dataset_env_mapping.get(env, Executor.EmptyObject())
                    if loop_data['depend'] == 0:
                        for env, data in dataset_env_mapping.items():
                            if data['is_default'] is True:
                                loop_data = data
                    loop_data = loop_data['data']
                    if isinstance(loop_data, Executor.EmptyObject):
                        raise await self.throw(None,
                                               backup_desc=f'系统错误：无法找到用例[{self.node.node.metadata.label}]对应环境中的数据集')
            except Exception as e:
                raise await self.throw(e, backup_desc='系统错误：用例通过数据集获取用例驱动次数失败')
        elif drive_strategy == 'script':
            try:
                script_code = case_info.load_loop_script
                env = search_env(self.node)
                variable = AsyncExecutorVariable(self.node)
                context = ContextDocument(variable, self.node.node._print, env_name=env)
                code_executor = DynamicCodeExecutor().compile(script_code)
                result = await code_executor.execute(context)
                loop_data = process_script_value(result)
            except Exception as e:
                raise await self.throw(e, backup_desc='系统错误：通过自定义脚本获取用例驱动次数失败')
        data_source = [{} for _ in range(loop_data)] if isinstance(loop_data, int) else loop_data
        DRIVE_STRATEGY_DESC = {
            'times': '固定次数',
            'dataset': '数据集',
            'script': '自定义脚本'
        }.get(drive_strategy)
        case_drive_desc = f"用例[{self.node.node.metadata.label}]通过 {DRIVE_STRATEGY_DESC} 驱动步骤，驱动次数:{len(data_source)}"
        await self.send_step(CaseProcessObject(desc=case_drive_desc))
        child_status, parent = self.get_case_or_multitasker_child_status_and_parent(case_info)
        for index, data in enumerate(data_source):
            yield ChildStepCase(id=index,
                                check=case_info.check,
                                label='步骤子用例',
                                is_raise_step=True,
                                is_root_step=False,
                                status=child_status,
                                parent=parent,
                                project_id=case_info.project_id,
                                project_name=case_info.project_name,
                                error_strategy='raise',
                                temp_variables=data,
                                children=case_info.children)
