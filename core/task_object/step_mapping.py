from typing import Dict, Union, Any


class Step:
    pass


class HasChildStep(Step):
    pass


class VirtualNode:
    pass


class RealNode(Any):
    pass


class NormalStep(Step):

    def __init__(self):
        self.id = None
        self.type = None
        self.label = None
        self.check = None


class Interface(Step, RealNode):
    def __init__(self, type=None, id=None, label=None, check=None, is_raise_step=None, is_root_step=None,
                 should_raise=None, raise_code=None, status=None, parent=None, interface=None, project_id=None):
        self.type = type
        self.id = id
        self.label = label
        self.check = check
        self.is_raise_step = is_raise_step
        self.is_root_step = is_root_step
        self.should_raise = should_raise
        self.raise_code = raise_code
        self.status = status
        self.parent = parent
        self.interface = interface
        self.project_id = project_id


class Script(Step, RealNode):
    def __init__(self, type=None, id=None, check=None, is_raise_step=None, is_root_step=None, status=None, parent=None,
                 label=None, script=None):
        self.type = type
        self.id = id
        self.check = check
        self.is_raise_step = is_raise_step
        self.is_root_step = is_root_step
        self.status = status
        self.parent = parent
        self.label = label
        self.script = script


class Group(HasChildStep, RealNode):
    def __init__(self, type=None, id=None, is_raise_step=None, is_root_step=None, label=None, error_strategy=None,
                 check=None, status=None, parent=None, children=None):
        self.type = type
        self.id = id
        self.is_raise_step = is_raise_step
        self.is_root_step = is_root_step
        self.label = label
        self.error_strategy = error_strategy
        self.check = check
        self.status = status
        self.parent = parent
        self.children = children


class Database(Step, RealNode):
    def __init__(self, type=None, id=None, check=None, is_raise_step=None, is_root_step=None, status=None, parent=None,
                 label=None, params_mode=None, database_id=None, sql=None, params=None, script=None):
        self.type = type
        self.id = id
        self.check = check
        self.is_raise_step = is_raise_step
        self.is_root_step = is_root_step
        self.status = status
        self.parent = parent
        self.label = label
        self.params_mode = params_mode
        self.database_id = database_id
        self.sql = sql
        self.params = params
        self.script = script


class Case(HasChildStep, RealNode):
    def __init__(self, type=None, id=None, check=None, label=None, is_raise_step=None, is_root_step=None, status=None,
                 parent=None, project_id=None, project_name=None, env=None, error_strategy=None,
                 case_error_strategy=None, env_strategy=None,
                 runtime_parameters_strategy=None, children=None, drive_strategy=None, loop_strategy=None, times=None,
                 dataset=None, load_loop_script=None):
        self.type = type
        self.id = id
        self.check = check
        self.label = label
        self.is_raise_step = is_raise_step
        self.is_root_step = is_root_step
        self.status = status
        self.parent = parent
        self.project_id = project_id
        self.project_name = project_name
        self.env = env
        self.error_strategy = error_strategy
        self.case_error_strategy = case_error_strategy
        self.env_strategy = env_strategy
        self.runtime_parameters_strategy = runtime_parameters_strategy
        self.children = children
        self.drive_strategy = drive_strategy
        self.loop_strategy = loop_strategy
        self.times = times
        self.dataset = dataset
        self.load_loop_script = load_loop_script


class ChildStepCase(HasChildStep, VirtualNode):

    def __init__(self, type='child_step_case', id=None, check=None, label=None, is_raise_step=None, is_root_step=None,
                 status=None,
                 parent=None, project_id=None, project_name=None, error_strategy=None, children=None,
                 temp_variables=None):
        self.type = type
        self.id = id
        self.check = check
        self.label = label
        self.is_raise_step = is_raise_step
        self.is_root_step = is_root_step
        self.status = status
        self.parent = parent
        self.project_id = project_id
        self.project_name = project_name
        self.error_strategy = error_strategy
        self.temp_variables = temp_variables
        self.children = children


class ChildMultitasker(HasChildStep, VirtualNode):
    def __init__(self, type='child_multitasker', id=None, is_raise_step=None, is_root_step=None, label=None,
                 error_strategy=None, check=None,
                 status=None, parent=None,
                 children=None, temp_variables=None):
        self.type = type
        self.id = id
        self.is_raise_step = is_raise_step
        self.is_root_step = is_root_step
        self.label = label
        self.error_strategy = error_strategy
        self.check = check
        self.status = status
        self.parent = parent
        self.children = children
        self.temp_variables = temp_variables


class Multitasker(HasChildStep, RealNode):
    def __init__(self, type=None, id=None, is_raise_step=None, is_root_step=None, label=None, drive_strategy=None,
                 loop_strategy=None, error_strategy=None, check=None, times=None, dataset=None, delay=None,
                 load_loop_script=None, delay_interface=None, save_response=None, status=None, parent=None,
                 children=None):
        self.type = type
        self.id = id
        self.is_raise_step = is_raise_step
        self.is_root_step = is_root_step
        self.label = label
        self.drive_strategy = drive_strategy
        self.loop_strategy = loop_strategy
        self.error_strategy = error_strategy
        self.check = check
        self.times = times
        self.dataset = dataset
        self.delay = delay
        self.load_loop_script = load_loop_script
        self.delay_interface = delay_interface
        self.save_response = save_response
        self.status = status
        self.parent = parent
        self.children = children


