from enum import Enum

rcp_headers = {
    'Content-Type': 'application/json',
    'HTTP_X_INTERNAL': 'from_nginx'
}


class RpcCallbackTypeEnum(str, Enum):
    START_TASK = 'start_task'
    END_TASK = 'end_task'
