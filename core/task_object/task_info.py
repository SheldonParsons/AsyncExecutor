class TaskInfo:

    def __init__(self, type=None, parent=None, id=None, hex_index=None, name=None, project_id=None, project_name=None,
                 range_type=None,
                 use_same_env=None, env=None, loop_strategy=None, error_strategy=None, status=None, cron_job=None,
                 cron_expression=None, rpc_method=None, record_level=None):
        self.type = type
        self.parent = parent
        self.id = id
        self.label = '主任务'
        self.hex_index = hex_index
        self.name = name
        self.project_id = project_id
        self.project_name = project_name
        self.range_type = range_type
        self.use_same_env = use_same_env
        self.env = env
        self.loop_strategy = loop_strategy
        self.error_strategy = error_strategy
        self.status = status
        self.cron_job = cron_job
        self.cron_expression = cron_expression
        self.rpc_method = rpc_method
        self.record_level = record_level
        self.error_info = ""

    def to_dict(self):
        return self.__dict__