class Assertion(Step, RealNode):
    def __init__(self, type=None, id=None, check=None, is_raise_step=None, is_root_step=None, status=None, parent=None,
                 label=None, key=None, value=None, pattern=None, script=None, assert_mode=None, interface_range=None,
                 interface_body_pattern=None, interface_code_pattern=None, interface_header_pattern=None,
                 interface_body_jsonpath=None, interface_body_value=None, interface_header_value=None,
                 interface_code_value=None, interface_header_key=None, interface_body_range=None, failed_desc=None,
                 success_desc=None):
        self.type = type
        self.id = id
        self.check = check
        self.is_raise_step = is_raise_step
        self.is_root_step = is_root_step
        self.status = status
        self.parent = parent
        self.label = label
        self.key = key
        self.value = value
        self.pattern = pattern
        self.script = script
        self.assert_mode = assert_mode
        self.interface_range = interface_range
        self.interface_body_pattern = interface_body_pattern
        self.interface_code_pattern = interface_code_pattern
        self.interface_header_pattern = interface_header_pattern
        self.interface_body_jsonpath = interface_body_jsonpath
        self.interface_body_value = interface_body_value
        self.interface_header_value = interface_header_value
        self.interface_code_value = interface_code_value
        self.interface_header_key = interface_header_key
        self.interface_body_range = interface_body_range
        self.failed_desc = failed_desc
        self.success_desc = success_desc


class Empty(Step, RealNode):
    def __init__(self, type=None, id=None, check=None, is_raise_step=None, is_root_step=None, status=None, parent=None,
                 label=None):
        self.type = type
        self.id = id
        self.check = check
        self.is_raise_step = is_raise_step
        self.is_root_step = is_root_step
        self.status = status
        self.parent = parent
        self.label = label


class Error(Step, RealNode):
    def __init__(self, type=None, id=None, check=None, is_raise_step=None, is_root_step=None, status=None, parent=None,
                 label=None, key=None, value=None, pattern=None, script=None, error_mode=None):
        self.type = type
        self.id = id
        self.check = check
        self.is_raise_step = is_raise_step
        self.is_root_step = is_root_step
        self.status = status
        self.parent = parent
        self.label = label
        self.key = key
        self.value = value
        self.pattern = pattern
        self.script = script
        self.error_mode = error_mode


class Delay(Step, RealNode):
    def __init__(self, type=None, id=None, check=None, is_raise_step=None, is_root_step=None, status=None, parent=None,
                 label=None, delay=None):
        self.type = type
        self.id = id
        self.check = check
        self.is_raise_step = is_raise_step
        self.is_root_step = is_root_step
        self.status = status
        self.parent = parent
        self.label = label
        self.delay = delay


class If(HasChildStep, RealNode):
    def __init__(self, type=None, id=None, is_raise_step=None, is_root_step=None, label=None, error_strategy=None,
                 check=None, status=None, parent=None, key=None, value=None, pattern=None, script=None, if_mode=None,
                 children=None):
        self.type = type
        self.id = id
        self.is_raise_step = is_raise_step
        self.is_root_step = is_root_step
        self.label = label
        self.error_strategy = error_strategy
        self.check = check
        self.status = status
        self.parent = parent
        self.key = key
        self.value = value
        self.pattern = pattern
        self.script = script
        self.if_mode = if_mode
        self.children = children


class StepDispatch:

    def __init__(self, **kwargs):
        self._type = kwargs.get("type", None)
        self.kwargs = kwargs

    def __call__(self):
        if self._type == 'interface':
            return Interface(**self.kwargs)
        if self._type == 'script':
            return Script(**self.kwargs)
        if self._type == 'group':
            return Group(**self.kwargs)
        if self._type == 'database':
            return Database(**self.kwargs)
        if self._type == 'case':
            return Case(**self.kwargs)
        if self._type == 'multitasker':
            return Multitasker(**self.kwargs)
        if self._type == 'assertion':
            return Assertion(**self.kwargs)
        if self._type == 'empty':
            return Empty(**self.kwargs)
        if self._type == 'if':
            return If(**self.kwargs)
        if self._type == 'error':
            return Error(**self.kwargs)
        if self._type == 'delay':
            return Delay(**self.kwargs)
        return None


class StepMapping:
    def __init__(self, step_mapping):
        self.mapping: Dict[
            int, Dict[str, Union[Interface, Script, Group, Database, Case, Multitasker, Assertion, Empty, If,]]] = {
            name: {step_name: StepDispatch(**step_item)() for step_name, step_item in item.items()} for name, item in
            step_mapping.items()}

    def to_dict(self):
        return {name: {step_name: step_item.__dict__ for step_name, step_item in item.items()} for
                name, item in self.mapping.items()}
