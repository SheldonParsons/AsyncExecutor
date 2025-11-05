from enum import Enum


class ExecType(str, Enum):
    DJANGO = "django"
    REMOTE = "remote"


class RunningModeEnum(str, Enum):
    CONCURRENTLY = "concurrent"
    SEQUENTIALLY = "sequential"


class StatusEnum(str, Enum):
    PENDING = "pending"  # 等待运行
    END = "end"  # 正常结束
    ERROR_END = "error_end"  # 异常结束
    USER_END = "user_end"  # 用户手工停止


class BodyCurrentType(str, Enum):
    NONE = "none"
    FORM_DATA = "form-data"
    X_WWW_FORM_URLENCODED = "x-www-form-urlencoded"
    JSON = 'json'
    RAW = 'raw'


class InterfaceDataTypeEnum(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    NUMBER = "number"
    ARRAY = "array"
    NULL = "null"
    FILES = "files"
    OBJECT = "object"


class RecordMessageTypeEnum(str, Enum):
    STATUS = 'status'
    PROCESS = 'process'


class ExtractSourceType(int, Enum):
    RESPONSE_BODY = 0
    RESPONSE_HEADER = 1
    RESPONSE_COOKIE = 2
    WASTE_TIME = 3


class RangeType(int, Enum):
    WHOLE_BODY = 0
    JSONPATH = 1
    REGEXP = 2
    XPATH = 3


class ExtractVariableType(int, Enum):
    TEMP = 0
    ENV = 1
    GLOBAL = 2


class StepTypeEnum(str, Enum):
    INTERFACE = 'interface'
    ASSERTION = 'assertion'
    SCRIPT = 'script'
    CASE = 'case'
    GROUP = 'group'
    MULTITASKER = 'multitasker'
    DATABASE = 'database'
    IF = 'if'
    EMPTY = 'empty'
    ERROR = 'error'
    CHILD_MULTITASKER = 'child_multitasker'
    CHILD_STEP_CASE = 'child_step_case'


class RedisProcessTypeEnum(str, Enum):
    SYSTEM = "system"
    SYSTEM_EXCEPTION = "system_exception"
    ASSERTION_EXCEPTION = "assertion_exception"
    INTERFACE_EXCEPTION = "interface_exception"
    DATABASE_EXCEPTION = "database_exception"
    VARIABLE_EXCEPTION = "variable_exception"
    VARIABLE_WARNING = "variable_warning"
    ACTION_SCRIPT_PRINT = "action_script_print"
    ACTION_SCRIPT = "action_script"
    ACTION_SLEEP = "action_sleep"
    ACTION_EXTRACT = "action_extract"
    ACTION_WARNING = "action_warning"
    INTERFACE_SUCCESS_FINISHED = "interface_success_finished"
    INTERFACE_ERROR_FINISHED = "interface_error_finished"
    INTERFACE_WARNING = "interface_warning"
    INTERFACE_INFO = "interface_info"
    CASE_DRIVE = "case_drive"
    MULTITASKER_DRIVE = "multitasker_drive"
    ASSERTION_SUCCESS = "assertion_success"
    ASSERTION_FAILED = "assertion_failed"
    IF_SUCCESS = "if_success"
    IF_FAILED = "if_failed"
    ERROR_FAILED = "error_failed"
    DELAY_WARNING = "delay_warning"
    DELAY_SUCCESS = "delay_success"
    VARIABLE_GET = "variable_get"
    VARIABLE_SET = "variable_set"
    STEP_RUNNING = "step_running"
    STEP_SKIPPED = "step_skipped"
    STEP_ERROR = "step_error"


class NodeStatusEnum(str, Enum):
    PENDING = "mid_pending"  # 中间状态，最终会被坍缩到某个最终状态
    RUNNING = "mid_running"  # 中间状态
    SKIPPED = "end_skipped"  # 最终状态，该步骤被跳过
    SKIPPED_CHILD = "end_skipped_child"
    END = "end_normal"  # 最终状态，该步骤被执行，没有发生错误
    ERROR = "end_error"  # 最终状态，该步骤被执行，但发生了错误
    ERROR_CHILD = "end_error_child"
    CONDITIONAL = "end_conditional"  # 最终状态，该步骤被执行，但发生了可预期的条件式跳过，将指导子步骤进行跳过


class NodeResultEnum(str, Enum):
    UNKNOWN = "mid_unknown"  # 中间结果，该步骤的结果还未被计算出来
    SUCCESS = "end_success"  # 最终结果，它和它的子步骤都成功被执行，且没有出现异常
    ERROR_SELF = "end_error_self"  # 最终结果，它自身出现了异常
    ERROR_CHILD = "end_error_child"  # 最终结果，它的子节点出现了异常
    SKIPPED_SELF = "end_skipped_self"  # 最终结果，它自身被跳过
    SKIPPED_CHILD = "end_skipped_child"  # 最终结果，它的子节点出现了跳过


class InnerCaseErrorStrategyEnum(str, Enum):
    CURRENT_STEP = 'current_step'  # 跳过当前步骤
    REF_CASE_INNER = 'ref_case_inner'  # 由引用用例内部抉择
    REF_CHILD_CASE = 'ref_child_case'  # 结束引用子用例
    REF_CASE = 'ref_case'  # 结束引用用例
    CURRENT_CASE = 'current_case'  # 结束子用例
    CASE = 'case'  # 结束用例
    RAISE = 'raise'  # 交由上级处理
    TASK = 'task'  # 结束任务


class CaseErrorStrategyEnum(str, Enum):
    CURRENT_STEP = 'current_step'  # 跳过当前步骤
    CURRENT_CASE = 'current_case'  # 结束当前用例
    CASE = 'case'  # 结束用例
    RAISE = 'raise'  # 交由上级处理
    TASK = 'task'  # 结束任务


class TaskErrorStrategyEnum(str, Enum):
    CURRENT_STEP = 'current_step'  # 跳过当前步骤
    CURRENT_CASE = 'current_case'  # 结束当前用例
    CASE = 'case'  # 结束用例
    TASK = 'task'  # 结束任务


class ErrorStrategyMixinEnum(str, Enum):
    CURRENT_STEP = 'current_step'  # 跳过当前步骤 1
    CURRENT_CASE = 'current_case'  # 结束当前用例 1
    CASE = 'case'  # 结束用例 1
    CURRENT_MULTITASKER = 'current_multitasker'  # 结束子执行器 1
    MULTITASKER = 'multitasker'  # 结束执行器 1
    REF_CASE_INNER = 'ref_case_inner'  # 由引用用例内部抉择 -
    REF_CHILD_CASE = 'ref_child_case'  # 结束引用子用例 1
    REF_CASE = 'ref_case'  # 结束引用用例 1
    RAISE = 'raise'  # 交由上级处理 -
    TASK = 'task'  # 结束任务 1


class MultitaskerErrorStrategyEnum(str, Enum):
    CURRENT_STEP = 'current_step'  # 跳过当前步骤
    CURRENT_MULTITASKER = 'current_multitasker'  # 结束子执行器
    MULTITASKER = 'multitasker'  # 结束执行器
    CURRENT_CASE = 'current_case'  # 结束子用例
    CASE = 'case'  # 结束用例
    RAISE = 'raise'  # 交由上级处理
    TASK = 'task'  # 结束任务


class RedisDetailTypeEnum(str, Enum):
    INTERFACE_SUCCESS = "interface_success"
    INTERFACE_ERROR = "interface_error"


class AssertionModeEnum(str, Enum):
    LAST_INTERFACE = 'interface'
    FAST = 'fast'
    SCRIPT = 'script'


class IfModeEnum(str, Enum):
    FAST = 'fast'
    SCRIPT = 'script'


class AssertionInterfaceRangeEnum(str, Enum):
    BODY = 'body'
    HEADER = 'header'
    CODE = 'code'


class AssertionPatternEnum(str, Enum):
    EQ = 'eq'
    NEQ = 'neq'
    EXIST = 'exist'
    NO_EXIST = 'noexist'
    GT = 'gt'
    GTE = 'gte'
    LT = 'lt'
    LTE = 'lte'
    CONTAINS = 'contains'
    NOT_CONTAINS = 'notContains'
    REGEX = 'regex'
    INSET = 'inset'
    UN_INSET = 'uninset'
