from __future__ import annotations
import asyncio
import json
from abc import ABC, abstractmethod
from typing import Any, List, Dict
from typing import TYPE_CHECKING

from core.enums.executor import RecordMessageTypeEnum, NodeStatusEnum, NodeResultEnum
from core.payload.utils.tools import StaticPathIndex
from core.payload.variables_controller.variable import VariableToller
from core.record.task_record import TaskRecord
from core.record.utils import ScriptPrintProcessObject, ActionSleepProcessObject, \
    ActionWarningProcessObject, JsonDetail, ProcessObject, ExceptionObject, ExceptionProcessObject, \
    ActionScriptProcessObject, ActionExtractProcessObject
from core.task_object.case_list import Case
from core.task_object.child_case_list import ChildCase
from core.task_object.generate_object import GlobalOption
from core.task_object.task_info import TaskInfo

if TYPE_CHECKING:
    from core.task_object.galobal_mapping import MultiwayTreeNode
    from core.controller.async_task_runner import TaskRunner
from core.utils.py_variable_parser import ChangeModeEnum, ExchangeToller


class Executor(ABC):
    class EmptyObject:
        pass

    @abstractmethod
    def run(self, *args, **kwargs):
        pass


def position_to_str(position_list: List):
    s = ""
    for position_item in position_list:
        position_type = position_item["type"]
        if position_type == 'task':
            s += "任务/"
        elif position_type == 'case':
            s += f"{position_item['label']}/"
        elif position_type in ['child_case', 'child_step_case']:
            s += f'子用例{position_item['index'] + 1}/'
        elif position_type == 'child_multitasker':
            s += f'子任务执行器{position_item["index"] + 1}/'
        else:
            s += f"{position_item['label']}/"
    return s


class StepExecutor(Executor):

    def __init__(self, node: MultiwayTreeNode):
        self.node: MultiwayTreeNode = node

    @abstractmethod
    def run(self, *args, **kwargs):
        pass

    async def send_step(self, process: ProcessObject):
        process.set_position_list(self.node.node.spi.position_list)
        await self.node.node.add_step(process.to_json())

    async def send_system_notice_step(self, s: str):
        await self.send_step(ProcessObject(desc=s))

    async def sleep_notify(self, sleep_time):
        step_label = self.node.node.metadata.label
        await self.send_step(ActionSleepProcessObject(f"步骤：[{step_label}]，开始等待,{sleep_time} 毫秒..."))

    async def script_notify(self):
        step_label = self.node.node.metadata.label
        await self.send_step(ActionScriptProcessObject(f"步骤：[{step_label}]，开始执行自定义脚本..."))

    async def extract_notify(self, extract_info: dict):
        step_label = self.node.node.metadata.label
        data = {
            "step_label": step_label,
            "extract_info": json.dumps(extract_info),
        }
        await self.send_step(ActionExtractProcessObject(data))

    async def warning_notify(self, desc):
        await self.send_step(ActionWarningProcessObject(desc=desc))

    async def throw(self, e, backup_desc="", backup_class=ExceptionProcessObject, other_info=None):
        if e and len(e.args) > 0 and isinstance(e.args[0], ProcessObject):
            exception_object: ExceptionObject = e.args[0]
            exception_object.set_other_info(other_info)
        else:
            exception_object = backup_class(f"{backup_desc}{':' + str(e) if e else ''}")
            exception_object.set_other_info(other_info)
        raise RuntimeError(exception_object)

    async def unknown_throw(self, e, backup_desc="", backup_class=ExceptionProcessObject):
        if e and len(e.args) > 0 and isinstance(e.args[0], ProcessObject):
            pass
        else:
            exception_object = backup_class(f"{backup_desc}{':' + str(e) if e else ''}")
            await self.send_step(exception_object)
            raise RuntimeError(exception_object)

    @classmethod
    def get_case_or_multitasker_child_status_and_parent(cls, step_info):
        status = 'pending'
        if step_info.check == 'none':
            status = 'skipped'
        parent = step_info.parent.replace("_step", f"_{step_info.id}_step")
        return status, parent

    def replace(self, value):
        variable_mapping = VariableToller.get_variable_mapping(self.node)
        return ExchangeToller(value, variable_mapping, ChangeModeEnum.CHANGE_EVERY_TIME).replace()


