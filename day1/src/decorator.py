#!/usr/bin/env python3
"""
装饰器实战：retry 和 timing
"""

import time
import random
from functools import wraps
from loguru import logger
from typing import Callable, Any, Optional

# ========== 装饰器1：自动重试 ==========

def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    exceptions: tuple = (Exception,)
) -> Callable:
    """
    失败自动重试装饰器
    
    用法：
        @retry(max_attempts=3, delay=2.0)
        def call_api():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)  # 保留原函数信息
        def wrapper(*args, **kwargs) -> Any:
            for attempt in range(1, max_attempts + 1):
                try:
                    logger.info(f"[{func.__name__}] 尝试 {attempt}/{max_attempts}")
                    result = func(*args, **kwargs)
                    logger.success(f"[{func.__name__}] 成功！")
                    return result
                    
                except exceptions as e:
                    logger.warning(f"[{func.__name__}] 失败: {e}")
                    
                    if attempt == max_attempts:
                        logger.error(f"[{func.__name__}] 重试耗尽，最终失败")
                        raise  # 最后一次，抛出异常
                    
                    # 等待后重试
                    logger.info(f"等待 {delay} 秒后重试...")
                    time.sleep(delay)
            
            return None  # 理论上不会执行到这里
        return wrapper
    return decorator


# ========== 装饰器2：性能计时 ==========

def timing(func: Callable) -> Callable:
    """
    函数执行时间计时器
    
    用法：
        @timing
        def heavy_computation():
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        start = time.perf_counter()  # 高精度计时
        
        result = func(*args, **kwargs)
        
        elapsed = time.perf_counter() - start
        logger.info(f"[{func.__name__}] 耗时: {elapsed:.4f} 秒")
        
        return result
    return wrapper


# ========== 装饰器3：组合使用 ==========

def log_call(func: Callable) -> Callable:
    """记录函数调用参数和结果"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        args_str = ", ".join([str(a) for a in args])
        kwargs_str = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
        all_args = f"{args_str}, {kwargs_str}" if kwargs_str else args_str
        
        logger.debug(f"调用 {func.__name__}({all_args})")
        result = func(*args, **kwargs)
        logger.debug(f"{func.__name__} 返回: {result}")
        return result
    return wrapper