from typing import Optional, List
from core.global_client.sync_redis import close_sync_pool


class TaskEffectManager:
    def __init__(self, redis_client, task_id: int, key_prefix: str = "record_status:"):
        self.redis = redis_client
        self.task_id = task_id
        self.key = f"{key_prefix}{task_id}"

    def close_client(self):
        close_sync_pool()

    def check_and_init(self) -> bool:
        value = self.redis.get(self.key)
        if value is None:
            self.redis.set(self.key, 1)
            return True
        try:
            int_val = int(value)
            return int_val == 1
        except (ValueError, TypeError):
            return False

    def set_stopped(self):
        self.redis.set(self.key, 0)

    def set_running(self):
        self.redis.set(self.key, 1)

    @staticmethod
    def batch_stop(redis_client, task_ids: List[int], key_prefix: str = "record_status:"):
        if not task_ids:
            return
        mapping = {f"{key_prefix}{tid}": 0 for tid in task_ids}
        print(f"stop mapping:{mapping}")
        redis_client.mset(mapping)
