import json
from typing import Union

import aiohttp
import socket

from core.payload.utils.tools import get_current_ms

try:
    SO_REUSEPORT = socket.SO_REUSEPORT
except AttributeError:
    SO_REUSEPORT = 0x0200

TIMEOUT = 60


class ProcessLogging:

    def __init__(self):
        self.loggings = []

    def append(self, log: str):
        self.loggings.append(log)

    def to_json(self):
        return json.dumps(self.__dict__, ensure_ascii=False)


class RequestTiming:

    def __init__(self, start_time_at: float):
        self.start_time_at = start_time_at
        self.request_start: Union[float, None] = None
        self.total_time: Union[float, None] = None
        self.receive_chunk_time_last: Union[float, None] = None
        self.receive_chunk_time_last_at: Union[float, None] = None
        self.network_time: Union[float, None] = None
        self.response_time_at: Union[float, None] = None
        self.error_time: Union[float, None] = None
        self.error_time_at: Union[float, None] = None
        self.redirect_time: Union[float, None] = None
        self.redirect_time_at: Union[float, None] = None
        self.queue_start: Union[float, None] = None
        self.queue_start_at: Union[float, None] = None
        self.queue_end: Union[float, None] = None
        self.queue_end_at: Union[float, None] = None
        self.conn_create_start: Union[float, None] = None
        self.conn_create_start_at: Union[float, None] = None
        self.conn_create_end: Union[float, None] = None
        self.conn_create_end_at: Union[float, None] = None
        self.dns_start_at: Union[float, None] = None
        self.dns_start: Union[float, None] = None
        self.dns_end: Union[float, None] = None
        self.dns_end_at: Union[float, None] = None

    def to_json(self):
        return json.dumps(self.__dict__, ensure_ascii=False)


