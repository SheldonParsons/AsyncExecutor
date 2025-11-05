from __future__ import annotations
from typing import Callable, Awaitable, Any, TYPE_CHECKING

from core.enums.executor import NodeStatusEnum, StepTypeEnum
from core.utils.tools import SkippedStepResult

if TYPE_CHECKING:
    from core.payload.step_exec import RunStepExecutor
from core.record.utils import StepSkippedProcessObject, StepRunningProcessObject, CoreExecReturn
from core.task_object.step_mapping import NormalStep


class StepExecRunner:

    def __init__(self, step_exec: RunStepExecutor, run_callback: Callable[[], Awaitable[Any]]):
        self.is_send_self_step = True
        self.is_send_parent_step = True
        self.is_send_child_case = True
        self.is_send_summary = True
        self.is_run_core_exec = True
        self.is_skipped = False
        self.is_in_case = step_exec.in_case
        self.step_metadata: NormalStep = step_exec.metadata
        self.step_exec: RunStepExecutor = step_exec
        self.run_callback: Callable[[], Awaitable[Any]] = run_callback

    async def run(self):
        self.is_skipped = self.step_exec.status == NodeStatusEnum.SKIPPED
        self.is_run_core_exec = not self.is_skipped
        if self.is_in_case:
            return await self.exec_in_case()
        else:
            return await self.exec_not_in_case()

    async def exec_in_case(self):
        self.is_send_parent_step = False
        self.is_send_child_case = False
        self.is_send_summary = False
        result = await self.core_runner()
        return await self.process_core_exec_return(result)

    async def exec_not_in_case(self):
        if self.step_metadata.type in (StepTypeEnum.CHILD_MULTITASKER, StepTypeEnum.EMPTY):
            self.is_send_self_step = False
        if self.step_metadata.type in StepTypeEnum.EMPTY:
            self.is_send_parent_step = False
            self.is_send_child_case = False
            self.is_send_summary = False
            self.is_run_core_exec = False
        if self.step_metadata.type in (StepTypeEnum.INTERFACE, StepTypeEnum.ASSERTION) and not self.is_skipped:
            self.is_send_parent_step = False
            self.is_send_child_case = False
            self.is_send_summary = False
        result = await self.core_runner()
        return await self.process_core_exec_return(result)

    async def process_core_exec_return(self, result):
        if isinstance(result, CoreExecReturn):
            await self.process_other_record(result)
            return result.result
        return result

    async def process_other_record(self, core_exec_return: CoreExecReturn):
        self.step_exec.send_parent_step(*core_exec_return.parent_process_list)
        self.step_exec.send_child_case(*core_exec_return.child_case_process_list)
        self.step_exec.send_summary(*core_exec_return.summary_process_list)

    async def core_runner(self):
        process_object = await self.get_base_process()
        if self.is_send_self_step:
            self.step_exec.send_step(process_object)
        if self.is_send_parent_step:
            self.step_exec.send_parent_step(process_object)
        if self.is_send_child_case:
            self.step_exec.send_child_case(process_object)
        if self.is_send_summary:
            self.step_exec.send_summary(process_object)
        if self.is_run_core_exec:
            result = await self.run_callback()
        else:
            result = SkippedStepResult()
        return result

    async def get_base_process(self):
        if self.is_skipped:
            return StepSkippedProcessObject(desc=f"[{self.step_exec.spi.step_name}]步骤已跳过")
        else:
            self.step_exec.status = NodeStatusEnum.RUNNING
            await self.step_exec.update_step_status()
            return StepRunningProcessObject(desc=f"[{self.step_exec.spi.step_name}]步骤开始运行")


class StepRecordRunner:

    def __init__(self, step_exec: RunStepExecutor, run_callback: Callable[[], Awaitable[Any]]):
        self.step_exec = step_exec
        self.run_callback = run_callback

    async def run(self):
        return await StepExecRunner(self.step_exec, self.run_callback).run()
