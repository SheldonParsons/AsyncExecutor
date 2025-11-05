from core.record.redis_client import AsyncRedisClient
from core.record.task_record import TaskRecord


class RecordController:

    def __init__(self, task_record: TaskRecord):
        self.task_record = task_record

    def get_client(self) -> AsyncRedisClient:
        return self.task_record.redis
