from __future__ import annotations

from collections import deque
from typing import Union, Self, TYPE_CHECKING, TypeVar, Generic

if TYPE_CHECKING:
    from core.executor.core import RunnerExecutor

    T = TypeVar('T', bound=RunnerExecutor)
else:
    T = TypeVar('T')

from core.record.task_record import TaskRecord


class MultiwayTreeNode(Generic[T]):

    def __init__(self, parent: Union[MultiwayTreeNode, None] = None, node: RunnerExecutor = None,
                 children: deque[RunnerExecutor] = None):
        self.parent: Union[MultiwayTreeNode, None] = parent
        self.node: T = node
        self.children: deque[RunnerExecutor] = children
        self.interface_last_node: Self = None
        self.interface_last_node_result = False
        self.interface_detail_index = None

    def add_child(self, child: Union[RunnerExecutor, TaskRecord]):
        self.children.append(child)

    def set_child(self, child_list: deque[Union[RunnerExecutor, TaskRecord]]):
        self.children = child_list
