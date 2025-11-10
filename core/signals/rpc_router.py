from enum import Enum

rcp_headers = {
    'Content-Type': 'application/json',
    'X-Internal': 'from_nginx'
}


class RpcCallbackTypeEnum(str, Enum):
    START_TASK = 'start_task'
    END_TASK = 'end_task'
