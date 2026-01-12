import asyncio
from typing import Callable

from core.customer_script.base import AsyncExecutorVariable, ContextDocument
from core.customer_script.execute import DynamicCodeExecutor
from core.payload.utils.tools import search_env
from core.record.utils import ExceptionProcessObject, InterfaceErrorFinishProcessObject
from core.task_object.step_mapping import Interface


class InterfaceRetryHandler:

    def __init__(self, interface: Interface, async_callback: Callable, node=None):
        self.timeout = int(interface.timeout)
        self.retry_strategy = str(interface.retry_strategy)
        self.retry_times = int(interface.retry_times)
        self.retry_script = str(interface.retry_script)
        self.async_callback = async_callback
        self.node = node
        self._should_next = True
        self.current_msg = ""
        self._has_retry_times = 0

    async def run(self, before_run_callback, has_next_after_run_callback, after_run_callback=lambda: None):
        for index in range(self.retry_times):
            before_run_callback()
            await self.next()
            self._has_retry_times += 1
            if not self._should_next:
                after_run_callback()
                break
            else:
                await has_next_after_run_callback(index, self.retry_times, self.current_msg)

    async def next(self):
        await self.async_callback()

    async def has_retry(self, result: bool = False, code: int = 0, raise_code: int = 0, exception=None,
                        response_details=None,send_step=None) -> bool:
        if self.retry_strategy == 'no':
            self._should_next = False
            return False
        if self.retry_strategy == 'timeout' and result is False and isinstance(exception,
                                                                               asyncio.TimeoutError) and self.retry_times > (self._has_retry_times + 1):
            self._should_next = True
            self.current_msg = "请求超时"
            return True
        elif self.retry_strategy == 'code' and result is True and self.retry_times > (self._has_retry_times + 1) and code == raise_code:
            self._should_next = True
            self.current_msg = f"响应码异常:{code}:{raise_code}"
            return True
        elif self.retry_strategy == 'script' and result is True and self.retry_times > (self._has_retry_times + 1):
            try:
                env = search_env(self.node)
                variable = AsyncExecutorVariable(self.node)
                context = ContextDocument(variable, self.node.node._print, has_response=True, env_name=env,
                                          dataset_toolkit=None, response_details=response_details)
                dynamic_code_executor = DynamicCodeExecutor().compile(code_str=self.retry_script)
                result = await dynamic_code_executor.execute(context)
                if result is False:
                    self._should_next = True
                    self.current_msg = f"重试自定义脚本判断失败"
                    return True
            except Exception as e:
                error_object = InterfaceErrorFinishProcessObject(
                    f"重试脚本异常：{e}")
                await send_step(error_object)

        self._should_next = False
        return False
