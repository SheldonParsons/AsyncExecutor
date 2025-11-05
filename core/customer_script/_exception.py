import traceback


class ActionException(Exception):

    def get_traceback(self):
        return traceback.format_exc()

    def to_string(self):
        return str(self)


class CodeException(ActionException):
    pass


class CodeRuntimeException(CodeException):
    pass


class ForbiddenImportException(CodeException):
    pass


class ForbiddenCallException(CodeException):
    pass


class CallInnerFunctionException(CodeException):
    pass


class RecursionErrorException(CodeException):
    pass


class TimeoutException(CodeException):
    pass


class CompilerException(CodeException):
    pass
