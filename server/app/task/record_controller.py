import json
from typing import Optional, Tuple, Any, Dict, List

from core.global_client.sync_redis import get_sync_client
from core.record.redis_client import AsyncRedisClient


class RecordController:

    def __init__(self, name):
        self.name = name
        self.client = get_sync_client()[0]

    def get_data(self, **kwargs):
        return getattr(self, self.name)(**kwargs)

    def get_json_list_by_chunk(self, key: str, start_index: int, record_backup_index=None,
                               extra_key: Optional[str] = None) -> Tuple[
        List[Dict[str, Any]], int, Optional[Any]]:
        """
        从 Redis 列表分批获取 JSON 数据并解析为字典列表。

        Args:
            record_backup_index:
            key (str): Redis 列表的键。
            start_index (int): 查询的起始索引。
            extra_key(str):额外的查询

        Returns:
            Tuple[List[Dict[str, Any]], int]: 一个元组, 包含:
                                              1. 解析后的字典列表。
                                              2. 下一次查询的新索引。
        """
        # 因为 decode_responses=True, 这里直接返回 List[str]
        pipe = self.client.pipeline()
        pipe.lrange(key, start_index, -1)
        if extra_key:
            pipe.get(extra_key)
        results = pipe.execute()
        json_strings: List[str] = results[0]
        if len(json_strings) == 0 and start_index == 0:
            # 尝试从文件恢复
            AsyncRedisClient.sync_import_from_file(record_backup_index)
            # --- 再次尝试查询（同样使用 pipeline）---
            pipe_retry = self.client.pipeline()
            pipe_retry.lrange(key, start_index, -1)
            if extra_key:
                pipe_retry.get(extra_key)  # 再次查询时也要带上 extra_key

            results = pipe_retry.execute()  # 使用新的结果覆盖旧的
            json_strings = results[0]
        if not json_strings and start_index == 0:
            raise RuntimeError("数据已过期，无法恢复")

        # --- 数据处理 ---
        extra_key_value = None
        if extra_key:
            # 如果提供了 extra_key，那么 results 列表的第二个元素就是它的值
            extra_key_value = json.loads(results[1])

        parsed_data: List[Dict[str, Any]] = []
        for item_str in json_strings:
            try:
                item_dict = json.loads(item_str)
                parsed_data.append(item_dict)
            except json.JSONDecodeError:
                continue

        # 注意：next_index 应该基于原始获取的数据量计算，而不是成功解析的数量
        next_index = start_index + len(json_strings)

        return parsed_data, next_index, extra_key_value

    def get_json_from_redis(self, key: str, record_backup_index: Any) -> Dict[str, Any]:
        """
        从 Redis 查询一个 JSON 数据，如果 key 不存在，则尝试从备份恢复并重新查询。

        Args:
            key (str): 要查询的 Redis key。
            record_backup_index (Any): 传递给恢复函数所需的备份索引。

        Returns:
            Dict[str, Any]: 从 Redis 获取并解析后的 Python 字典。

        Raises:
            RuntimeError: 如果初次查询和恢复后再次查询均失败。
            ValueError: 如果从 Redis 获取到的内容不是有效的 JSON 格式。
        """
        content = self.client.get(key)

        if content is None:
            AsyncRedisClient.sync_import_from_file(record_backup_index)
            content = self.client.get(key)

        if content is None:
            raise RuntimeError("数据已过期，无法恢复")

        try:
            data_dict = json.loads(content)
            return data_dict
        except json.JSONDecodeError as e:
            raise RuntimeError(f"从 key '{key}' 获取的内容无法被解析为 JSON。错误: {e}")

    def get_redis_details_batch(self,
                                record_backup_index: str,
                                parent_index: str,
                                child_indices: List[str]
                                ) -> Dict[str, Any]:
        """
        根据父级索引和子索引列表，批量从 Redis 中获取数据。

        Args:
            record_backup_index:
            parent_index (str): Redis key 的父级/前缀部分。
            child_indices (List[str]): 需要拼接在父级索引后的子索引列表。

        Returns:
            Dict[str, Any]: 一个字典，键是子索引，值是从 Redis 查询到的对应内容。

        Raises:
            RuntimeError: 数据在本地文件备份中已经过期。
        """
        # 1. 根据父级和子级索引，拼接出所有需要查询的完整 key
        # 使用列表推导式可以非常简洁地完成这个任务
        full_keys = [f"{record_backup_index}:{parent_index}:{child}" for child in child_indices]

        # 2. 使用 MGET 命令，在一次网络通信中获取所有 key 的值
        # mget 会返回一个列表，顺序与 full_keys 对应。如果某个 key 不存在，对应位置的值为 None。
        values = self.client.mget(full_keys)

        # 3. 检查是否有查询失败的 key (值为 None)
        if None in values:
            AsyncRedisClient.sync_import_from_file(record_backup_index)
            # 再次尝试读取
            values = self.client.mget(full_keys)
        if None in values:
            raise RuntimeError("数据已过期，无法恢复")

        # 4. 如果所有 key 都成功查到，将子索引和查询到的值组合成一个字典
        result_dict = dict(zip(child_indices, values))

        return result_dict
