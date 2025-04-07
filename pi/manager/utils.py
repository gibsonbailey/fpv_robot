from functools import wraps
import socket


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


def recv_all(sock: socket.socket, length: int) -> bytes:
    data = b""
    while len(data) < length:
        more = sock.recv(length - len(data))
        if not more:
            raise ConnectionError("Socket connection closed")
        data += more
    return data

