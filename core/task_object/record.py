class Record:

    def __init__(self, id=None, record_backup_index=None, run_source=None, hex_index=None, start_at=None, status=None,
                 case_count=None, child_case_count=None, exec_user=None, task=None):
        self.id = id
        self.record_backup_index = record_backup_index
        self.run_source = run_source
        self.hex_index = hex_index
        self.start_at = start_at
        self.end_at = 0
        self.status = status
        self.case_count = case_count
        self.child_case_count = child_case_count
        self.exec_user = exec_user
        self.done_child_case_count = 0
        self.task = task

    def to_dict(self):
        return self.__dict__
