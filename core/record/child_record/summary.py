from typing import List, Union

from core.record.child_record.core import RecordController
from core.record.task_record import TaskRecord
from core.record.utils import ProcessObject


class SummaryRecord(RecordController):

    def __init__(self, task_record: TaskRecord):
        super().__init__(task_record)

    async def push_message(self, process_list: List[Union[ProcessObject, str]]):
        await self.get_client().append_to_list(key=f"{self.task_record.redis_index}:summary_record:process",
                                               values=[ProcessObject(desc=process).to_json() if isinstance(process,
                                                                                                           str) else process.to_json()
                                                       for process in
                                                       process_list])
