import json
from functools import lru_cache

from core.record.redis_client import AsyncRedisClient
from core.record.utils import ProcessObject
from core.task_object.child_case_list import ChildCase
from core.task_object.generate_object import GlobalOption


class TaskRecord:

    def __init__(self, global_option: GlobalOption):
        self.global_option = global_option
        self.redis = AsyncRedisClient()
        self.redis_index = global_option.record.record_backup_index

    async def cache_info(self):
        # task_info 缓存
        await self.redis.set_value(f"{self.redis_index}:task_info",
                                   json.dumps(self.global_option.task_info.to_dict(), ensure_ascii=False))
        # case list缓存
        # await self.redis.set_value(f"{self.redis_index}:case_info",
        #                            json.dumps(self.global_option.case_list.to_dict(), ensure_ascii=False))

        # step_mapping 缓存
        # await self.redis.set_value(f"{self.redis_index}:step_mapping",
        #                            json.dumps(self.global_option.step_mapping.to_dict(), ensure_ascii=False))
        # 原始 global_cache 缓存
        # await self.redis.set_value(f"{self.redis_index}:origin_global_cache",
        #                            json.dumps(self.global_option.global_cache.to_dict(), ensure_ascii=False))
        # 原始 record 缓存
        await self.redis.set_value(f"{self.redis_index}:record_info",
                                   json.dumps(self.global_option.record.to_dict(), ensure_ascii=False))
        # 初始化创建步骤record
        await self.initial_step_key(self.global_option.case_steps_snapshot)

        child_case_process_mapping = {}
        child_case_status_mapping = {}

        def _delete_cache_fields(child_case_list: list):
            res = []
            for item in child_case_list:
                res.append(json.dumps({
                    key: value for key, value in item.items() if
                    key not in ["temp_variables", "origin_child_steps"]
                }, ensure_ascii=False))
                child_case_index = item.get('index_in_global_list')
                child_case_key_prefix = f"{self.redis_index}:child_case_record:{child_case_index}"
                child_case_process_mapping[f"{child_case_key_prefix}:process"] = [
                    ProcessObject(desc="子用例等待运行中...").to_json()]
                case_index = item.get('parent')
                child_case_status_mapping[f"{child_case_key_prefix}:status"] = self.step_status_change(case_index)
            return res

        # child_case_list 缓存
        await self.redis.batch_create_and_init_lists(
            {f"{self.redis_index}:child_case_record:child_case_list": _delete_cache_fields(
                self.global_option.child_case_list.to_dict())})
        await self.redis.batch_set_value(child_case_status_mapping)
        # child_case_process 缓存
        await self.redis.batch_create_and_init_lists(child_case_process_mapping)

    @lru_cache(maxsize=None)
    def step_status_change(self, parent):
        origin_mapping = self.global_option.step_mapping.mapping.get(str(parent))
        cache_dict = {}
        abort_steps = set()
        for key, item in origin_mapping.items():
            if item.type == 'empty':
                continue
            if item.type == 'case':
                abort_steps.update(item.children)
            if key in abort_steps:
                if getattr(item, 'children', 0) != 0:
                    abort_steps.update(item.children)
                continue
            cache_dict[item.id] = {
                "status": "mid_pending",
                "result": 'mid_unknown'
            }
        return json.dumps(cache_dict, ensure_ascii=False)

    async def cache_redis_record(self, key, output_dir):
        await self.redis.export_by_prefix(key, output_dir)

    async def update_params(self, key=None, **kwargs):
        await self.redis.update_fields_lua(key, **kwargs)

    async def update_fields_to_list(self, key=None, *other_args, **kwargs):
        await self.redis.update_fields_to_list_lua(key, *other_args, **kwargs)

    async def increment_field(self, key, **kwargs):
        def _increment(task_info):
            task_info: dict = json.loads(task_info)
            for key, value in kwargs.items():
                task_info[key] = int(task_info[key]) + int(value)
            return json.dumps(task_info, ensure_ascii=False)

        await self.redis.locked_update_value(key, _increment)

    async def batch_push_to_key(self, key: str, *args):
        await self.redis.batch_create_and_init_lists({
            key: list(args)
        })

    async def batch_push_or_update_to_key(self, key: str, *args):
        await self.redis.batch_create_and_init_lists_updated({
            key: list(args)
        })

    async def get_value(self, key):
        return await self.redis.get_value(key)

    @classmethod
    def push_key_to_mapping(cls, step_list, prefix, status_mapping, process_mapping):
        for step in step_list:
            if step["type"] == 'empty':
                continue
            step_status_index = f"{prefix}:step:{step['id']}:status"
            step_process_index = f"{prefix}:step:{step['id']}:process"
            status_mapping[step_status_index] = json.dumps({
                "id": step["id"],
                "type": step["type"],
                "label": step["label"],
                "status": 'mid_pending',
                "result": "mid_unknown",
                "start": 0,
                "end": 0
            }, ensure_ascii=False)
            process_mapping[step_process_index] = [ProcessObject(desc="步骤等待运行中...").to_json()]
            if step.get("children", None):
                cls.push_key_to_mapping(step["children"], prefix, status_mapping, process_mapping)

    async def initial_step_key(self, case_steps_snapshot):
        add_step_default_status_mapping = {}
        add_step_process_mapping = {
            f"{self.redis_index}:summary_record:process": [ProcessObject(desc="任务等待运行中...").to_json()]
        }
        for child_case in self.global_option.child_case_list.list:
            child_case: ChildCase = child_case
            prefix_index = f"{self.redis_index}:step_record"
            case_id = child_case.case_id
            child_index = child_case.index_in_global_list
            case_index = f"{prefix_index}:case:{case_id}:child_case:{child_index}"
            step_list = case_steps_snapshot.get(str(case_id))
            self.push_key_to_mapping(step_list, case_index, add_step_default_status_mapping,
                                     add_step_process_mapping)
        await self.redis.batch_set_value(add_step_default_status_mapping)
        await self.redis.batch_create_and_init_lists(add_step_process_mapping)

    async def close(self):
        await self.redis.close()
