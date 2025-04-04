import time
import functools
import logging
import threading
from config.settings import TIMING_PREFIX

timing_lock = threading.Lock()

def log_execution_time(name):
    """Décorateur pour mesurer le temps d'exécution d'une fonction"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(func.__module__)
            start = time.perf_counter()
            result = func(*args, **kwargs)
            end = time.perf_counter()
            
            with timing_lock:
                logger.info(f"{TIMING_PREFIX}{name} executed in {(end - start)*1000:.2f}ms")
            
            return result
        return wrapper
    return decorator