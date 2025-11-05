import os
from collections import deque
from typing import Union, Dict

from core.controller.async_task_runner import TaskRunner
from core.executor.core import Executor
from core.payload.task_exec import RunTaskExecutor
from core.payload.utils.tools import StaticPathIndex, PositionItem
from core.record.task_record import TaskRecord
from core.task_object.case_list import CaseList
from core.task_object.galobal_mapping import MultiwayTreeNode
from core.task_object.generate_object import GlobalOption


class PayloadExecutor(Executor):

    def __init__(self, global_option: GlobalOption, task_record: TaskRecord, index: str = "01"):
        self.global_option = global_option
        self.record = task_record
        self.task_runner: Union[TaskRunner, None] = None
        self.dynamic_mapping: Dict[str, MultiwayTreeNode] = {}
        self.index = index

    async def run(self):
        self.task_runner = TaskRunner(int(os.getenv("MAX_CONCURRENCY")))
        await self.task_runner.run(self._run())

    async def _run(self):
        await self.record.cache_info()
        # 获取所有用例
        print("PayloadExecutor...")
        print("用例列表")
        print(self.global_option.case_list.to_dict())
        print("子用例列表")
        print(self.global_option.child_case_list.to_dict())
        print("步骤mapping")
        print(self.global_option.step_mapping.to_dict())
        print("全局缓存对象")
        print(self.global_option.global_cache.to_dict())
        await self.run_task(self.global_option.case_list)

    async def run_task(self, case_list: CaseList):
        spi = StaticPathIndex(record_index=self.record.redis_index, task=1)
        spi.add_position(PositionItem(type='task', index=1, label="").to_dict())
        task_executor = RunTaskExecutor(self.global_option.task_info, self.global_option, case_list, self.task_runner,
                                        self.dynamic_mapping, self.record, spi)
        await self.task_runner.context.run_sequentially(deque([task_executor]))
        print(f"self.dynamic_mapping:{self.dynamic_mapping}")
        # await self.record.close()
