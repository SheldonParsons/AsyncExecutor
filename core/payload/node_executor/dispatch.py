from core.executor.core import Executor
from core.payload.node_executor.assertion import AssertionRunController
from core.payload.node_executor.case import CaseRunController
from core.payload.node_executor.database import DatabaseRunController
from core.payload.node_executor.delay import DelayRunController
from core.payload.node_executor.error_exec import ErrorRunController
from core.payload.node_executor.if_exec import IfRunController
from core.payload.node_executor.interface import InterfaceRunController
from core.payload.node_executor.multitasker import MultitaskerRunController
from core.payload.node_executor.script import ScriptRunController


class EmptyExecutor(Executor):

    def __init__(self, *args, **kwargs):
        pass

    async def run(self):
        pass


class ExecutorRouter:

    def __call__(self, t: str):
        return {
            "case": CaseRunController,
            "multitasker": MultitaskerRunController,
            "interface": InterfaceRunController,
            "assertion": AssertionRunController,
            'database': DatabaseRunController,
            'script': ScriptRunController,
            'if': IfRunController,
            "error": ErrorRunController,
            "delay": DelayRunController
        }.get(t, EmptyExecutor)


ExecutorCaller = ExecutorRouter()
