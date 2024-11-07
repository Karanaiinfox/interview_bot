import functools
import logging

logger = logging.getLogger(__name__)

def log_function_call(func):
    """Decorator to log function calls with arguments and execution time."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger.info(f"Called function: {func.__name__} with args: {args}, kwargs: {kwargs}")
        return func(*args, **kwargs)
    return wrapper
