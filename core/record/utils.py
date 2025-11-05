import json
from abc import ABC, abstractmethod
from typing import Any, Union, List

from core.enums.executor import RedisProcessTypeEnum, RedisDetailTypeEnum
from core.payload.utils.tools import get_current_ms


class JsonDetail(ABC):
    def __init__(self, type: str = RedisDetailTypeEnum.INTERFACE_SUCCESS.value, index: str = "",
                 data: dict[str, dict] = None):
        self.type = type
        self.index = index
        self.data: dict[str, dict] = data

    @abstractmethod
    def to_dict(self):
        pass


class StepDetail(JsonDetail):

    def to_dict(self):
        return {
            "type": self.type,
            "index": self.index,
        }


class CoreExecReturn:

    def __init__(self, parent_process_list=None, child_case_process_list=None, summary_process_list=None, result=None):
        self.parent_process_list: List[ProcessObject] = parent_process_list or []
        self.child_case_process_list: List[ProcessObject] = child_case_process_list or []
        self.summary_process_list: List[ProcessObject] = summary_process_list or []
        self.result = result


class ProcessObject:

    def __init__(self, type=RedisProcessTypeEnum.SYSTEM.value, desc="",
                 detail: Union[None, JsonDetail] = None, position_list=None, other_info=None):
        self.type = type
        self.desc = desc
        self.detail: Any = detail
        self.time = get_current_ms()
        self.position_list = position_list
        self.other_info = other_info

    def set_other_info(self, other_info):
        self.other_info = other_info

    def set_position_list(self, position_list):
        self.position_list = position_list

    def to_json(self):
        return json.dumps({
            "type": self.type,
            "desc": self.desc,
            "detail": self.detail.to_dict() if self.detail else None,
            "position_list": self.position_list,
            "times": 0,
            "time": self.time
        }, ensure_ascii=False)


class ExceptionObject(ProcessObject):
    pass


class ExceptionProcessObject(ExceptionObject):
    def __init__(self, desc="", type=RedisProcessTypeEnum.SYSTEM_EXCEPTION.value,
                 detail: Union[None, JsonDetail] = None, raise_object=None):
        super().__init__(type=type, desc=desc, detail=detail)
        self.raise_object = raise_object


class StepRunningProcessObject(ProcessObject):
    def __init__(self, desc="", type=RedisProcessTypeEnum.STEP_RUNNING.value,
                 detail: Union[None, JsonDetail] = None):
        super().__init__(type=type, desc=desc, detail=detail)


class StepSkippedProcessObject(ProcessObject):
    def __init__(self, desc="", type=RedisProcessTypeEnum.STEP_SKIPPED.value,
                 detail: Union[None, JsonDetail] = None):
        super().__init__(type=type, desc=desc, detail=detail)


class AssertionExceptionProcessObject(ExceptionProcessObject):
    def __init__(self, desc="", type=RedisProcessTypeEnum.ASSERTION_EXCEPTION.value,
                 detail: Union[None, JsonDetail] = None):
        super().__init__(type=type, desc=desc, detail=detail)


class DatabaseExceptionProcessObject(ExceptionProcessObject):
    def __init__(self, desc="", type=RedisProcessTypeEnum.DATABASE_EXCEPTION.value,
                 detail: Union[None, JsonDetail] = None):
        super().__init__(type=type, desc=desc, detail=detail)


class CaseProcessObject(ProcessObject):
    def __init__(self, desc="", type=RedisProcessTypeEnum.CASE_DRIVE.value,
                 detail: Union[None, JsonDetail] = None):
        super().__init__(type=type, desc=desc, detail=detail)


class MultitaskerProcessObject(ProcessObject):
    def __init__(self, desc="", type=RedisProcessTypeEnum.MULTITASKER_DRIVE.value,
                 detail: Union[None, JsonDetail] = None):
        super().__init__(type=type, desc=desc, detail=detail)


class ScriptPrintProcessObject(ProcessObject):
    def __init__(self, desc="", type=RedisProcessTypeEnum.ACTION_SCRIPT_PRINT.value,
                 detail: Union[None, JsonDetail] = None):
        super().__init__(type=type, desc=desc, detail=detail)


class ActionSleepProcessObject(ProcessObject):
    def __init__(self, desc="", type=RedisProcessTypeEnum.ACTION_SLEEP.value, detail: Union[None, JsonDetail] = None):
        super().__init__(type=type, desc=desc, detail=detail)


class ActionScriptProcessObject(ProcessObject):
    def __init__(self, desc="", type=RedisProcessTypeEnum.ACTION_SCRIPT.value, detail: Union[None, JsonDetail] = None):
        super().__init__(type=type, desc=desc, detail=detail)


