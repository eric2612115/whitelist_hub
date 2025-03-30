"""
Tools system for agents.

This module defines the base Tool class and tool registry system.
"""

import inspect
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set, Type, ClassVar, Callable, Awaitable
from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


class Tool(ABC):
    """Base class for all tools that agents can use.
    
    A tool is a function that an agent can call to perform an action
    or retrieve information from the external world.
    """
    
    name: ClassVar[str]
    description: ClassVar[str]
    parameters_schema: ClassVar[Dict[str, Any]]
    required_parameters: ClassVar[List[str]]
    
    def __init__(self):
        """Initialize the tool."""
        if not hasattr(self.__class__, 'name'):
            raise ValueError(f"Tool class {self.__class__.__name__} must define a 'name' class variable")
        if not hasattr(self.__class__, 'description'):
            raise ValueError(f"Tool class {self.__class__.__name__} must define a 'description' class variable")
    
    @abstractmethod
    async def execute(self, parameters: Dict[str, Any]) -> Any:
        """Execute the tool with the given parameters.
        
        Args:
            parameters: The parameters for the tool
            
        Returns:
            The result of the tool execution
        """
        pass
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the parameters against the schema.
        
        Args:
            parameters: The parameters to validate
            
        Returns:
            The validated parameters
            
        Raises:
            ValueError: If the parameters are invalid
        """
        # Check required parameters
        for param in self.required_parameters:
            if param not in parameters:
                raise ValueError(f"Missing required parameter: {param}")
        
        # Return a copy of the parameters
        return parameters.copy()


class ToolRegistry:
    """Registry for all available tools in the system.
    
    This is a singleton class that maintains a registry of all available tools
    that agents can use.
    """
    
    _tools: Dict[str, Type[Tool]] = {}
    
    @classmethod
    def register_tool(cls, tool_class: Type[Tool]) -> Type[Tool]:
        """Register a tool class in the registry.
        
        Args:
            tool_class: The tool class to register
            
        Returns:
            The registered tool class
            
        Raises:
            ValueError: If a tool with the same name is already registered
        """
        if not hasattr(tool_class, 'name'):
            raise ValueError(f"Tool class {tool_class.__name__} must define a 'name' class variable")
        
        tool_name = tool_class.name
        if tool_name in cls._tools:
            logger.warning(f"Tool with name {tool_name} is already registered. Overwriting.")
        
        cls._tools[tool_name] = tool_class
        logger.info(f"Registered tool: {tool_name}")
        return tool_class
    
    @classmethod
    def get_tool_class(cls, name: str) -> Type[Tool]:
        """Get a tool class by name.
        
        Args:
            name: The name of the tool
            
        Returns:
            The tool class
            
        Raises:
            ValueError: If no tool with the given name is registered
        """
        if name not in cls._tools:
            raise ValueError(f"No tool registered with name: {name}")
        return cls._tools[name]
    
    @classmethod
    def get_tool(cls, name: str) -> Tool:
        """Get a tool instance by name.
        
        Args:
            name: The name of the tool
            
        Returns:
            A new instance of the tool
            
        Raises:
            ValueError: If no tool with the given name is registered
        """
        tool_class = cls.get_tool_class(name)
        return tool_class()
    
    @classmethod
    def list_tools(cls) -> List[Dict[str, Any]]:
        """List all registered tools.
        
        Returns:
            A list of tool information dictionaries
        """
        return [
            {
                "name": tool_class.name,
                "description": tool_class.description,
                "parameters_schema": getattr(tool_class, 'parameters_schema', {}),
                "required_parameters": getattr(tool_class, 'required_parameters', [])
            }
            for tool_class in cls._tools.values()
        ]


def register_tool(tool_class: Type[Tool] = None) -> Any:
    """Decorator for registering a tool class.
    
    This decorator can be used on a Tool class to automatically register it
    with the ToolRegistry.
    
    Args:
        tool_class: The tool class to register
        
    Returns:
        The registered tool class
    """
    def decorator(cls):
        return ToolRegistry.register_tool(cls)
    
    if tool_class is None:
        return decorator
    return decorator(tool_class)


# Create convenience functions for external use
def get_tool(name: str) -> Tool:
    """Get a tool instance by name.
    
    Args:
        name: The name of the tool
        
    Returns:
        A new instance of the tool
    """
    return ToolRegistry.get_tool(name)
