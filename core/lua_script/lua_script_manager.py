import hashlib
import os
import traceback
from typing import Dict

from core.global_client.sync_redis import get_sync_client, close_sync_pool

# 全局脚本缓存
LUA_SCRIPTS_CACHE: Dict[str, Dict[str, str]] = {}


class LuaScriptManager:
    @classmethod
    def initialize(cls, BASE_DIR, script_dir: str = None):
        """初始化并加载所有Lua脚本"""
        if not script_dir:
            lua_dir = os.getenv("LUA_SCRIPTS_DIR")
            script_dir = BASE_DIR + '/' + lua_dir

        if not os.path.exists(script_dir):
            raise FileNotFoundError(f"Lua scripts directory not found: {script_dir}")

        # 清空缓存
        global LUA_SCRIPTS_CACHE
        LUA_SCRIPTS_CACHE = {}

        # 加载所有脚本
        for filename in os.listdir(script_dir):
            if filename.endswith('.lua'):
                script_name = os.path.splitext(filename)[0]
                cls.load_script(BASE_DIR, script_name, script_dir)
        # 加载到redis缓存
        cls.preload_to_redis()
        close_sync_pool()

    @classmethod
    def _delete_data(cls, r, prefix: str):
        """
            使用 SCAN 和 Pipelining 高效删除指定前缀的键。
            :param r: redis.Redis 客户端实例
            :param prefix: 要删除的键前缀
            """
        print(f"开始删除前缀为 '{prefix}*' 的所有键...")
        print(r.select(0))
        keys_to_delete = r.scan_iter(match=f"{prefix}*")  # 匹配所有以 prefix 开头的键
        for key in keys_to_delete:
            r.delete(key)  # 删除每一个匹配到的键
            print(f"Deleted key: {key}")

    @classmethod
    def preload_to_redis(cls):
        redis_client, _ = get_sync_client()

        global LUA_SCRIPTS_CACHE
        for script_name, script_data in LUA_SCRIPTS_CACHE.items():
            try:
                # 使用SCRIPT LOAD确保脚本在Redis中可用
                loaded_sha = redis_client.script_load(script_data['content'])

                # 验证SHA1是否匹配
                if loaded_sha != script_data['sha1']:
                    print(f"Script {script_name} SHA1 mismatch: "
                          f"expected {script_data['sha1']}, got {loaded_sha}")
            except Exception as e:
                traceback.print_exc()
                print(f"Failed to preload script {script_name} to Redis: {str(e)}")

    @classmethod
    def load_script(cls, BASE_DIR, script_name: str, script_dir: str = None):
        """加载单个脚本到缓存"""
        if not script_dir:
            lua_dir = os.getenv("LUA_SCRIPTS_DIR")
            script_dir = BASE_DIR + '/' + lua_dir

        file_path = os.path.join(script_dir, f"{script_name}.lua")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                sha1 = hashlib.sha1(content.encode('utf-8')).hexdigest()

                global LUA_SCRIPTS_CACHE
                LUA_SCRIPTS_CACHE[script_name] = {
                    'content': content,
                    'sha1': sha1
                }
                return sha1
        except FileNotFoundError:
            raise ValueError(f"Lua script '{script_name}' not found at {file_path}")

    @classmethod
    def get_script_sha1(cls, BASE_DIR, script_name: str) -> str:
        """获取脚本的SHA1值"""
        global LUA_SCRIPTS_CACHE
        if script_name not in LUA_SCRIPTS_CACHE:
            cls.load_script(BASE_DIR, script_name)
        return LUA_SCRIPTS_CACHE[script_name]['sha1']

    @classmethod
    def get_script_content(cls, BASE_DIR, script_name: str) -> str:
        """获取脚本内容"""
        global LUA_SCRIPTS_CACHE
        if script_name not in LUA_SCRIPTS_CACHE:
            cls.load_script(BASE_DIR, script_name)
        return LUA_SCRIPTS_CACHE[script_name]['content']
