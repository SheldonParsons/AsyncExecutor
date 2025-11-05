import copy
from collections import deque
from typing import Dict, Union, Tuple, List, Self

from core.controller.async_task_runner import TaskRunner
from core.enums.executor import NodeStatusEnum
from core.executor.core import RunnerExecutor
from core.payload.step_exec import RunStepExecutor
from core.payload.utils.tools import StaticPathIndex, PositionItem, get_current_ms
from core.record.child_record.record import RecordInfoRecord
from core.task_object.child_case_list import ChildCase
from core.task_object.galobal_mapping import MultiwayTreeNode
from core.task_object.generate_object import GlobalOption
from core.task_object.step_mapping import Interface, Script, Group, Database, Case, Multitasker, \
    Assertion, Empty, If


class RunChildCaseExecutor(RunnerExecutor):

    def __init__(self, child_case_info: ChildCase, global_option: GlobalOption, origin_step_mapping: Dict[
        str, Union[Interface, Script, Group, Database, Case, Multitasker, Assertion, Empty, If,]],
                 task_runner: TaskRunner, dynamic_mapping: dict, parent_node_index, record, spi):
        super().__init__(child_case_info, global_option, task_runner, dynamic_mapping, record, spi)
        self.origin_step_mapping = origin_step_mapping
        self.parent_node_index = parent_node_index

    async def before_callback(self, *args, **kwargs):
        self.start = get_current_ms()
        self.status = NodeStatusEnum.RUNNING
        await self.update_fields_to_list(self.metadata.index_in_global_list, start=self.start,
                                         status=self.status.value)
        index = f"{self.parent_node_index}_{self.metadata.index_in_global_list}"
        step_executors, case_node = await self.make_dynamic_node(index)
        self.dynamic_mapping[f"{index}_child_case"] = case_node
        self.check_and_change_status(case_node, check_self=False)
        return step_executors, case_node

    async def run(self, step_executors, case_node):
        await self.task_runner.context.run_sequentially(step_executors)

    async def after_callback(self, result=None, *args, **kwargs):
        if self.status == NodeStatusEnum.SKIPPED:
            pass
        elif self.has_child_error:
            self.status = NodeStatusEnum.ERROR_CHILD
        elif self.has_child_skipped:
            self.status = NodeStatusEnum.SKIPPED_CHILD
        else:
            self.status = NodeStatusEnum.END
        await RecordInfoRecord(self.record).increment_field(done_child_case_count=1)
        await self.end_child_case()

    async def skipped_callback(self, *args, **kwargs):
        self.status = NodeStatusEnum.SKIPPED
        await self.end_child_case()

    async def error_callback(self, e: None, *args, **kwargs):
        self.status = NodeStatusEnum.ERROR
        await self.end_child_case()

    async def end_child_case(self):
        self.end = get_current_ms()
        await self.update_fields_to_list(self.metadata.index_in_global_list, end=self.end, status=self.status.value)

    async def make_dynamic_node(self, index) -> Tuple[deque[Self], MultiwayTreeNode]:
        step_executors = deque([])
        for step_index in self.metadata.origin_child_steps:
            step_object = self.origin_step_mapping.get(step_index)
            spi = StaticPathIndex(record_index=self.spi.record_index, task=self.spi.task, case=self.spi.case,
                                  child_case=self.spi.child_case, step=step_object.id, case_name=self.spi.case_name,
                                  step_name=step_object.label, case_index=self.spi.case_index)
            spi.position_list = copy.deepcopy(self.spi.position_list)
            spi.add_position(PositionItem(type=step_object.type, index=step_object.id,
                                          label=step_object.label).to_dict())
            step_executor = RunStepExecutor(step_object, self.global_option, self.task_runner,
                                            self.dynamic_mapping, index, self.origin_step_mapping, self, self.record,
                                            step_index, spi)
            step_executors.append(step_executor)
        case_node = MultiwayTreeNode(parent=self.dynamic_mapping[f"{self.parent_node_index}_case"], node=self,
                                     children=step_executors)
        return step_executors, case_node
