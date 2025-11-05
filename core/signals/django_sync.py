import json
import os

import aiohttp
from aiohttp import ClientSession

from core.enums.executor import ExecType
from core.signals.rpc_router import RpcCallbackTypeEnum, rcp_headers


class DjangoSyncSignal:

    @classmethod
    async def start_task_rcp(cls, task_id, record_id, exec_type: ExecType):
        if exec_type == ExecType.REMOTE:
            params = {
                'rcp_type': RpcCallbackTypeEnum.START_TASK.value
            }
            data = {
                'task_id': task_id,
                'record_id': record_id
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(url=os.getenv('ASYNCTEST_RCP_ROUTER'), data=json.dumps(data),
                                        params=params, headers=rcp_headers) as response:
                    return await response.json()

    @classmethod
    async def end_task_rcp(cls, task_id, record_id, exec_type: ExecType):
        if exec_type == ExecType.REMOTE:
            params = {
                'rcp_type': RpcCallbackTypeEnum.END_TASK.value
            }
            data = {
                'task_id': task_id,
                'record_id': record_id
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(url=os.getenv('ASYNCTEST_RCP_ROUTER'), data=json.dumps(data),
                                        params=params, headers=rcp_headers) as response:
                    res = await response.json()
                    print(f"res:{res}")
                    return json.dumps(res['data'])
