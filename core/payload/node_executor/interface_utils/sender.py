import asyncio
import json

import aiohttp
from aiohttp import ClientSession

from core.payload.node_executor.interface_utils.http_client import RequestTiming, ProcessLogging
from core.payload.utils.tools import get_current_ms


class HttpSender:

    def __init__(self, method, url, body, params, headers, session: ClientSession, finish_callback, exception_callback,
                 timeout: int = 60):
        self.method = method
        self.url = url
        self.body = body
        self.params = params
        self.headers = headers
        self.session: ClientSession = session
        self.finish_callback = finish_callback
        self.exception_callback = exception_callback

        self.timeout = aiohttp.ClientTimeout(
            total=int(timeout),
            connect=10,
            sock_connect=10,
            sock_read=int(timeout),
        )

    async def __call__(self):
        reqeust_timing = RequestTiming(get_current_ms())
        process = ProcessLogging()
        self.http_interface = None
        try:
            async with self.session.request(self.method, self.url, params=self.params, headers=self.headers,
                                            data=self.body,
                                            timeout=self.timeout,
                                            trace_request_ctx={"index": '0',
                                                               "timing": reqeust_timing,
                                                               "process": process,
                                                               "finish_callback": self.finish_callback,
                                                               "exception_callback": self.exception_callback}):
                pass
        except asyncio.TimeoutError as e:
            if self.exception_callback:
                error_time_at = get_current_ms()
                elapsed = error_time_at - reqeust_timing.start_time_at
                error_details = {
                    "type": type(e).__name__,
                    "info": f"{type(e).__name__}:响应超时，预期响应时间:{self.timeout.total} 秒",
                    "waste_time": f"{elapsed:.4f}",
                    "time": get_current_ms()
                }
                reqeust_timing.error_time = elapsed
                reqeust_timing.error_time_at = error_time_at
                await self.exception_callback(json.dumps(error_details, ensure_ascii=False), reqeust_timing, process,
                                              e)
