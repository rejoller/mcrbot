import asyncio
import functools


def timeout(seconds=1, error_message="Таймаут"):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except asyncio.TimeoutError:
                raise TimeoutError(error_message)
        return wrapper
    return decorator