import copy
from collections import deque
from typing import List

from core.controller.async_task_runner import TaskRunner
from core.executor.core import RunnerExecutor
from core.payload.child_case_exec import RunChildCaseExecutor
from core.payload.utils.tools import run_loop_strategy, StaticPathIndex, PositionItem
from core.record.child_record.summary import SummaryRecord
from core.task_object.case_list import Case
from core.task_object.child_case_list import ChildCaseList, ChildCase
from core.task_object.galobal_mapping import MultiwayTreeNode
from core.task_object.generate_object import GlobalOption


class RunCaseExecutor(RunnerExecutor):

    def __init__(self, case_info: Case, global_option: GlobalOption, child_case_list: List[ChildCase],
                 task_runner: TaskRunner, dynamic_mapping, parent_node_index, record, spi):
        super().__init__(case_info, global_option, task_runner, dynamic_mapping, record, spi)
        self.child_case_list = child_case_list
        self.parent_node_index = parent_node_index

    async def before_callback(self, *args, **kwargs):
        await SummaryRecord(self.record).push_message([f"开始执行用例:[{self.metadata.name}]"])
        index = f"{self.parent_node_index}_{self.metadata.index}"

        def get_statis_path(child_case):
            static = StaticPathIndex(record_index=self.spi.record_index,
                                     task=self.spi.task, case=self.spi.case,
                                     child_case=child_case.index_in_global_list,
                                     case_name=self.spi.case_name, case_index=self.spi.case_index)
            static.position_list = copy.deepcopy(self.spi.position_list)
            static.add_position(PositionItem(type='child_case', index=child_case.index_in_global_list,
                                             label=f"").to_dict())
            return static
        child_case_executors = deque([RunChildCaseExecutor(child_case, self.global_option,
                                                           self.global_option.step_mapping.mapping[str(self.metadata.index)],
                                                           self.task_runner, self.dynamic_mapping, index, self.record,
                                                           get_statis_path(child_case)) for
                                      child_case in self.child_case_list])
        case_node = MultiwayTreeNode(parent=self.dynamic_mapping[f"{self.parent_node_index}_task"], node=self,
                                     children=child_case_executors)
        self.dynamic_mapping[f"{index}_case"] = case_node
        return child_case_executors

    async def run(self, child_case_executors, *args, **kwargs):
        await run_loop_strategy(self.metadata, self.task_runner.context, child_case_executors)

    async def after_callback(self, result=None, *args, **kwargs):
        await SummaryRecord(self.record).push_message([f"用例:[{self.metadata.name}]，执行结束"])

    async def error_callback(self, e: None, *args, **kwargs):
        await SummaryRecord(self.record).push_message([f"用例:[{self.metadata.name}]，出现错误，执行结束"])

    async def skipped_callback(self, *args, **kwargs):
        pass
