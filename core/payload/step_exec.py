import copy
from collections import deque
from typing import Union, Self, Tuple, Dict, Callable, Any

from core.controller.async_task_runner import TaskRunner
from core.enums.executor import NodeStatusEnum, NodeResultEnum, StepTypeEnum
from core.executor.core import RunnerExecutor
from core.payload.node_executor.case import CaseRunController
from core.payload.node_executor.dispatch import ExecutorCaller
from core.payload.node_executor.multitasker import MultitaskerRunController
from core.payload.utils.error_strategy import ErrorStrategyController
from core.payload.utils.tools import run_loop_strategy, StaticPathIndex, PositionItem, get_current_ms
from core.record.child_record.step import StepRecordRunner
from core.record.utils import ExceptionProcessObject, ProcessObject
from core.task_object.galobal_mapping import MultiwayTreeNode
from core.task_object.generate_object import GlobalOption
from core.task_object.step_mapping import Case, Empty, RealNode


class RunStepExecutor(RunnerExecutor):

    def __init__(self, step: Any,
                 global_option: GlobalOption, task_runner: TaskRunner, dynamic_mapping: Dict[str, MultiwayTreeNode],
                 parent_node_index,
                 origin_step_mapping, parent, record, origin_step_index, spi, in_case=False):
        super().__init__(step, global_option, task_runner, dynamic_mapping, record, spi)
        self.child_steps = []
        self.parent_node_index = parent_node_index
        self.origin_step_mapping = origin_step_mapping
        self.origin_step_index = origin_step_index
        self.parent = parent
        self.in_case = in_case

    async def before_callback(self, *args, **kwargs):
        self.start = get_current_ms()
        await self.update_step(start=self.start)
        try:
            self.child_steps, current_node = await self.make_dynamic_node()
        except Exception as e:
            raise RuntimeError(ExceptionProcessObject(desc=f"系统错误：创建子步骤失败，子步骤将不会被执行:{e}"))
        else:
            print(f"\033[34m before_callback步骤：{self.metadata.type}：判断是否执行core：{self.metadata.label}\033[0m")
            print(f"{self.metadata.label}spi:{self.spi.to_dict()}")
            self.check_and_change_status(current_node)
            return current_node

    async def run(self, current_node: MultiwayTreeNode):
        core_exec = lambda: ExecutorCaller(self.metadata.type)(current_node, self.in_case).run()
        result = await StepRecordRunner(self, core_exec).run()
        await self.run_child(self.child_steps)
        return result

    async def after_callback(self, result=None, current_node: MultiwayTreeNode = None, *args, **kwargs):
        father_step: Union[None, MultiwayTreeNode] = self.search_step(current_node)
        self.status = NodeStatusEnum.END
        if self.has_child_error:
            self.result = NodeResultEnum.ERROR_CHILD
            if father_step:
                father_step.node.has_child_error = True
        elif self.has_child_skipped:
            self.result = NodeResultEnum.SKIPPED_CHILD
            if father_step:
                father_step.node.has_child_skipped = True
        else:
            self.result = NodeResultEnum.SUCCESS
        await self.update_fields_to_list(self.spi.child_case, done_step_count=1)
        await self.end_step()

    async def error_callback(self, e: Exception, current_node: MultiwayTreeNode = None, *args, **kwargs):
        self.status = NodeStatusEnum.ERROR
        self.result = NodeResultEnum.ERROR_SELF
        father_step: Union[None, MultiwayTreeNode] = self.search_step(current_node)
        if father_step:
            father_step.node.has_child_error = True
        await self.update_fields_to_list(self.spi.child_case, failed_step_count=1)
        await self.end_step()
        if e and len(e.args) > 0 and isinstance(e.args[0], ProcessObject):
            process_object = e.args[0]
        else:
            process_object = ExceptionProcessObject(f"系统错误：{e}")
        await self.send_all_record(process_object)
        # TODO: 需要特殊处理主动抛出错误的情况
        self.change_parent_status_on_error(current_node)

    @classmethod
    def change_parent_status_on_error(cls, current_node: MultiwayTreeNode):
        ErrorStrategyController(current_node).exec()

    async def send_all_record(self, process_object):
        # TODO:性能优化，一次通信写入
        if self.metadata.type not in (StepTypeEnum.CHILD_MULTITASKER, StepTypeEnum.EMPTY):
            self.send_step(process_object)
        if self.metadata.type not in StepTypeEnum.EMPTY:
            self.send_parent_step(process_object)
            self.send_child_case(process_object)
            self.send_summary(process_object)

    async def skipped_callback(self, result=None, current_node: MultiwayTreeNode = None, *args, **kwargs):
        self.status = NodeStatusEnum.SKIPPED
        self.result = NodeResultEnum.SKIPPED_SELF
        father_step: Union[None, MultiwayTreeNode] = self.search_step(current_node)
        if father_step:
            father_step.node.has_child_skipped = True
        await self.update_fields_to_list(self.spi.child_case, skipped_step_count=1)
        await self.end_step()

    async def end_step(self):
        self.end = get_current_ms()
        # TODO:性能优化，一次通信写入
        await self.update_step_status()
        if not self.in_case and isinstance(self.metadata, RealNode) and not isinstance(self.metadata, Empty):
            await self.update_step(end=self.end, status=self.status.value, result=self.result.value)

    async def update_step_status(self):
        if not self.in_case and isinstance(self.metadata, RealNode) and not isinstance(self.metadata, Empty):
            update_step = {
                str(self.metadata.id): {
                    "status": self.status.value,
                    "result": self.result.value
                }
            }
            await self.set_child_case_step_status(**update_step)

    def search_step(self, current_node: MultiwayTreeNode):
        if self.in_case:
            # 如果是case中的步骤，直接找到Case节点
            return self.search_node(current_node, lambda node: isinstance(node.node.metadata, Case))
        else:
            # 如果不是case中的步骤，找到最近的真实节点
            return self.search_node(current_node, lambda node: True)

    def search_node(self, current_node: MultiwayTreeNode,
                    judge_callback: Callable[[MultiwayTreeNode], bool]) -> Union[MultiwayTreeNode, None]:
        parent_node = current_node.parent
        if parent_node is None:
            return None
        if judge_callback(parent_node):
            return parent_node
        else:
            return self.search_node(parent_node, judge_callback)

    async def run_child(self, step_executors):
        if self.metadata.type in ['group', 'case', 'multitasker', 'if', 'child_multitasker', 'child_step_case']:
            if self.metadata.type in ['case', 'multitasker']:
                await run_loop_strategy(self.metadata, self.task_runner.context, step_executors)
            else:
                await self.task_runner.context.run_sequentially(step_executors)

    async def make_dynamic_node(self) -> Tuple[deque[Self], MultiwayTreeNode]:
        """
        动态MultiwayTreeNode对象，并为该对象添加子RunStepExecutor
        Returns: child_steps: deque[RunStepExecutor], step_node: MultiwayTreeNode
        """
        index = f"{self.parent_node_index}_{self.metadata.id}"
        parent_index_str = f"{self.parent_node_index}_child_case" if self.parent.metadata.type == 'child_case' else f"{self.parent_node_index}_step"
        step_node = MultiwayTreeNode(parent=self.dynamic_mapping[parent_index_str], node=self)
        child_steps = await self.make_child_executor(index, step_node)
        step_node.set_child(child_steps)
        self.dynamic_mapping[f"{index}_step"] = step_node
        return child_steps, step_node

    async def make_child_executor(self, index, step_node: MultiwayTreeNode = None) -> deque[Self]:
        step_executors = deque([])
        spi = None
        if self.in_case:
            spi = self.spi.copy()
        if self.metadata.type in ['group', 'child_step_case', 'if', 'child_multitasker']:
            if self.metadata.type in ['child_multitasker']:
                parent_step = self.spi.parent_step
                parent_step_name = self.spi.parent_step_name
            else:
                parent_step = self.metadata.id
                parent_step_name = self.metadata.label
            for step_index in self.metadata.children:
                step_object = self.origin_step_mapping.get(step_index)
                if spi:
                    _spi = self.spi.copy()
                else:
                    _spi = StaticPathIndex(record_index=self.spi.record_index, task=self.spi.task,
                                           case=self.spi.case,
                                           case_index=self.spi.case_index,
                                           case_name=self.spi.case_name,
                                           child_case=self.spi.child_case,
                                           step=step_object.id,
                                           step_name=step_object.label,
                                           parent_step=parent_step,
                                           parent_step_name=parent_step_name,
                                           position_list=copy.deepcopy(self.spi.position_list))
                _spi.add_position(
                    PositionItem(type=step_object.type, index=step_object.id, label=step_object.label).to_dict())
                step_executor = RunStepExecutor(step_object, self.global_option, self.task_runner,
                                                self.dynamic_mapping, index, self.origin_step_mapping, self,
                                                self.record, step_index, _spi, in_case=self.in_case)
                step_executors.append(step_executor)
        elif self.metadata.type == 'multitasker':
            async for step_object in MultitaskerRunController(step_node).make_child_node():
                if spi:
                    _spi = self.spi.copy()
                else:
                    _spi = StaticPathIndex(record_index=self.spi.record_index, task=self.spi.task,
                                           case=self.spi.case,
                                           case_index=self.spi.case_index,
                                           child_case=self.spi.child_case,
                                           step=step_object.id,
                                           step_name=step_object.label,
                                           parent_step=self.metadata.id,
                                           parent_step_name=self.metadata.label,
                                           position_list=copy.deepcopy(self.spi.position_list))
                _spi.add_position(PositionItem(type=step_object.type, index=step_object.id, label=f"").to_dict())
                step_executor = RunStepExecutor(step_object, self.global_option, self.task_runner,
                                                self.dynamic_mapping, index, self.origin_step_mapping, self,
                                                self.record, self.origin_step_index, _spi, in_case=self.in_case)
                step_executors.append(step_executor)
        elif self.metadata.type == 'case':
            async for step_object in CaseRunController(step_node).make_child_node():
                _spi = self.spi.copy()
                _spi.add_position(PositionItem(type=step_object.type, index=step_object.id, label=f"").to_dict())
                step_executor = RunStepExecutor(step_object, self.global_option, self.task_runner,
                                                self.dynamic_mapping, index, self.origin_step_mapping, self,
                                                self.record, self.origin_step_index, _spi, in_case=True)
                step_executors.append(step_executor)
        return step_executors
