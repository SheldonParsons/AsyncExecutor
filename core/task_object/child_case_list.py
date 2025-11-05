from typing import List


class ChildCase:

    def __init__(self, type=None, parent=None, temp_variables=None, error_strategy=None, case_name=None, case_id=None,
                 start=None, end=None, done_step_count=None, failed_step_count=None, skipped_step_count=None,
                 status=None, origin_child_steps=None, child_case_prefix=None, index=None, desc=None,
                 index_in_global_list=None):
        self.type = type
        self.id = index
        self.label = '主用例-子用例'
        self.parent = parent
        self.temp_variables = temp_variables
        self.error_strategy = error_strategy
        self.case_name = case_name
        self.case_id = case_id
        self.start = start
        self.end = end
        self.done_step_count = done_step_count
        self.failed_step_count = failed_step_count
        self.skipped_step_count = skipped_step_count
        self.status = status
        self.origin_child_steps = origin_child_steps
        self.child_case_prefix = child_case_prefix
        self.index = index
        self.desc = desc
        self.index_in_global_list = index_in_global_list

    def to_dict(self):
        return self.__dict__


class ChildCaseList:

    def __init__(self, child_case_list):
        self.list: List[ChildCase] = [ChildCase(**item) for item in child_case_list]

    def to_dict(self):
        return [item.to_dict() for item in self.list]
