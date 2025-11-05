import copy
import json
from collections import deque, defaultdict
from typing import List, Any, Dict

from core.controller.async_task_runner import TaskRunner
from core.enums.executor import StatusEnum
from core.executor.core import RunnerExecutor
from core.payload.case_exec import RunCaseExecutor
from core.payload.utils.tools import run_loop_strategy, get_current_ms, StaticPathIndex, PositionItem
from core.record.child_record.record import RecordInfoRecord
from core.record.child_record.summary import SummaryRecord
from core.record.child_record.task import TaskInfoRecord
from core.task_object.case_list import CaseList,Case
from core.task_object.child_case_list import ChildCase
from core.task_object.galobal_mapping import MultiwayTreeNode
from core.task_object.generate_object import GlobalOption
from core.task_object.task_info import TaskInfo


class RunTaskExecutor(RunnerExecutor):

    def __init__(self, task_info: TaskInfo, global_option: GlobalOption, case_list: CaseList,
                 task_runner: TaskRunner, dynamic_mapping, record, spi):
        super().__init__(task_info, global_option, task_runner, dynamic_mapping, record, spi)
        self.case_list = case_list

    async def before_callback(self, *args, **kwargs):
        await SummaryRecord(self.record).push_message(["任务开始"])
        return True

    async def run(self, *args, **kwargs):
        index = "1"

        def get_statis_path(case):
            static = StaticPathIndex(record_index=self.spi.record_index, task=self.spi.task, case=case.id,
                                     case_name=case.name, case_index=case.index)
            static.position_list = copy.deepcopy(self.spi.position_list)
            static.add_position(PositionItem(type='case', index=case.id, label=case.name).to_dict())
            return static

        child_case_list_mapping = self.mapping_child_case_list(self.global_option.child_case_list.list)
        case_executors = deque([
            RunCaseExecutor(case, self.global_option, child_case_list_mapping.get(case.id), self.task_runner,
                            self.dynamic_mapping, index, self.record,
                            get_statis_path(case)) for
            case
            in self.case_list.data])
        task_node = MultiwayTreeNode(parent=None, node=self, children=case_executors)
        self.dynamic_mapping[f"{index}_task"] = task_node
        await run_loop_strategy(self.metadata, self.task_runner.context, case_executors)

    async def after_callback(self, result=None, *args, **kwargs):
        await SummaryRecord(self.record).push_message(["任务结束"])
        await TaskInfoRecord(self.record).change_info(status=StatusEnum.END.value)
        await RecordInfoRecord(self.record).change_info(status=StatusEnum.END.value, end_at=get_current_ms())

    async def error_callback(self, e: None, *args, **kwargs):
        await SummaryRecord(self.record).push_message(["任务错误结束"])
        await TaskInfoRecord(self.record).change_info(status=StatusEnum.ERROR_END.value, error_info=str(e))
        await RecordInfoRecord(self.record).change_info(status=StatusEnum.ERROR_END.value, end_at=get_current_ms())

    async def skipped_callback(self, *args, **kwargs):
        pass

    @classmethod
    def mapping_child_case_list(cls,
                                  data_list: List[ChildCase]
                                  ) -> Dict[int, List[Any]]:
        result = defaultdict(list)
        for item in data_list:
            result[item.case_id].append(item)
        return result