class RunnerExecutor:

    def __init__(self, metadata: Any, global_option, task_runner, dynamic_mapping, record, spi):
        self.metadata: Any = metadata
        self.global_option: GlobalOption = global_option
        self.task_runner: TaskRunner = task_runner
        self.dynamic_mapping: Dict[str, MultiwayTreeNode] = dynamic_mapping
        self.record: TaskRecord = record
        self.spi: StaticPathIndex = spi
        self.status: NodeStatusEnum = NodeStatusEnum.PENDING
        self.start = 0
        self.end = 0
        self.result: NodeResultEnum = NodeResultEnum.UNKNOWN
        self.is_end_before_run = False
        self.has_child_error = False
        self.has_child_skipped = False
        self.redis_semaphore = asyncio.Semaphore(100)

    def check_and_change_status(self, current_node: MultiwayTreeNode, check_self=True):
        # 这个状态目前只会用于父级、超父级的状态判断
        skipped_status_tuple = (NodeStatusEnum.SKIPPED, NodeStatusEnum.CONDITIONAL, NodeStatusEnum.ERROR)
        if not isinstance(current_node.node.metadata, TaskInfo):
            # 检查上级点状态
            if current_node.parent.node.status in skipped_status_tuple:
                self.status = NodeStatusEnum.SKIPPED
                return
        # 检查当前节点check变量值
        if check_self and self.metadata.check == 'none':
            self.status = NodeStatusEnum.SKIPPED
            return
        if not isinstance(current_node.node.metadata, TaskInfo):
            # 检查任务状态
            task_index = f"{self.spi.task}_task"
            task_node: MultiwayTreeNode = self.dynamic_mapping.get(task_index)
            if task_node.node.status in skipped_status_tuple:
                self.status = NodeStatusEnum.SKIPPED
                return
        if not isinstance(current_node.node.metadata, (Case, TaskInfo)):
            # 检查用例状态
            case_index = f"{self.spi.task}_{self.spi.case_index}_case"
            case_node: MultiwayTreeNode = self.dynamic_mapping.get(case_index)
            if case_node.node.status in skipped_status_tuple:
                self.status = NodeStatusEnum.SKIPPED
                return
        if not isinstance(current_node.node.metadata, (ChildCase, Case, TaskInfo)):
            # 检查子用例状态
            child_case_index = f"{self.spi.task}_{self.spi.case_index}_{self.spi.child_case}_child_case"
            child_case_node: MultiwayTreeNode = self.dynamic_mapping.get(child_case_index)
            if child_case_node.node.status in skipped_status_tuple:
                self.status = NodeStatusEnum.SKIPPED
                return

    @abstractmethod
    def run(self, *args, **kwargs):
        pass

    @abstractmethod
    async def before_callback(self, *args, **kwargs) -> bool:
        pass

    @abstractmethod
    async def after_callback(self, result=None, *args, **kwargs):
        pass

    @abstractmethod
    async def error_callback(self, e: Exception, *args, **kwargs):
        pass

    @abstractmethod
    async def skipped_callback(self, *args, **kwargs) -> bool:
        pass

    def _print(self, *args, sep=' ', end='\n'):
        _args = [str(item) if not isinstance(item, str) else item for item in args]
        process = ScriptPrintProcessObject(sep.join(_args))
        process.set_position_list(self.spi.position_list)

        async def _inner_print(data):
            async with self.redis_semaphore:
                await self.add_step_or_update(data)

        print_content = process.to_json()
        self.run_concurrently(_inner_print(print_content))

    @classmethod
    def run_concurrently_waiting(cls, task) -> Any:
        async def _runner():
            return await asyncio.gather(task)

        result_list = asyncio.run(_runner())

        return result_list[0]

    @classmethod
    def run_concurrently(cls, task):
        """并发地启动一组任务"""
        task_group = []
        task_obj = asyncio.create_task(task)
        task_group.append(task_obj)

        async def wait_group():
            return await asyncio.gather(*task_group)

        return asyncio.create_task(wait_group())

    def step_key(self, t: RecordMessageTypeEnum = RecordMessageTypeEnum.STATUS):
        main_key = self.record.redis_index
        return f"{main_key}:step_record:case:{self.spi.case}:child_case:{self.spi.child_case}:step:{self.spi.step}:{t.value}"

    def step_parent_key(self, t: RecordMessageTypeEnum = RecordMessageTypeEnum.STATUS):
        if self.spi.parent_step is None:
            return None
        main_key = self.record.redis_index
        return f"{main_key}:step_record:case:{self.spi.case}:child_case:{self.spi.child_case}:step:{self.spi.parent_step}:{t.value}"

    def child_case_key(self, t: RecordMessageTypeEnum = RecordMessageTypeEnum.PROCESS):
        main_key = self.record.redis_index
        return f"{main_key}:child_case_record:{self.spi.child_case}:{t.value}"

    def global_child_case_list(self):
        main_key = self.record.redis_index
        return f"{main_key}:child_case_record:child_case_list"

    def record_info_key(self):
        main_key = self.record.redis_index
        return f"{main_key}:record_info"

    def task_info_key(self):
        main_key = self.record.redis_index
        return f"{main_key}:task_info"

    def summary_key(self):
        main_key = self.record.redis_index
        return f"{main_key}:summary_record:process"

    async def update_step(self, **kwargs):
        key = self.step_key()
        await self.record.update_params(key, **kwargs)

    async def update_fields_to_list(self, index, **kwargs):
        key = self.global_child_case_list()
        await self.record.update_fields_to_list(key, *[index], **kwargs)

    async def update_parent_step(self, **kwargs):
        key = self.step_parent_key()
        if key:
            await self.record.update_params(key, **kwargs)

    async def batch_add_detail(self, data: JsonDetail):
        add_cache_mapping = {}
        for info_key, info_value in data.data.items():
            key = self.step_detail_key(f"{data.type}_detail", data.index, info_key)
            add_cache_mapping[key] = info_value
        await self.record.redis.batch_set_value(add_cache_mapping)

    def step_detail_key(self, type_key, prefix_key, info_key):
        main_key = self.record.redis_index
        return f"{main_key}:{type_key}:{prefix_key}:{info_key}"

    def send_step(self, *process: ProcessObject):
        send_list = []
        for item in process:
            item.set_position_list(self.spi.position_list)
            send_list.append(item.to_json())
        self.run_concurrently(self.add_step(*send_list))

    async def set_child_case_step_status(self, **kwargs):
        key = self.child_case_key(RecordMessageTypeEnum.STATUS)
        await self.record.update_params(key, **kwargs)

    def send_parent_step(self, *process: ProcessObject):
        send_list = []
        for item in process:
            item.set_position_list(self.spi.position_list)
            send_list.append(item.to_json())
        self.run_concurrently(self.add_parent_step(*send_list))

    def send_child_case(self, *process: ProcessObject):
        send_list = []
        for item in process:
            item.set_position_list(self.spi.position_list)
            send_list.append(item.to_json())
        self.run_concurrently(self.add_child_case(*send_list))

    def send_summary(self, *process: ProcessObject):
        send_list = []
        for item in process:
            item.set_position_list(self.spi.position_list)
            send_list.append(item.to_json())
        self.run_concurrently(self.add_summary(*send_list))

    async def add_step(self, *args):
        key = self.step_key(RecordMessageTypeEnum.PROCESS)
        await self.record.batch_push_to_key(key, *args)

    async def add_step_or_update(self, *args):
        key = self.step_key(RecordMessageTypeEnum.PROCESS)
        await self.record.batch_push_or_update_to_key(key, *args)

    async def add_parent_step(self, *args):
        key = self.step_parent_key(RecordMessageTypeEnum.PROCESS)
        if key:
            await self.record.batch_push_to_key(key, *args)

    async def add_child_case(self, *args):
        key = self.child_case_key()
        await self.record.batch_push_to_key(key, *args)

    async def add_summary(self, *args):
        key = self.summary_key()
        await self.record.batch_push_to_key(key, *args)

    async def get_value(self, key):
        return await self.record.get_value(key)
