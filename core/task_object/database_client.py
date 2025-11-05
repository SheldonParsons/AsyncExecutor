from abc import ABC, abstractmethod
from typing import Dict, List

import aiomysql
import asyncpg


class DatabaseController:
    def __init__(self):
        self.pool_client_cache_mapping: Dict[str, DatabasePoolClient] = {}

    async def get_result(self, host=None, port=None, password=None, username=None, database_name=None,
                         database_type=None, sql=None, *args, **kwargs) -> List:
        pool_client: DatabasePoolClient = await self.get_pool_client(host, port, password, username, database_name,
                                                                     database_type)
        return await pool_client.execute(sql)

    async def get_pool_client(self, host=None, port=None, password=None, username=None, database_name=None,
                              database_type=None):
        key = f"{host}:{port}:{password}:{username}:{database_name}"
        pool_client = self.pool_client_cache_mapping.get(key, None)
        if not pool_client:
            pool_client = await self.create_new_client_pool(host, port, password, username, database_name,
                                                            database_type)
        return pool_client

    async def create_new_client_pool(self, host, port, password, username, database_name, database_type):
        key = f"{host}:{port}:{password}:{username}:{database_name}"
        self.pool_client_cache_mapping[key] = await self.generate_pool(host, port, password, username, database_name,
                                                                       database_type)
        return self.pool_client_cache_mapping[key]

    @classmethod
    async def generate_pool(cls, host, port, password, username, database_name, database_type):
        if database_type == 'pgsql':
            postgres_pool_client = PostgresPoolClient()
            await postgres_pool_client.generate_pool(host, port, password, username, database_name)
            return postgres_pool_client
        elif database_type == 'mysql':
            mysql_pool_client = MysqlPoolClient()
            await mysql_pool_client.generate_pool(host, port, password, username, database_name)
            return mysql_pool_client
        return None

    async def close(self):
        for pool_client in self.pool_client_cache_mapping.values():
            if pool_client:
                await pool_client.close()


class DatabasePoolClient(ABC):

    @abstractmethod
    async def generate_pool(self, host, port, password, username, database_name):
        pass

    @abstractmethod
    async def close(self):
        pass

    @abstractmethod
    async def execute(self, sql):
        pass


class PostgresPoolClient(DatabasePoolClient):
    def __init__(self):
        self.pool = None

    async def generate_pool(self, host, port, password, username, database_name):
        self.pool = await asyncpg.create_pool(
            host=host,
            port=port,
            user=username,
            password=password,
            database=database_name,
            timeout=5,
            min_size=1,
            max_size=10
        )

    async def close(self):
        if self.pool:
            await self.pool.close()

    async def execute(self, sql):
        async with self.pool.acquire() as conn:
            command = sql.strip().split()[0].upper()
            if command == "SELECT":
                rows = await conn.fetch(sql)
                return [dict(row) for row in rows]
            elif command in {"INSERT", "UPDATE", "DELETE"}:
                return [await conn.execute(sql)]
            else:
                raise ValueError(f"该SQL语句暂不支持: {sql}")


class MysqlPoolClient(DatabasePoolClient):
    def __init__(self):
        self.pool = None

    async def generate_pool(self, host, port, password, username, database_name):
        self.pool = await aiomysql.create_pool(
            host=host,
            port=port,
            user=username,
            password=password,
            db=database_name,
            connect_timeout=5,
            autocommit=True,
            minsize=1,
            maxsize=10
        )

    async def close(self):
        if self.pool:
            await self.pool.close()

    async def execute(self, sql):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                command = sql.strip().split()[0].upper()
                if command == "SELECT":
                    await cur.execute(sql)
                    rows = await cur.fetchall()
                    return list(rows)
                elif command in {"INSERT", "UPDATE", "DELETE"}:
                    await cur.execute(sql)
                    return [f"{command} {cur.rowcount}"]
                else:
                    raise ValueError(f"该SQL语句暂不支持: {sql}")