class OptimizedTCPConnector(aiohttp.TCPConnector):
    """优化连接器配置，解决端口耗尽问题"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def _create_connection(self, req, traces, timeout):
        try:
            conn = await super()._create_connection(req, traces, timeout)
            transport = conn.transport
            sock = transport.get_extra_info('socket')

            if sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.setsockopt(socket.SOL_SOCKET, SO_REUSEPORT, 1)
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

                # 设置更激进的保活参数
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                if hasattr(socket, 'TCP_KEEPIDLE'):
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 30)
                if hasattr(socket, 'TCP_KEEPINTVL'):
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
                if hasattr(socket, 'TCP_KEEPCNT'):
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)
            return conn
        except Exception as e:
            raise e


class HttpClient:

    def __init__(self):
        self.session = None

    def get_session(self):
        connector = OptimizedTCPConnector(
            limit=0,  # 无限制连接数
            enable_cleanup_closed=True,  # 主动清理关闭连接
            force_close=True,  # 避免TIME_WAIT堆积
            ssl=False,
            use_dns_cache=True,
            ttl_dns_cache=300
        )

        timeout = aiohttp.ClientTimeout(
            total=TIMEOUT,  # 请求总超时
            connect=TIMEOUT,  # TCP连接超时
            sock_connect=TIMEOUT,  # socket connect 超时
            sock_read=TIMEOUT  # socket 读取超时
        )
        trace_config = aiohttp.TraceConfig()
        # 注册所有钩子
        trace_config.on_request_start.append(self.on_request_start)
        trace_config.on_request_chunk_sent.append(self.on_request_chunk_sent)
        trace_config.on_response_chunk_received.append(self.on_response_chunk_received)
        trace_config.on_request_end.append(self.on_request_end)
        trace_config.on_request_exception.append(self.on_request_exception)
        trace_config.on_request_redirect.append(self.on_request_redirect)
        trace_config.on_connection_queued_start.append(self.on_connection_queued_start)
        trace_config.on_connection_queued_end.append(self.on_connection_queued_end)
        trace_config.on_connection_create_start.append(self.on_connection_create_start)
        trace_config.on_connection_create_end.append(self.on_connection_create_end)
        trace_config.on_dns_resolvehost_start.append(self.on_dns_resolvehost_start)
        trace_config.on_dns_resolvehost_end.append(self.on_dns_resolvehost_end)
        self.session = aiohttp.ClientSession(connector=connector, timeout=timeout, trust_env=True,
                                             trace_configs=[trace_config])

        return self.session

    async def _get_response_details(self, response, request_start):
        """获取响应详细信息"""
        headers = dict(response.headers)

        # 处理响应体 - 注意：这里不会消耗响应体

        # 对于小文本响应，可以记录内容
        content_type = headers.get('Content-Type', '')
        if 'multipart/form-data' not in content_type:
            body = await response.read()
            body_info = f"{body.decode('utf-8', errors='replace')}"
        else:
            body_info = "文件类型响应体将不会被记录"
        return {
            "status": response.status,
            "headers": headers,
            "body": body_info,
            "url": str(response.url),
            "time": get_current_ms(),
            "waste_time": (get_current_ms() - request_start) / 1000
        }

    # 1. 请求开始
    async def on_request_start(self, session, trace_config_ctx, params):
        """请求开始时触发"""
        timing: RequestTiming = trace_config_ctx.trace_request_ctx["timing"]
        timing.request_start = get_current_ms()

    # 2. 数据块发送
    async def on_request_chunk_sent(self, session, trace_config_ctx, params):
        """每次发送数据块时触发"""
        ctx = trace_config_ctx.trace_request_ctx
        timing: RequestTiming = ctx["timing"]
        elapsed = (get_current_ms() - timing.conn_create_start_at) / 1000
        process: ProcessLogging = ctx["process"]
        process.append(f"[{ctx['index']}] 发送数据块: {len(params.chunk)} 字节 | 耗时: {elapsed:.4f}s")

    # 3. 数据块接收
    async def on_response_chunk_received(self, session, trace_config_ctx, params):
        """每次接收数据块时触发"""
        ctx = trace_config_ctx.trace_request_ctx
        receive_chunk_time_last_at = get_current_ms()
        timing: RequestTiming = ctx["timing"]
        elapsed = (receive_chunk_time_last_at - timing.conn_create_end_at) / 1000
        timing.receive_chunk_time_last = elapsed
        timing.receive_chunk_time_last_at = receive_chunk_time_last_at
        process: ProcessLogging = ctx["process"]
        process.append(f"[{ctx['index']}] 接收数据块: {len(params.chunk)} 字节 | 耗时: {elapsed:.4f}s")

    # 4. 请求完成
    async def on_request_end(self, session, trace_config_ctx, params):
        """请求成功完成时触发"""
        ctx = trace_config_ctx.trace_request_ctx
        timing: RequestTiming = ctx["timing"]
        response_details = await self._get_response_details(params.response, timing.request_start)
        end_time = get_current_ms()
        total_time = (end_time - timing.start_time_at) / 1000
        network_time = (end_time - timing.request_start) / 1000
        timing.total_time = total_time
        timing.network_time = network_time
        timing.response_time_at = end_time
        # 获取响应详细信息
        process: ProcessLogging = ctx["process"]
        process.append(f"[{ctx['index']}]总耗时: {total_time:.4f}s | 网络耗时: {network_time:.4f}s")
        await ctx["finish_callback"](json.dumps(response_details, ensure_ascii=False), timing, process)

    # 5. 请求异常
    async def on_request_exception(self, session, trace_config_ctx, params):
        """请求发生异常时触发"""
        ctx = trace_config_ctx.trace_request_ctx
        error_time_at = get_current_ms()
        timing: RequestTiming = ctx["timing"]
        elapsed = error_time_at - timing.start_time_at

        error_details = {
            "type": type(params.exception).__name__,
            "info": f"{type(params.exception).__name__}:{str(params.exception)}",
            "waste_time": f"{elapsed:.4f}",
            "time": get_current_ms()
        }

        timing.error_time = elapsed
        timing.error_time_at = error_time_at
        await ctx["exception_callback"](json.dumps(error_details, ensure_ascii=False), timing, ctx["process"])

    # 6. 请求重定向
    async def on_request_redirect(self, session, trace_config_ctx, params):
        """发生重定向时触发"""
        ctx = trace_config_ctx.trace_request_ctx
        redirect_time_at = get_current_ms()
        timing: RequestTiming = ctx["timing"]
        elapsed = redirect_time_at - timing.start_time_at
        timing.redirect_time = elapsed
        timing.redirect_time_at = redirect_time_at
        process: ProcessLogging = ctx["process"]
        redirect_path = params.response.headers.get('Location', None)
        if not redirect_path:
            redirect_path = '查询失败'
        process.append(
            f"[{ctx['index']}][触发重定向]原URL: {params.url}\n新URL: {redirect_path}\n状态码: {params.response.status}\n时间: {elapsed:.4f}ms")

    # 7. 连接排队开始
    async def on_connection_queued_start(self, session, trace_config_ctx, params):
        """连接进入连接池队列时触发"""
        ctx = trace_config_ctx.trace_request_ctx
        queue_start_at = get_current_ms()
        timing: RequestTiming = ctx["timing"]
        elapsed = queue_start_at - timing.request_start
        timing.queue_start_at = queue_start_at
        timing.queue_start = elapsed
        process: ProcessLogging = ctx["process"]
        process.append(f"[{ctx['index']}] 连接进入队列")

    # 8. 连接排队结束
    async def on_connection_queued_end(self, session, trace_config_ctx, params):
        """连接离开连接池队列时触发"""
        ctx = trace_config_ctx.trace_request_ctx
        timing: RequestTiming = ctx["timing"]
        queue_end_at = get_current_ms()
        queue_time = (queue_end_at - timing.queue_start_at) / 1000
        timing.queue_end = queue_time
        timing.queue_end_at = queue_end_at
        process: ProcessLogging = ctx["process"]
        process.append(f"[{ctx['index']}] 连接离开队列 | 排队耗时: {queue_time:.4f}s")

    # 9. 连接创建开始
    async def on_connection_create_start(self, session, trace_config_ctx, params):
        """开始创建新连接时触发"""
        ctx = trace_config_ctx.trace_request_ctx
        conn_create_start_at = get_current_ms()
        timing: RequestTiming = ctx["timing"]
        conn_create_start = conn_create_start_at - timing.request_start
        timing.conn_create_start_at = conn_create_start_at
        timing.conn_create_start = conn_create_start
        process: ProcessLogging = ctx["process"]
        process.append(f"[{ctx['index']}] 开始创建连接")

    # 10. 连接创建完成
    async def on_connection_create_end(self, session, trace_config_ctx, params):
        """连接创建完成时触发"""
        ctx = trace_config_ctx.trace_request_ctx
        timing: RequestTiming = ctx["timing"]
        conn_create_end_at = get_current_ms()
        conn_create_end = (conn_create_end_at - timing.conn_create_start_at) / 1000
        timing.conn_create_end = conn_create_end
        timing.conn_create_end_at = conn_create_end_at
        process: ProcessLogging = ctx["process"]
        process.append(f"[{ctx['index']}] 连接创建完成 | 耗时: {conn_create_end:.4f}s")

    # 11. DNS解析开始
    async def on_dns_resolvehost_start(self, session, trace_config_ctx, params):
        """开始DNS解析时触发"""
        ctx = trace_config_ctx.trace_request_ctx
        ctx["dns_start"] = get_current_ms()
        timing: RequestTiming = ctx["timing"]
        dns_start_at = get_current_ms()
        dns_start = dns_start_at - timing.request_start
        timing.dns_start_at = dns_start_at
        timing.dns_start = dns_start
        process: ProcessLogging = ctx["process"]
        process.append(f"[{ctx['index']}] 开始DNS解析 | 主机: {params.host}")

    # 12. DNS解析完成
    async def on_dns_resolvehost_end(self, session, trace_config_ctx, params):
        """DNS解析完成时触发"""
        ctx = trace_config_ctx.trace_request_ctx
        dns_time = (get_current_ms() - ctx["dns_start"]) / 1000
        timing: RequestTiming = ctx["timing"]
        dns_end_at = get_current_ms()
        dns_end = dns_end_at - timing.dns_start_at
        timing.dns_end = dns_end
        timing.dns_end_at = dns_end_at
        process: ProcessLogging = ctx["process"]
        process.append(f"[{ctx['index']}] DNS解析完成 | 结果: {params.host} | 耗时: {dns_time:.4f}s")

    async def close_session(self):
        """关闭单例 session"""
        if self.session:
            await self.session.close()
            self.session = None
