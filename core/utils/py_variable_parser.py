import json
import re
from collections import defaultdict
from enum import Enum
from typing import Dict, List, Union

from core.utils.mock_func import MockFuncStaticFuncsMixin
from core.utils.pipeline_func import PipelineFuncStaticFuncsMixin


class PipelineStep:
    def __init__(self, name: str, args: List[str]):
        self.name = name
        self.args = args

    def to_dict(self):
        return {"name": self.name, "args": self.args}


class MockParseResult:
    def __init__(self):
        self.name = ""
        self.type = "mock"
        self.mock_args: List[str] = []
        self.pipelines: List[PipelineStep] = []

    def to_dict(self):
        return {
            "name": self.name,
            "type": self.type,
            "args": self.mock_args if self.type == "mock" else [],
            "pipelines": [step.to_dict() for step in self.pipelines]
        }


class DoubleParseResult:
    def __init__(self):
        self.name = ""
        self.type = "double"
        self.pipelines: List[PipelineStep] = []

    def to_dict(self):
        return {
            "name": self.name,
            "type": self.type,
            "pipelines": [step.to_dict() for step in self.pipelines]
        }


class StaticParseResult:
    def __init__(self):
        self.name = ""
        self.type = "static"
        self.pipelines: List[PipelineStep] = []

    def to_dict(self):
        return {
            "name": self.name,
            "type": self.type,
            "pipelines": [step.to_dict() for step in self.pipelines]
        }


class VariableParser:
    def __init__(self):
        self.parse_results: Dict[str, Union[MockParseResult, DoubleParseResult, StaticParseResult]] = {}
        self.double_pattern = re.compile(r'\{\{(.*?)\}\}')
        self.mock_pattern = re.compile(r'\{%\s*mock([^%]+)\s*%\}', re.IGNORECASE)
        self.func_pattern = re.compile(r'\s*(\w+)\(([^)]*)\)\s*')

    def split(self, s: str, delimiter: str, trim_quotes=False) -> List[str]:
        tokens = []
        token = []
        in_quote = False

        for c in s:
            if c == "'":
                if trim_quotes:
                    continue
                in_quote = not in_quote
            elif c == delimiter and not in_quote:
                tokens.append(''.join(token).strip())
                token = []
            else:
                token.append(c)

        # 注意：即使 token 为空，也要加入（例如结尾是逗号）
        tokens.append(''.join(token).strip())
        return tokens

    def parse_function(self, s: str) -> Union[PipelineStep, None]:
        match = self.func_pattern.fullmatch(s)
        if not match:
            return None

        name = match.group(1)
        args_str = match.group(2).strip()
        args = self.split(args_str, ',', True) if args_str else []
        return PipelineStep(name, args)

    def process_static_brace(self, origin: str, content: str):
        if origin in self.parse_results:
            return
        parts = self.split(content, '|')
        if not parts:
            return

        result = StaticParseResult()
        result.name = parts[0]

        for part in parts[1:]:
            if func := self.parse_function(part):
                result.pipelines.append(func)

        self.parse_results[origin] = result

    def process_double_brace(self, origin: str, content: str):
        if origin in self.parse_results:
            return
        parts = self.split(content, '|')
        if not parts:
            return

        result = DoubleParseResult()
        result.name = parts[0]

        for part in parts[1:]:
            if func := self.parse_function(part):
                result.pipelines.append(func)

        self.parse_results[origin] = result

    def process_mock_block(self, origin: str, content: str):
        if origin in self.parse_results:
            return

        cleaned = re.sub(r'^\s*mock\s*|\s*$', '', content)
        parts = self.split(cleaned, '|')
        if not parts:
            return

        result = MockParseResult()
        mock_args = self.split(parts[0], ',', True)
        if mock_args:
            result.name = mock_args[0]
            result.mock_args = mock_args[1:]

        for part in parts[1:]:
            if func := self.parse_function(part):
                result.pipelines.append(func)
        self.parse_results[origin] = result

    def parse(self, input_str: str) -> Dict[str, Union[MockParseResult, DoubleParseResult, StaticParseResult]]:
        self.parse_results.clear()

        # 解析双括号
        for match in self.double_pattern.finditer(input_str):
            origin = match.group(0)
            content = match.group(1)
            if content.startswith("'"):
                self.process_static_brace(origin, content)
            else:
                self.process_double_brace(origin, content)

        # 解析mock块
        for match in self.mock_pattern.finditer(input_str):
            origin = match.group(0)
            content = match.group(1)
            self.process_mock_block(origin, content)
        return self.parse_results


