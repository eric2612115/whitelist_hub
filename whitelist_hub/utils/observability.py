"""
Observability utilities.

This module provides base classes and utilities for implementing 
observability patterns like event emission and telemetry.
"""

import logging
import time
import uuid
from abc import ABC
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Callable, Union

logger = logging.getLogger(__name__)


class EventEmitter:
    """Base class for objects that emit events.
    
    This class implements the observer pattern, allowing listeners
    to subscribe to events emitted by the object.
    """
    
    def __init__(self):
        """Initialize the event emitter."""
        self._listeners: Dict[str, Set[Callable[[Dict[str, Any]], None]]] = {}
        self._global_listeners: Set[Callable[[str, Dict[str, Any]], None]] = set()
    
    def add_listener(self, event: str, listener: Callable[[Dict[str, Any]], None]) -> None:
        """Add a listener for a specific event.
        
        Args:
            event: The event name
            listener: A function that takes the event data as an argument
        """
        if event not in self._listeners:
            self._listeners[event] = set()
        self._listeners[event].add(listener)
    
    def remove_listener(self, event: str, listener: Callable[[Dict[str, Any]], None]) -> None:
        """Remove a listener for a specific event.
        
        Args:
            event: The event name
            listener: The listener to remove
        """
        if event in self._listeners:
            self._listeners[event].discard(listener)
            if not self._listeners[event]:
                del self._listeners[event]
    
    def add_global_listener(self, listener: Callable[[str, Dict[str, Any]], None]) -> None:
        """Add a listener for all events.
        
        Args:
            listener: A function that takes the event name and data as arguments
        """
        self._global_listeners.add(listener)
    
    def remove_global_listener(self, listener: Callable[[str, Dict[str, Any]], None]) -> None:
        """Remove a global listener.
        
        Args:
            listener: The listener to remove
        """
        self._global_listeners.discard(listener)
    
    def emit_event(self, event: str, data: Dict[str, Any] = None) -> None:
        """Emit an event to all registered listeners.
        
        Args:
            event: The event name
            data: The event data
        """
        data = data or {}
        
        # Add timestamp if not present
        if "timestamp" not in data:
            data["timestamp"] = datetime.utcnow().isoformat()
        
        # Call event-specific listeners
        if event in self._listeners:
            for listener in self._listeners[event]:
                try:
                    listener(data)
                except Exception as e:
                    logger.error(f"Error in event listener for {event}: {str(e)}")
        
        # Call global listeners
        for listener in self._global_listeners:
            try:
                listener(event, data)
            except Exception as e:
                logger.error(f"Error in global event listener: {str(e)}")


class Observable(EventEmitter):
    """Base class for objects that can be observed.
    
    This class extends EventEmitter with additional convenience methods
    for observable objects like agents and workflows.
    """
    
    def __init__(self):
        """Initialize the observable object."""
        super().__init__()
        self.id = str(uuid.uuid4())
        self.created_at = datetime.utcnow()
    
    def emit_event(self, event: str, data: Dict[str, Any] = None) -> None:
        """Emit an event with object context information.
        
        Args:
            event: The event name
            data: The event data
        """
        data = data or {}
        
        # Add object context information
        context_data = {
            "id": self.id,
            "timestamp": datetime.utcnow().isoformat(),
            **data
        }
        
        # Add object type-specific fields
        for attr in ["name", "state", "type"]:
            if hasattr(self, attr):
                context_data[attr] = getattr(self, attr)
        
        super().emit_event(event, context_data)


class Telemetry:
    """Utility for collecting telemetry data.
    
    This class provides methods for tracking metrics like execution time,
    error rates, and resource usage.
    """
    
    @staticmethod
    def measure_execution_time(func: Callable) -> Callable:
        """Decorator to measure the execution time of a function.
        
        Args:
            func: The function to measure
            
        Returns:
            Decorated function
        """
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                execution_time = time.time() - start_time
                logger.debug(f"{func.__name__} execution time: {execution_time:.4f}s")
        
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                execution_time = time.time() - start_time
                logger.debug(f"{func.__name__} execution time: {execution_time:.4f}s")
        
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    @staticmethod
    def track_event(event_name: str, properties: Dict[str, Any] = None) -> None:
        """Track an event for telemetry purposes.
        
        Args:
            event_name: The name of the event
            properties: Event properties
        """
        properties = properties or {}
        logger.info(f"Telemetry event: {event_name} {properties}")
        # In a real implementation, this would send the event to a telemetry service


class LoggingEventListener:
    """Event listener that logs events.
    
    This class provides a simple implementation of an event listener
    that logs events to the standard logging system.
    """
    
    def __init__(self, level: int = logging.INFO):
        """Initialize the logging event listener.
        
        Args:
            level: The logging level to use
        """
        self.level = level
    
    def __call__(self, event: str, data: Dict[str, Any]) -> None:
        """Handle an event by logging it.
        
        Args:
            event: The event name
            data: The event data
        """
        logger.log(self.level, f"Event: {event} - {data}")
