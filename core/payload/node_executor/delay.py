import asyncio
from core.executor.core import StepExecutor
from core.record.utils import DelayWarningProcessObject, DelaySuccessProcessObject
from core.task_object.galobal_mapping import MultiwayTreeNode
from core.task_object.step_mapping import Delay


class DelayRunController(StepExecutor):

    def __init__(self, node: MultiwayTreeNode, in_case=False):
        super().__init__(node)
        self.in_case = in_case

    async def run(self, *args, **kwargs):
        delay_info: Delay = self.node.node.metadata
        try:
            delay = int(delay_info.delay)
        except ValueError:
            self.node.node.send_step(DelayWarningProcessObject(f"延迟时间转义失败，修正为 0 毫秒"))
            delay = 0
        if delay < 0:
            self.node.node.send_step(DelayWarningProcessObject(f"延迟时间小于0，修正为 0 毫秒"))
            delay = 0
        elif delay > 99999:
            self.node.node.send_step(DelayWarningProcessObject(f"延迟时间大于99999，修正为 0 毫秒"))
            delay = 0

        await asyncio.sleep(delay / 1000)
        self.node.node.send_step(DelaySuccessProcessObject(f"休眠 {delay} 毫秒"))
