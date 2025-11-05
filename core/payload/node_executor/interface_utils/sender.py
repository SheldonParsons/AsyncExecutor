from core.payload.node_executor.interface_utils.http_client import RequestTiming, ProcessLogging
from core.payload.utils.tools import get_current_ms


class HttpSender:

    def __init__(self, method, url, body, params, headers, session, finish_callback, exception_callback):
        self.method = method
        self.url = url
        self.body = body
        self.params = params
        self.headers = headers
        self.session = session
        self.finish_callback = finish_callback
        self.exception_callback = exception_callback

    async def __call__(self):
        reqeust_timing = RequestTiming(get_current_ms())
        process = ProcessLogging()
        self.http_interface = None
        async with self.session.request(self.method, self.url, params=self.params, headers=self.headers, data=self.body,
                                        trace_request_ctx={"index": '0',
                                                           "timing": reqeust_timing,
                                                           "process": process,
                                                           "finish_callback": self.finish_callback,
                                                           "exception_callback": self.exception_callback}):
            pass


