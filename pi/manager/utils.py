from functools import wraps


def cache_if_not_none(func):
    cache = {}

    @wraps(func)
    def wrapper(*args):
        if args in cache:
            return cache[args]
        result = func(*args)
        if result is not None:
            cache[args] = result
        return result

    return wrapper
