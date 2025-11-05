class Case:

    def __init__(self, type=None, parent=None, id=None, name=None, before_script=None, project_id=None,
                 project_name=None, env=None, data_set=None, drive_strategy=None, loop_times=None, loop_strategy=None,
                 runtime_parameters_strategy=None, error_strategy=None, status=None, index=None, child_case=None,
                 env_variables=None, start=None, end=None, child_case_count=None):
        self.type = type
        self.parent = parent
        self.label = '主用例'
        self.id = id
        self.name = name
        self.before_script = before_script
        self.project_id = project_id
        self.project_name = project_name
        self.env = env
        self.data_set = data_set
        self.drive_strategy = drive_strategy
        self.loop_times = loop_times
        self.loop_strategy = loop_strategy
        self.runtime_parameters_strategy = runtime_parameters_strategy
        self.error_strategy = error_strategy
        self.status = status
        self.index = index
        self.child_case = child_case
        self.env_variables = env_variables
        self.start = start
        self.end = end
        self.child_case_count = child_case_count

    def to_dict(self):
        return self.__dict__


class CaseList:

    def __init__(self, case_list):
        self.data = [Case(**item) for item in case_list]

    def to_dict(self):
        return [item.to_dict() for item in self.data]
