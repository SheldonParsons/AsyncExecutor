import ast
import asyncio
import sys
import traceback
from enum import Enum
from typing import List, Union

from core.customer_script.base import FORBIDDEN_MODULES, ContextDocument, DEFAULT_RECURSION_LIMIT, \
    PROXY_ASYNC_FUNCTION
from core.customer_script._exception import ForbiddenImportException, CompilerException, \
    RecursionErrorException, CodeRuntimeException
from global_object.signal import MemoryResourceLimitExceededError


class ForbiddenImportEnum(str, Enum):
    IMPORT = "import"
    IMPORT_FROM = "from"
    DYNAMIC_IMPORT = "__import__"
    TIME_SLEEP = "time.sleep()"


class Violation:

    def __init__(self, type=None, module=None, line_number=None):
        self.type: ForbiddenImportEnum = type
        self.module = module
        self.line_number = line_number


class SecurityVisitor(ast.NodeVisitor):
    def __init__(self, forbidden_modules: List[str]):
        self.forbidden_modules = forbidden_modules
        self.violations = []

    def visit_Import(self, node):
        for alias in node.names:
            if alias.name in self.forbidden_modules:
                self.violations.append(
                    Violation(type=ForbiddenImportEnum.IMPORT, module=alias.name, line_number=node.lineno))
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module in self.forbidden_modules:
            self.violations.append(
                Violation(type=ForbiddenImportEnum.IMPORT_FROM, module=node.module, line_number=node.lineno))
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id == ForbiddenImportEnum.DYNAMIC_IMPORT.value:
            if node.args and isinstance(node.args[0], ast.Str):
                module_name = node.args[0].s
                if module_name in self.forbidden_modules:
                    self.violations.append(
                        Violation(type=ForbiddenImportEnum.DYNAMIC_IMPORT, module=module_name,
                                  line_number=node.lineno))

        if (
                isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "time"
                and node.func.attr == "sleep"
        ):
            self.violations.append(
                Violation(type=ForbiddenImportEnum.TIME_SLEEP, module="time.sleep", line_number=node.lineno)
            )

        self.generic_visit(node)


class DynamicCodeExecutor:
    def __init__(self):
        self.forbidden_modules = FORBIDDEN_MODULES
        self.context = None
        self.compile_code = None

    class RecursionLimitContext:
        def __enter__(self):
            self.original_limit = sys.getrecursionlimit()
            sys.setrecursionlimit(DEFAULT_RECURSION_LIMIT)

        def __exit__(self, exc_type, exc_val, exc_tb):
            sys.setrecursionlimit(self.original_limit)

    def check_code_security(self, code_str: str):
        """检查代码是否包含禁止的导入"""
        try:
            tree = ast.parse(code_str)

            # 修改后的安全访问器，忽略未定义名称
            class SafeSecurityVisitor(SecurityVisitor):
                def visit_Name(self, node):
                    # 忽略所有未定义的变量名（将在运行时提供）
                    pass

                def visit_Attribute(self, node):
                    # 忽略属性访问（如 at.global）
                    self.generic_visit(node)

            visitor = SafeSecurityVisitor(self.forbidden_modules)
            visitor.visit(tree)
            if len(visitor.violations) > 0:
                violation: Violation = visitor.violations.pop()
                if violation.type == ForbiddenImportEnum.TIME_SLEEP:
                    error_msg = "代码包含禁止使用的模块:\n"
                    error_msg += f"- 行 {violation.line_number}: {violation.type.value}，如果您确实需要，请替换为await asyncio.sleep\n"
                else:
                    error_msg = "代码包含禁止的导入:\n"
                    error_msg += f"- 行 {violation.line_number}: {violation.type.value} {violation.module}\n"
                raise ForbiddenImportException(error_msg)
        except SyntaxError as e:
            e.lineno = e.lineno - 1
            if '<unknown>' not in str(e):
                error_line = e.text.strip() if e.text else "<无法获取该行代码>"
                error_msg = "语法错误:\n"
                error_msg += f"- 行 {e.lineno}: {type(e).__name__} {str(e)}\n"
                error_msg += f"- 错误代码： {error_line}"
                raise CompilerException(error_msg)

    def compile(self, code_str: str, script_source=False) -> Union["DynamicCodeExecutor", str]:
        self.check_code_security(code_str)
        wrapped_code = f"async def {PROXY_ASYNC_FUNCTION}():\n"
        for line in code_str.splitlines():
            wrapped_code += f"    {line}\n"
        wrapped_code += f"    pass\n"
        try:
            self.compile_code = compile(wrapped_code, "<dynamic>", "exec", optimize=0)
            if not script_source:
                return self
            return wrapped_code
        except NameError:
            # 忽略名称未定义错误（运行时变量）
            return self
        except SyntaxError as e:
            e.lineno = e.lineno - 1
            if "invalid syntax" in str(e):
                return self
            error_msg = "语法错误:\n"
            error_msg += f"- 行 {e.lineno}: SyntaxError {str(e.text)}"
            error_msg += f"- 错误原因 {str(e)}\n"
            raise CompilerException(error_msg)
        except Exception as e:
            raise CompilerException(e)

    async def execute(self, context: ContextDocument = None, compile_code: str = None):
        self.context = context.to_dict()
        if compile_code:
            self.compile_code = compile_code
        if self.compile_code is None:
            raise RuntimeError("代码未编译，或编译失败，无法执行")
        with self.RecursionLimitContext():
            exec(self.compile_code, self.context)
            try:
                return await self.context[PROXY_ASYNC_FUNCTION]()
            except MemoryResourceLimitExceededError as e:
                raise MemoryResourceLimitExceededError(f"内存溢出：{e}，请优化您的代码")
            except RecursionError:
                raise RecursionErrorException(f"递归深度限制：{DEFAULT_RECURSION_LIMIT}，请优化您的代码")
            except Exception as e:
                traceback.print_exc()
                exc_type, exc_value, exc_tb = sys.exc_info()
                tb = traceback.extract_tb(exc_tb).pop()
                exe_str = f"错误行号：{tb.lineno - 1},函数：自定义函数:\n"
                exe_str += f"异常类型：{exc_type.__name__}, 错误信息：{e}"
                raise CodeRuntimeException(exe_str)
