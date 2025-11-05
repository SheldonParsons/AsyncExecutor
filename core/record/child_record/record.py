from core.lua_executor.redis_helper import LuaScriptExecutor
from core.record.child_record.core import RecordController
from core.record.task_record import TaskRecord


class RecordInfoRecord(RecordController):

    def __init__(self, task_record: TaskRecord):
        super().__init__(task_record)

    async def change_info(self, **kwargs):
        await LuaScriptExecutor(self.get_client().client, 'update_fields').execute_async(
            f"{self.task_record.redis_index}:record_info", kwargs)

    async def increment_field(self, **kwargs):
        await LuaScriptExecutor(self.get_client().client, 'increment_fields').execute_async(
            f"{self.task_record.redis_index}:record_info",
            kwargs
        )
