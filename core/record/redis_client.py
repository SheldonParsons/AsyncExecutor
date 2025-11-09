import os
import json
import asyncio
from pathlib import Path
from typing import Optional, List, Any, Callable, Dict

import aiofiles
from core.global_client.async_redis import get_async_client
from core.global_client.sync_redis import get_sync_client, close_sync_pool
from core.lua_executor.redis_helper import LuaScriptExecutor


class AsyncRedisClient:
    """
    一个异步的 Redis 客户端封装类，使用单例模式和连接池。
    """
    _lock = asyncio.Lock()

    def __init__(self, redis_connection_str: str = None):

        # 从环境变量读取配置，并提供合理的默认值
        async_global_redis_client, pool = get_async_client()
        self.pool = pool
        self.client = async_global_redis_client
        self.default_ex = int(os.getenv("REDIS_TASK_RECORD_TIMEOUT"))

    async def close(self):
        """优雅地关闭连接池"""
        if self.pool:
            await self.pool.disconnect()

    # --- 7. KV (String) 类型操作 ---

    async def set_value(self, key: str, value: Any, ex: Optional[int] = None):
        """
        设置一个 KV 值，并附加默认的超时时间。
        如果 key 不存在，会自动创建。
        """
        timeout = ex if ex is not None else self.default_ex
        await self.client.set(key, value, ex=timeout)

    async def batch_set_value(self, data: dict, ex: Optional[int] = None):
        """
        使用 Pipeline 批量设置 KV 值和过期时间。

        Args:
            data (dict): 一个字典，键为 Redis key，值为要存储的数据。
            ex (Optional[int]): 超时时间，单位秒。如果为 None，则使用默认值。
        """
        timeout = ex if ex is not None else self.default_ex
        # 启用一个 Pipeline
        async with self.client.pipeline() as pipe:
            for key, value in data.items():
                # 将 SET 命令添加到管道中
                pipe.set(key, value)
                # 将 EXPIRE 命令添加到管道中
                pipe.expire(key, timeout)

            # 一次性执行所有命令
            await pipe.execute()

    async def batch_create_and_init_lists_updated(self, data: dict[str, list[Any]], ex: Optional[int] = None) -> None:
        if not data:
            return
        for key, values in data.items():
            if not values:
                continue

            # 确保 value 是一个有效的 JSON 字符串
            new_value_str = values[0]
            try:
                await LuaScriptExecutor(self.client, 'print_value').execute_async(key, json.loads(new_value_str))
            except (json.JSONDecodeError, TypeError):
                print(f"跳过 key '{key}'，因为其值不是有效的 JSON 字符串: {new_value_str}")
                continue

    async def batch_create_and_init_lists(self, data: dict[str, list[Any]], ex: Optional[int] = None) -> None:
        """
        使用 Pipeline 批量创建多个列表类型的 key，并为其插入初始内容。

        Args:
            data (dict): 一个字典，键为 Redis key，值为包含初始内容的列表。
            ex (Optional[int]): 可选的过期时间，单位秒。
        """
        if not data:
            return

        timeout = ex if ex is not None else self.default_ex

        # 启用一个 Pipeline
        async with self.client.pipeline() as pipe:
            for key, initial_values in data.items():
                if initial_values:
                    # 将 RPUSH 命令添加到管道中
                    pipe.rpush(key, *initial_values)
                    # 将 EXPIRE 命令添加到管道中
                    pipe.expire(key, timeout)

            # 一次性执行所有命令
            await pipe.execute()

    async def get_value(self, key: str) -> Optional[str]:
        """获取一个 KV 值"""
        return await self.client.get(key)

    async def delete_value(self, *key: str) -> int:
        """删除一个或多个 KV 值"""
        return await self.client.delete(*key)

    async def increment_fields_lua(self, key: str, **kwargs):
        await LuaScriptExecutor(self.client, 'increment_fields').execute_async(key, kwargs)

    async def update_fields_lua(self, key, **kwargs):
        await LuaScriptExecutor(self.client, 'update_fields').execute_async(key, kwargs)

    async def update_fields_to_list_lua(self, key, *other_args, **kwargs):
        await LuaScriptExecutor(self.client, 'update_fields_to_list').execute_async(key, kwargs, *other_args)

    async def locked_update_value(self, key: str, update_function: Callable[[Optional[str]], Any]) -> Any:
        """
        [事务性]带分布式锁的“读取-修改-写入”操作。
        在执行期间，其他客户端对该 key 的锁请求会被阻塞。

        Args:
            key (str): 要操作的键。
            update_function (Callable): 一个接收当前值并返回新值的函数。

        Returns:
            Any: update_function 返回的新值。
        """
        # 使用 redis 内置的分布式锁，超时10秒防止死锁
        async with self.client.lock(f"lock:{key}", timeout=10) as lock:
            if not lock.owned:
                raise Exception(f"Could not acquire lock for key: {key}")

            # 1. 在锁内安全地读取当前值
            current_value = await self.get_value(key)

            # 2. 调用外部函数计算新值
            new_value = update_function(current_value)

            # 3. 安全地写入新值
            await self.set_value(key, new_value)

            return new_value

    # --- 8. List 类型操作 ---

    def lock_context(self, key: str, timeout: int = 10):
        """
        提供一个异步上下文管理器来锁定一个 key。
        这是执行多个需要锁保护的操作的最佳方式。

        用法:
        async with redis_client.lock_context("my_key"):
            # 在这个代码块内，你拥有 "lock:my_key" 的锁
            value = await redis_client.get_value("my_key")
            # ... do something ...
            await redis_client.set_value("my_key", new_value)
        """
        # 我们直接返回 redis-py 库内置的强大锁对象
        return self.client.lock(f"lock:{key}", timeout=timeout)

    async def _safe_business_logic_demo(self, task_key: str):
        # 使用我们新的 lock_context 来创建一个受保护的代码块
        async with self.lock_context(task_key):
            # 1. 安全地读取
            current_data_str = await self.get_value(task_key)
            data = json.loads(current_data_str) if current_data_str else {"steps": []}

            # 2. 安全地修改
            import time
            data["steps"].append(f"Step added at {time.time()}")

            # 3. 安全地写回
            await self.set_value(task_key, json.dumps(data))

    async def append_to_list(self, key: str, values: List[Any], ex: Optional[int] = None):
        """
        向列表末尾追加一个或多个值。
        如果 key 不存在，会自动创建。
        """
        # 9. 是的，Redis 的 RPUSH 等命令在 key 不存在时会自动创建
        if not values:
            return
        # 使用 pipeline 确保两个命令的原子性
        async with self.client.pipeline() as pipe:
            pipe.rpush(key, *values)
            timeout = ex if ex is not None else self.default_ex
            pipe.expire(key, timeout)
            await pipe.execute()

    async def get_list_slice(self, key: str, start_index: int = 0) -> List[str]:
        """
        获取列表的一个切片。
        - start_index = 0: 返回整个列表。
        - start_index > 0: 返回从该索引到末尾的部分。
        """
        if start_index < 0:
            start_index = 0  # 保证下标大于等于0

        # Redis 的 LRANGE 命令中，-1 代表最后一个元素
        return await self.client.lrange(key, start_index, -1)

    # --- 10. 数据备份函数 ---

    async def export_by_prefix(self, key_prefix: str, output_dir: str):
        """
        [优化版]根据 key 前缀备份数据，同时保留 TTL (超时时间) 信息。
        """
        backup_data = {}
        async for key in self.client.scan_iter(f"{key_prefix}*"):
            key_type = await self.client.type(key)
            # [新增]获取 key 的剩余存活时间 (TTL)，单位为秒
            # -1 表示永不过期, -2 表示 key 不存在
            ttl = await self.client.ttl(key)
            value = None
            if key_type == 'string':
                value = await self.get_value(key)
            elif key_type == 'list':
                value = await self.get_list_slice(key, 0)

            if value is not None:
                backup_data[key] = {
                    "type": key_type,
                    "value": value,
                    "ttl": ttl  # [新增]将 TTL 信息存入备份
                }

        if not backup_data:
            return

        os.makedirs(output_dir, exist_ok=True)
        safe_filename = key_prefix.replace(':', '_').strip('_') + '.json'
        filepath = os.path.join(output_dir, safe_filename)
        async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(backup_data, indent=2, ensure_ascii=False))

    @classmethod
    def sync_import_from_file(cls, key_prefix: str):
        sync_redis_client, _ = get_sync_client()
        current_dir = Path(__file__).resolve().parent
        parent_dir = current_dir.parent
        output_dir = parent_dir / "static" / "record_redis_backup"
        safe_filename = key_prefix.replace(':', '_').strip('_') + '.json'
        filepath = os.path.join(output_dir, safe_filename)
        try:
            # 1. 使用标准的同步 open() 函数读取文件
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                backup_data: Dict[str, Any] = json.loads(content)
        except FileNotFoundError:
            raise RuntimeError(f"错误：备份文件未找到 at '{key_prefix}'")
        except json.JSONDecodeError:
            raise RuntimeError(f"错误：文件 '{key_prefix}' 不是一个有效的 JSON 文件。")

        if not backup_data:
            raise RuntimeError("信息：备份文件为空，无需恢复。")

        print(f"成功读取备份文件，准备恢复 {len(backup_data)} 个 key...")

        # 2. 使用同步的 Redis 客户端和 pipeline
        # 移除了 'async with'，使用标准的 'with'
        with sync_redis_client.pipeline(transaction=False) as pipe:
            for key, data in backup_data.items():
                key_type = data.get('type')
                value = data.get('value')
                ttl = data.get('ttl', -1)

                # 逻辑保持不变
                pipe.delete(key)

                if key_type == 'string':
                    pipe.set(key, value)
                elif key_type == 'list' and isinstance(value, list) and value:
                    pipe.rpush(key, *value)
                # 您可以根据需要添加对其他类型的支持，例如 hash, set 等
                # elif key_type == 'hash' and isinstance(value, dict) and value:
                #     pipe.hset(key, mapping=value)

                if ttl > 0:
                    pipe.expire(key, int(ttl))

            # 3. 移除了 'await'，直接执行
            pipe.execute()
        close_sync_pool()

    # AsyncRedisClient 类中的新增函数
    async def import_from_file(self, filepath: str):
        """
        从指定的备份文件 (JSON 格式) 中恢复数据到 Redis。
        """
        try:
            async with aiofiles.open(filepath, 'r', encoding='utf-8') as f:
                content = await f.read()
                backup_data = json.loads(content)
        except FileNotFoundError:
            return
        except json.JSONDecodeError:
            return

        if not backup_data:
            return

        # 使用 Pipeline 批量执行命令，极大提高效率
        async with self.client.pipeline(transaction=False) as pipe:
            for key, data in backup_data.items():
                key_type = data.get('type')
                value = data.get('value')
                ttl = data.get('ttl', -1)

                # 在恢复前，最好先删除旧的 key，防止类型冲突
                pipe.delete(key)

                if key_type == 'string':
                    pipe.set(key, value)
                elif key_type == 'list' and value:  # 确保 value 不为空
                    pipe.rpush(key, *value)

                # 如果 TTL 大于 0，则设置过期时间
                if ttl > 0:
                    pipe.expire(key, int(ttl))

            await pipe.execute()