class ActionExtractProcessObject(ProcessObject):
    def __init__(self, desc="", type=RedisProcessTypeEnum.ACTION_EXTRACT.value, detail: Union[None, JsonDetail] = None):
        super().__init__(type=type, desc=desc, detail=detail)


class ActionWarningProcessObject(ProcessObject):
    def __init__(self, desc="", type=RedisProcessTypeEnum.ACTION_WARNING.value, detail: Union[None, JsonDetail] = None):
        super().__init__(type=type, desc=desc, detail=detail)


class AssertionSuccessProcessObject(ProcessObject):
    def __init__(self, desc="", type=RedisProcessTypeEnum.ASSERTION_SUCCESS.value,
                 detail: Union[None, JsonDetail] = None):
        super().__init__(type=type, desc=desc, detail=detail)


class AssertionFailedProcessObject(ProcessObject):
    def __init__(self, desc="", type=RedisProcessTypeEnum.ASSERTION_FAILED.value,
                 detail: Union[None, JsonDetail] = None):
        super().__init__(type=type, desc=desc, detail=detail)


class InterfaceSuccessFinishProcessObject(ProcessObject):
    def __init__(self, desc="", type=RedisProcessTypeEnum.INTERFACE_SUCCESS_FINISHED.value,
                 detail: Union[None, JsonDetail] = None):
        super().__init__(type=type, desc=desc, detail=detail)


class InterfaceErrorFinishProcessObject(ProcessObject):
    def __init__(self, desc="", type=RedisProcessTypeEnum.INTERFACE_ERROR_FINISHED.value,
                 detail: Union[None, JsonDetail] = None):
        super().__init__(type=type, desc=desc, detail=detail)


class InterfaceExceptionProcessObject(ExceptionProcessObject):
    def __init__(self, desc="", type=RedisProcessTypeEnum.INTERFACE_EXCEPTION.value,
                 detail: Union[None, JsonDetail] = None):
        super().__init__(type=type, desc=desc, detail=detail)


class InterfaceWarningProcessObject(ProcessObject):
    def __init__(self, desc="", type=RedisProcessTypeEnum.INTERFACE_WARNING.value,
                 detail: Union[None, JsonDetail] = None):
        super().__init__(type=type, desc=desc, detail=detail)


class IfSuccessProcessObject(ProcessObject):
    def __init__(self, desc="", type=RedisProcessTypeEnum.IF_SUCCESS.value,
                 detail: Union[None, JsonDetail] = None):
        super().__init__(type=type, desc=desc, detail=detail)


class IfFailedProcessObject(ProcessObject):
    def __init__(self, desc="", type=RedisProcessTypeEnum.IF_FAILED.value,
                 detail: Union[None, JsonDetail] = None):
        super().__init__(type=type, desc=desc, detail=detail)


class ErrorFailedProcessObject(ProcessObject):
    def __init__(self, desc="", type=RedisProcessTypeEnum.ERROR_FAILED.value,
                 detail: Union[None, JsonDetail] = None):
        super().__init__(type=type, desc=desc, detail=detail)


class DelayWarningProcessObject(ProcessObject):
    def __init__(self, desc="", type=RedisProcessTypeEnum.DELAY_WARNING.value,
                 detail: Union[None, JsonDetail] = None):
        super().__init__(type=type, desc=desc, detail=detail)


class DelaySuccessProcessObject(ProcessObject):
    def __init__(self, desc="", type=RedisProcessTypeEnum.DELAY_SUCCESS.value,
                 detail: Union[None, JsonDetail] = None):
        super().__init__(type=type, desc=desc, detail=detail)


class VariableSetProcessObject(ProcessObject):
    def __init__(self, desc="", type=RedisProcessTypeEnum.VARIABLE_SET.value,
                 detail: Union[None, JsonDetail] = None):
        super().__init__(type=type, desc=desc, detail=detail)


class VariableGetProcessObject(ProcessObject):
    def __init__(self, desc="", type=RedisProcessTypeEnum.VARIABLE_GET.value,
                 detail: Union[None, JsonDetail] = None):
        super().__init__(type=type, desc=desc, detail=detail)


class VariableWarningProcessObject(ProcessObject):
    def __init__(self, desc="", type=RedisProcessTypeEnum.VARIABLE_WARNING.value,
                 detail: Union[None, JsonDetail] = None):
        super().__init__(type=type, desc=desc, detail=detail)


class VariableExceptionProcessObject(ProcessObject):
    def __init__(self, desc="", type=RedisProcessTypeEnum.VARIABLE_EXCEPTION.value,
                 detail: Union[None, JsonDetail] = None):
        super().__init__(type=type, desc=desc, detail=detail)
