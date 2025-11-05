from core.customer_script.base import AsyncExecutorVariable, ContextDocument
from core.customer_script.execute import DynamicCodeExecutor
from core.executor.core import Executor, StepExecutor
from core.payload.utils.tools import search_env, process_script_value
from core.record.utils import MultitaskerProcessObject
from core.task_object.galobal_mapping import MultiwayTreeNode
from core.task_object.step_mapping import Multitasker, ChildMultitasker


class MultitaskerRunController(StepExecutor):

    def __init__(self, node: MultiwayTreeNode, in_case=False):
        super().__init__(node)
        self.in_case = in_case

    async def run(self, *args, **kwargs):
        pass

    async def make_child_node(self):
        multitasker_info: Multitasker = self.node.node.metadata
        drive_strategy = multitasker_info.drive_strategy
        loop_data = None
        if drive_strategy == 'times':
            try:
                loop_data = int(multitasker_info.times)
            except Exception as e:
                raise await self.throw(e, backup_desc='系统错误：通过固定次数获取多任务执行器驱动次数失败')
        elif drive_strategy == 'dataset':
            try:
                env = search_env(self.node)
                dataset_env_mapping: dict = self.node.node.global_option.global_cache.origin_dataset_mapping.get(
                    str(multitasker_info.dataset), Executor.EmptyObject())
                if isinstance(dataset_env_mapping, Executor.EmptyObject):
                    raise await self.throw(None,
                                           backup_desc=f'系统错误：无法找到多任务执行器[{self.node.node.metadata.label}]对应数据集')
                else:
                    loop_data = dataset_env_mapping.get(env, Executor.EmptyObject())
                    if isinstance(loop_data, Executor.EmptyObject):
                        raise await self.throw(None,
                                               backup_desc=f'系统错误：无法找到多任务执行器[{self.node.node.metadata.label}]对应环境中的数据集')
            except Exception as e:
                raise await self.throw(e, backup_desc='系统错误：多任务执行器通过数据集获取多任务执行器驱动次数失败')
        elif drive_strategy == 'script':
            try:
                script_code = multitasker_info.load_loop_script
                env = search_env(self.node)
                variable = AsyncExecutorVariable(self.node, can_set=False)
                context = ContextDocument(variable, self.node.node._print, env_name=env)
                code_executor = DynamicCodeExecutor().compile(script_code)
                await self.script_notify()
                result = await code_executor.execute(context)
                loop_data = process_script_value(result)
            except Exception as e:
                raise await self.throw(e, backup_desc='系统错误：通过自定义脚本获取多任务执行器驱动次数失败')
        data_source = [{} for _ in range(loop_data)] if isinstance(loop_data, int) else loop_data
        DRIVE_STRATEGY_DESC = {
            'times': '固定次数',
            'dataset': '数据集',
            'script': '自定义脚本'
        }.get(drive_strategy)
        multitasker_drive_desc = f"多任务执行器[{self.node.node.metadata.label}]通过 {DRIVE_STRATEGY_DESC} 驱动步骤，驱动次数:{len(data_source)}"
        await self.send_step(MultitaskerProcessObject(desc=multitasker_drive_desc))
        child_status, parent = self.get_case_or_multitasker_child_status_and_parent(multitasker_info)
        check = 'none' if multitasker_info.check == 'none' else 'check'
        for index, data in enumerate(data_source):
            yield ChildMultitasker(id=index,
                                   is_raise_step=True,
                                   is_root_step=False,
                                   label='子多任务执行器',
                                   error_strategy='raise',
                                   check=check,
                                   status=child_status,
                                   parent=parent,
                                   children=multitasker_info.children,
                                   temp_variables=data)
