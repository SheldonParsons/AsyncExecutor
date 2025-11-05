import os
from typing import Union

import redis
import threading

_init_lock = threading.Lock()

# "单例"实例变量
_sync_pool: Union[redis.ConnectionPool, None] = None


def init_redis_pools(connect_str, max_connections=100):
    """
    初始化两个连接池。
    这个函数是幂等的（可以安全地多次调用）。
    """
    global _sync_pool
    with _init_lock:
        if _sync_pool is None:
            _sync_pool = redis.ConnectionPool.from_url(connect_str, max_connections=max_connections,decode_responses=True)


def get_sync_client():
    """
    从异步池获取一个*异步*的 Redis 客户端。
    """
    if _sync_pool is None:
        init_redis_pools(os.getenv("LOCAL_REDIS_CONNECTION"), max_connections=int(os.getenv("MAX_CONNECTIONS")))

    return redis.Redis(connection_pool=_sync_pool), _sync_pool


def close_sync_pool():
    """
    关闭异步连接池 (在进程退出时调用)。
    """
    global _sync_pool
    if _sync_pool:
        _sync_pool.disconnect()
        _sync_pool = None