class ChangeModeEnum(str, Enum):
    CHANGE_EVERY_TIME = "change_every_time"
    JUST_ONCE = "just_once"


class ExchangeToller:

    def __init__(self, text: str, variable_mapping: dict = None, mode=None):
        self.mode = mode
        self.variable_mapping = variable_mapping or {}
        self.text = text
        self.result_text = None

    @classmethod
    def batch_replace(cls, text, replacements):
        pattern = re.compile("|".join(map(re.escape, replacements.keys())))

        def repl(_replacements, match):
            return _replacements[match.group()]

        return pattern.sub(lambda m: repl(replacements, m), text)

    @classmethod
    def replace_different(cls, text, patterns_list, callback):
        # 按模式长度降序排序，确保优先匹配长模式
        sorted_patterns = sorted(patterns_list, key=len, reverse=True)
        pattern = re.compile("|".join(map(re.escape, sorted_patterns)))

        def repl(match):
            """替换回调函数"""
            matched_text = match.group()
            # 调用用户提供的回调函数获取替换值
            return callback(matched_text)

        result = pattern.sub(repl, text)
        return result

    def replace(self):
        def get_pipeline_result(origin_data, pipelines: List[PipelineStep]) -> str:
            input_value = origin_data
            for step in pipelines:
                input_value = getattr(PipelineFuncStaticFuncsMixin, step.name,
                                      PipelineFuncStaticFuncsMixin._default_function)(input_value, *step.args)
            return input_value

        def get_prefix_result(process: Union[MockParseResult, DoubleParseResult, StaticParseResult] = None,
                              variable_mapping: dict = None):
            if isinstance(process, DoubleParseResult):
                return variable_mapping.get(process.name, "")
            if isinstance(process, MockParseResult):
                return getattr(MockFuncStaticFuncsMixin, process.name, MockFuncStaticFuncsMixin._default_function)(
                    *process.mock_args)
            if isinstance(process, StaticParseResult):
                return process.name

        def get_every_callback(_text):
            _process = patterns_mapping.get(_text)
            _prefix_result = get_prefix_result(_process, variable_mapping=self.variable_mapping)
            result = get_pipeline_result(_prefix_result, _process.pipelines)
            return str(result)

        patterns_mapping: Dict[
            str, Union[MockParseResult, DoubleParseResult, StaticParseResult]] = VariableParser().parse(self.text)
        if len(patterns_mapping) == 0:
            return self.text
        if self.mode is None:
            has_change_variable = False
            for process in patterns_mapping.values():
                if isinstance(process, MockParseResult):
                    has_change_variable = True
                    break
            if has_change_variable:
                self.mode = ChangeModeEnum.CHANGE_EVERY_TIME
            else:
                self.mode = ChangeModeEnum.JUST_ONCE
        if self.mode == ChangeModeEnum.JUST_ONCE:
            cache_result_mapping = defaultdict(str)
            for key_word, result_object in patterns_mapping.items():
                prefix_result = get_prefix_result(result_object, variable_mapping=self.variable_mapping)
                value = get_pipeline_result(prefix_result, result_object.pipelines)
                cache_result_mapping[key_word] = str(value)
            self.result_text = self.batch_replace(self.text, cache_result_mapping)
            return self.result_text
        if self.mode == ChangeModeEnum.CHANGE_EVERY_TIME:
            self.result_text = self.replace_different(self.text, patterns_mapping.keys(), get_every_callback)
            return self.result_text


# 使用示例
if __name__ == "__main__":
    parser = VariableParser()
    # test_str2 = """
    # {{name}}
    # {{'sheldon'}}
    # {% mock 'integer',1000,2000 %}
    # {{name|md5()|substr(10,20)}}
    # {{'大萨达撒'|md5()|substr(10,20)|padStart(20,'12')}}
    # {{'大萨达撒'|md5()|substr(10,20)|padStart(20,'12')}}
    # {% mock 'now','second','yyyy-MM-dd HH:mm:ss','-2 day','start'|substr(1,5)|concat('sheldon') %}
    # ----------error------------
    # {% mock 'int2eger',1000,2000|m5d5()|bas2e64() %}
    # {% mock 'integer',1000,2000|md5()|base64() %}
    # {% mock 'name','true' %}
    # """
    test_str2 = """
    {
        "name": {%mock1%},
        "jk": "测试-BJAutoR{% mock 'now','day','yyyymmdd','','start' %}"
    }
    """
    test_str = "{% mock 'integer',1000,2000 %}"
    variable_mapping: Dict[str, str] = {
        "name": "sheldon parsons"
    }
    res = ExchangeToller(test_str2, variable_mapping).replace()
    print(res)
    print(json.loads(res))
