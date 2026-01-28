# 自定义资源信号异常
class ResourceLimitExceededError(Exception):
    pass


# 自定义内存信号异常
class MemoryResourceLimitExceededError(ResourceLimitExceededError):
    pass


# 自定义超时信号异常
class TimeResourceLimitExceededError(ResourceLimitExceededError):
    pass


# 自定义主动停止信号异常
class EffectStopExceededError(ResourceLimitExceededError):
    pass
