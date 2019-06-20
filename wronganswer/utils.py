class lazy_property:

    def __init__(self, func):
        self.func = func

    def __get__(self, instance, owner):
        value = self.func(instance)
        instance.__dict__[self.func.__name__] = value
        return value
