"""
Retry utilities.

This module provides decorators and utilities for implementing
retry logic on functions and methods.
"""

import asyncio
import functools
import inspect
import logging
import random
import time
from typing import Any, Callable, List, Optional, Type, TypeVar, Union, cast

logger = logging.getLogger(__name__)


T = TypeVar("T")


def retryable(
    max_retries: int = 3,
    retry_delay: float = 1.0,
    exponential_backoff: bool = True,
    jitter: bool = True,
    max_delay: float = 60.0,
    exceptions: Union[Type[Exception], List[Type[Exception]]] = Exception
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to make a function retryable.
    
    Args:
        max_retries: Maximum number of retries
        retry_delay: Base delay between retries in seconds
        exponential_backoff: Whether to use exponential backoff
        jitter: Whether to add jitter to the delay
        max_delay: Maximum delay between retries in seconds
        exceptions: Exception types to retry on
        
    Returns:
        Decorated function
    """
    if isinstance(exceptions, type) and issubclass(exceptions, Exception):
        exceptions = [exceptions]
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None
            
            for retry in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except tuple(exceptions) as e:
                    last_exception = e
                    
                    if retry >= max_retries:
                        logger.warning(
                            f"Function {func.__name__} failed after {retry + 1} attempts. "
                            f"Last error: {str(e)}"
                        )
                        raise
                    
                    # Calculate delay with exponential backoff and jitter
                    delay = retry_delay
                    if exponential_backoff:
                        delay = min(retry_delay * (2 ** retry), max_delay)
                    if jitter:
                        delay = delay * (0.5 + random.random())
                    
                    logger.info(
                        f"Retrying function {func.__name__} after error: {str(e)}. "
                        f"Retry {retry + 1}/{max_retries} in {delay:.2f}s"
                    )
                    
                    # Wait before retrying
                    await asyncio.sleep(delay)
            
            # This should never happen, but just in case
            assert last_exception is not None
            raise last_exception
        
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None
            
            for retry in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except tuple(exceptions) as e:
                    last_exception = e
                    
                    if retry >= max_retries:
                        logger.warning(
                            f"Function {func.__name__} failed after {retry + 1} attempts. "
                            f"Last error: {str(e)}"
                        )
                        raise
                    
                    # Calculate delay with exponential backoff and jitter
                    delay = retry_delay
                    if exponential_backoff:
                        delay = min(retry_delay * (2 ** retry), max_delay)
                    if jitter:
                        delay = delay * (0.5 + random.random())
                    
                    logger.info(
                        f"Retrying function {func.__name__} after error: {str(e)}. "
                        f"Retry {retry + 1}/{max_retries} in {delay:.2f}s"
                    )
                    
                    # Wait before retrying
                    time.sleep(delay)
            
            # This should never happen, but just in case
            assert last_exception is not None
            raise last_exception
        
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


async def async_retry(
    func: Callable[..., Any],
    *args: Any,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    exponential_backoff: bool = True,
    jitter: bool = True,
    max_delay: float = 60.0,
    exceptions: Union[Type[Exception], List[Type[Exception]]] = Exception,
    **kwargs: Any
) -> Any:
    """Retry an async function with the given arguments.
    
    Args:
        func: The function to retry
        *args: Positional arguments for the function
        max_retries: Maximum number of retries
        retry_delay: Base delay between retries in seconds
        exponential_backoff: Whether to use exponential backoff
        jitter: Whether to add jitter to the delay
        max_delay: Maximum delay between retries in seconds
        exceptions: Exception types to retry on
        **kwargs: Keyword arguments for the function
        
    Returns:
        The result of the function
        
    Raises:
        The last exception raised by the function
    """
    if isinstance(exceptions, type) and issubclass(exceptions, Exception):
        exceptions = [exceptions]
    
    last_exception = None
    
    for retry in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except tuple(exceptions) as e:
            last_exception = e
            
            if retry >= max_retries:
                logger.warning(
                    f"Function {func.__name__} failed after {retry + 1} attempts. "
                    f"Last error: {str(e)}"
                )
                raise
            
            # Calculate delay with exponential backoff and jitter
            delay = retry_delay
            if exponential_backoff:
                delay = min(retry_delay * (2 ** retry), max_delay)
            if jitter:
                delay = delay * (0.5 + random.random())
            
            logger.info(
                f"Retrying function {func.__name__} after error: {str(e)}. "
                f"Retry {retry + 1}/{max_retries} in {delay:.2f}s"
            )
            
            # Wait before retrying
            await asyncio.sleep(delay)
    
    # This should never happen, but just in case
    assert last_exception is not None
    raise last_exception
