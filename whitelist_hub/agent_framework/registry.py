"""
Registry for agents and agent factories.

This module provides a registry system for agents, allowing them to be
registered, discovered, and instantiated by name.
"""

import logging
from typing import Any, Dict, List, Optional, Type, Callable, TypeVar, cast

from .agent import Agent, AgentConfig

logger = logging.getLogger(__name__)

# Type variable for agent classes
TAgent = TypeVar('TAgent', bound=Agent)


class AgentRegistry:
    """Registry for agent classes and factories.
    
    This class maintains a registry of agent classes and factory functions
    that can be used to create agent instances.
    """
    
    # Maps agent names to their classes or factory functions
    _agent_classes: Dict[str, Type[Agent]] = {}
    _agent_factories: Dict[str, Callable[[AgentConfig], Agent]] = {}
    
    # Maps agent classes to their default configurations
    _default_configs: Dict[Type[Agent], AgentConfig] = {}
    
    @classmethod
    def register_agent_class(cls, agent_name: str, agent_class: Type[TAgent]) -> Type[TAgent]:
        """Register an agent class with the registry.
        
        Args:
            agent_name: The name of the agent
            agent_class: The agent class to register
            
        Returns:
            The registered agent class
            
        Raises:
            ValueError: If an agent with the same name is already registered
        """
        if agent_name in cls._agent_classes:
            logger.warning(f"Agent class with name {agent_name} is already registered. Overwriting.")
        
        cls._agent_classes[agent_name] = agent_class
        logger.info(f"Registered agent class: {agent_name}")
        return agent_class
    
    @classmethod
    def register_agent_factory(
        cls, agent_name: str, factory: Callable[[AgentConfig], Agent]
    ) -> Callable[[AgentConfig], Agent]:
        """Register an agent factory function with the registry.
        
        Args:
            agent_name: The name of the agent
            factory: A function that creates an agent instance from a configuration
            
        Returns:
            The registered factory function
            
        Raises:
            ValueError: If an agent with the same name is already registered
        """
        if agent_name in cls._agent_factories:
            logger.warning(f"Agent factory with name {agent_name} is already registered. Overwriting.")
        
        cls._agent_factories[agent_name] = factory
        logger.info(f"Registered agent factory: {agent_name}")
        return factory
    
    @classmethod
    def register_default_config(
        cls, agent_class: Type[Agent], config: AgentConfig
    ) -> None:
        """Register a default configuration for an agent class.
        
        Args:
            agent_class: The agent class
            config: The default configuration
        """
        cls._default_configs[agent_class] = config
        logger.info(f"Registered default config for agent class: {agent_class.__name__}")
    
    @classmethod
    def get_agent_class(cls, name: str) -> Optional[Type[Agent]]:
        """Get an agent class by name.
        
        Args:
            name: The name of the agent
            
        Returns:
            The agent class, or None if not found
        """
        return cls._agent_classes.get(name)
    
    @classmethod
    def get_agent_factory(cls, name: str) -> Optional[Callable[[AgentConfig], Agent]]:
        """Get an agent factory function by name.
        
        Args:
            name: The name of the agent
            
        Returns:
            The factory function, or None if not found
        """
        return cls._agent_factories.get(name)
    
    @classmethod
    def get_default_config(cls, agent_class: Type[Agent]) -> Optional[AgentConfig]:
        """Get the default configuration for an agent class.
        
        Args:
            agent_class: The agent class
            
        Returns:
            The default configuration, or None if not registered
        """
        return cls._default_configs.get(agent_class)
    
    @classmethod
    def get_agent(cls, name: str, config: Optional[AgentConfig] = None) -> Optional[Agent]:
        """Get an agent instance by name.
        
        This method will first try to use a factory function if one is registered
        for the agent name. If not, it will try to instantiate the agent class.
        
        Args:
            name: The name of the agent
            config: Optional configuration for the agent
            
        Returns:
            An agent instance, or None if no agent is registered with the given name
        """
        # Try to get the factory
        factory = cls.get_agent_factory(name)
        if factory:
            return factory(config) if config else factory(AgentConfig(name=name))
        
        # Try to get the class
        agent_class = cls.get_agent_class(name)
        if agent_class:
            if config:
                return agent_class(config)
            
            # Try to use default config
            default_config = cls.get_default_config(agent_class)
            if default_config:
                return agent_class(default_config)
            
            # Create with minimal config
            return agent_class(AgentConfig(name=name))
        
        # No agent found
        return None
    
    @classmethod
    def list_agents(cls) -> List[str]:
        """List all registered agent names.
        
        Returns:
            List of agent names
        """
        # Combine and deduplicate
        return list(set(list(cls._agent_classes.keys()) + list(cls._agent_factories.keys())))


def register_agent(name: Optional[str] = None) -> Callable[[Type[TAgent]], Type[TAgent]]:
    """Decorator for registering an agent class.
    
    This decorator can be used on an Agent class to automatically register it
    with the AgentRegistry.
    
    Args:
        name: Optional name to register the agent with. If None, the class name will be used.
        
    Returns:
        A decorator function
    """
    def decorator(agent_class: Type[TAgent]) -> Type[TAgent]:
        agent_name = name or agent_class.__name__
        return AgentRegistry.register_agent_class(agent_name, agent_class)
    return decorator


def get_agent(name: str, config: Optional[AgentConfig] = None) -> Optional[Agent]:
    """Get an agent instance by name.
    
    Args:
        name: The name of the agent
        config: Optional configuration for the agent
        
    Returns:
        An agent instance, or None if no agent is registered with the given name
    """
    return AgentRegistry.get_agent(name, config)
