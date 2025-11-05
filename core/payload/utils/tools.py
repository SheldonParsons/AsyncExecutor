import copy
import os
import time
from typing import Union

from core.customer_script.dataset_object import DataSet
from core.enums.executor import RunningModeEnum


async def run_loop_strategy(loop_target=None, context=None, executors=None):
    if loop_target.loop_strategy == RunningModeEnum.SEQUENTIALLY.value:
        return await context.run_sequentially(executors)
    elif loop_target.loop_strategy == RunningModeEnum.CONCURRENTLY.value:
        return await context.run_concurrently(executors)
    return None


def search_env(node, has_found_case_node=False):
    if node.node.metadata.type == 'case' and has_found_case_node is False:
        if node.node.metadata.env_strategy == 'self_case':
            return node.node.metadata.env
        else:
            return search_env(node.parent, True)
    elif node.node.metadata.type == 'main_case':
        return node.node.metadata.env
    else:
        return search_env(node.parent, has_found_case_node)


def process_script_value(value) -> Union[list, int]:
    MAX_GENERATE_LENGTH = int(os.getenv("MAX_GENERATE_LENGTH"))
    if isinstance(value, DataSet):
        data = value.get_data()
        if isinstance(data, list) and len(data) > MAX_GENERATE_LENGTH:
            return data[:MAX_GENERATE_LENGTH]
        return data

    try:
        number = abs(int(value))
        return min(number, MAX_GENERATE_LENGTH)
    except (ValueError, TypeError):
        pass

    try:
        length = len(value)
        return min(length, MAX_GENERATE_LENGTH)
    except TypeError:
        pass

    return 1


class PositionItem:

    def __init__(self, type="", index: int = None, label: str = None):
        self.type = type
        self.index = index
        self.label = label

    def to_dict(self):
        return self.__dict__


class StaticPathIndex:

    def __init__(self, record_index=None, task=None, case=None, child_case=None, parent_step=None, step=None,
                 parent_step_name=None, step_name=None, case_name=None, position_list=None, case_index=None):
        self.record_index = None
        self.task = task
        self.case = case
        self.case_index = case_index
        self.child_case = child_case
        self.step = step
        self.parent_step = parent_step
        self.parent_step_name = parent_step_name
        self.step_name = step_name
        self.case_name = case_name
        self.position_list = position_list or []

    def to_dict(self):
        return self.__dict__

    def add_position(self, position: dict):
        self.position_list.append(position)

    def copy(self):
        spi = StaticPathIndex(record_index=self.record_index, task=self.task, case=self.case,
                              case_index=self.case_index,
                              child_case=self.child_case, parent_step=self.parent_step, step=self.step,
                              parent_step_name=self.parent_step_name, step_name=self.step_name,
                              case_name=self.case_name)
        spi.position_list = copy.deepcopy(self.position_list)
        return spi


def get_current_ms():
    return int(time.time() * 1000)
