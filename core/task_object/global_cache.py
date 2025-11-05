class GlobalCache:

    def __init__(self, origin_interface_mapping=None, origin_file_mapping=None, origin_project_env_server_mapping=None,
                 origin_project_env_variable_mapping=None,
                 origin_database_mapping=None, origin_dataset_mapping=None, origin_global_variable_mapping=None,
                 case_before_script_print_mapping=None):
        self.origin_interface_mapping = origin_interface_mapping
        self.origin_file_mapping = origin_file_mapping
        self.origin_project_env_server_mapping = origin_project_env_server_mapping
        self.origin_project_env_variable_mapping = origin_project_env_variable_mapping
        self.origin_database_mapping = origin_database_mapping
        self.origin_dataset_mapping = origin_dataset_mapping
        self.origin_global_variable_mapping = origin_global_variable_mapping
        self.case_before_script_print_mapping = case_before_script_print_mapping

    def _get_file_path_by_name(self, file_name):
        return self.origin_file_mapping[file_name]['exec_path']

    def to_dict(self):
        return self.__dict__
