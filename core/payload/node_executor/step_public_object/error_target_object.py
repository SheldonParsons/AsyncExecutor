class ErrorRaiseTarget:

    def __init__(self, is_raise_exception=None, error_strategy=None, target=None):
        self.is_raise_exception = is_raise_exception
        self.error_strategy = error_strategy
        self.target = target
