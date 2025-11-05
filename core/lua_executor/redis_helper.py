import json
from typing import Union, Any

from core.lua_script.lua_script_manager import LuaScriptManager



class LuaScriptExecutor:
    def __init__(self, redis_client, script_name: str):
        self.redis = redis_client
        self.script_name = script_name
        from server.start import BASE_DIR
        self.script_sha1 = LuaScriptManager.get_script_sha1(BASE_DIR, script_name)

    async def execute_async(self, key: str, params: dict, *other_args, key_count=1, ) -> Any:
        """异步执行 Lua 脚本 (直接使用SHA1)"""
        try:
            return await self._execute_via_sha_async(self.script_sha1, key, params, *other_args, key_count=key_count)
        except Exception as e:
            raise e

    async def _execute_via_sha_async(self, sha: str, key, params: dict, *other_args, key_count=1) -> Any:
        """使用 SHA 执行脚本（异步）"""
        if len(other_args) > 0:
            return await self.redis.evalsha(sha, key_count, key, json.dumps(params), *other_args)
        else:
            return await self.redis.evalsha(sha, key_count, key, json.dumps(params))

    def _prepare_args(self, args: tuple, kwargs: dict) -> list:
        """准备传递给 Redis 的参数"""
        all_args = [str(arg) for arg in args]

        # 处理关键字参数（如果有）
        if kwargs:
            for key, value in kwargs.items():
                all_args.append(str(key))
                all_args.append(value)
        return all_args

    def _parse_result(self, result: Union[str, bytes]) -> Any:
        """解析 Redis 返回的结果"""
        if isinstance(result, bytes):
            try:
                # 尝试解码为 JSON
                return json.loads(result.decode('utf-8'))
            except UnicodeDecodeError:
                # 如果是二进制数据，直接返回字节
                return result
            except json.JSONDecodeError:
                # 如果是普通字符串，返回字符串
                return result.decode('utf-8')
        return result
