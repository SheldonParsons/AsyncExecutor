from core.utils.mock_func import MockFuncStaticFuncsMixin
from core.utils.pipeline_func import PipelineFuncStaticFuncsMixin


class DataWrapper:
    def __init__(self, value):
        self.value = value

    def __getattr__(self, name):
        if hasattr(PipelineFuncStaticFuncsMixin, name):
            pipeline_func = getattr(PipelineFuncStaticFuncsMixin, name)

            def wrapper(*args, **kwargs):
                # 1. 调用原始 Mock 方法获取结果
                raw_value = pipeline_func(self.value, *args, **kwargs)
                self.value = raw_value
                # 2. 将结果包装在 DataWrapper 中
                return self

            return wrapper


class MockFuncGenerator:
    def __getattr__(self, name):
        # 检查请求的方法是否存在于 Mock 工具类中
        if hasattr(MockFuncStaticFuncsMixin, name):
            mock_func = getattr(MockFuncStaticFuncsMixin, name)

            def wrapper(*args, **kwargs):
                # 1. 调用原始 Mock 方法获取结果
                raw_value = mock_func(*args, **kwargs)
                # 2. 将结果包装在 DataWrapper 中
                return DataWrapper(raw_value)

            return wrapper

        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")


if __name__ == "__main__":
    a = MockFuncGenerator()

    # 直接获取 Mock 结果（通过 .value 访问原始值）
    bool_result = a.boolean(10, 20, "true").value
    print(f"Boolean result: {bool_result} (type: {type(bool_result)})")
    print(a.boolean(10, 20, "true"))
    # 链式调用：Mock -> MD5
    md5_result = a.boolean(10, 20, "true").md5().value
    print(f"MD5 result: {md5_result}")

    # 链式调用：Mock -> MD5 -> SHA1
    sha_result = a.boolean(10, 20, "true").md5().sha("sha1").value
    print(f"SHA1 result: {sha_result}")

    # 使用 natural 方法
    num_result = a.natural(1, 100).value
    print(f"Random number: {num_result}")

    # natural -> base64
    b64_result = a.natural(1, 100).base64().value
    print(f"Base64 encoded: {b64_result}")
