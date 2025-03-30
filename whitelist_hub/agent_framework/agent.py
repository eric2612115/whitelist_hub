"""
Agent core implementation.

This module defines the base Agent class and its configuration.
"""

import asyncio
import uuid
import logging
import inspect
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Callable, Type, Union, TypeVar
from enum import Enum
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field, validator

from .context import Context, Message, Thought, Action
from .tools import Tool, ToolRegistry


logger = logging.getLogger(__name__)


class AgentState(str, Enum):
    """Agent execution states."""
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    WAITING = "waiting"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELED = "canceled"


class AgentRole(str, Enum):
    """Standard agent roles in the system."""
    COORDINATOR = "coordinator"
    CRAWLER = "crawler"
    ANALYZER = "analyzer"
    VERIFIER = "verifier"
    CUSTOM = "custom"


class AgentConfig(BaseModel):
    """Configuration for an agent."""
    name: str
    description: str = ""
    role: AgentRole = AgentRole.CUSTOM
    model_name: str = "gemini-2.0-pro-001"  # Default to Gemini Pro
    temperature: float = 0.2
    max_tokens: Optional[int] = None
    tools: List[str] = Field(default_factory=list)
    system_prompt: str = ""
    timeout_seconds: int = 60
    max_retries: int = 3
    retry_delay_seconds: int = 1
    telemetry_enabled: bool = True
    verbose: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Agent(ABC):
    """Base class for all agents in the system.
    
    An agent is responsible for executing a specific task using AI models
    and tools. It can reason, plan, and execute actions to achieve its goals.
    """
    
    def __init__(self, config: AgentConfig):
        """Initialize the agent with its configuration.
        
        Args:
            config: The agent configuration
        """
        self.config = config
        self.id = str(uuid.uuid4())
        self.state = AgentState.IDLE
        self.tools = []
        self._load_tools()
        self._listeners = set()
        
    def _load_tools(self):
        """Load the tools specified in the configuration."""
        for tool_name in self.config.tools:
            try:
                tool = ToolRegistry.get_tool(tool_name)
                self.tools.append(tool)
                if self.config.verbose:
                    logger.info(f"Agent {self.config.name} loaded tool: {tool_name}")
            except Exception as e:
                logger.error(f"Failed to load tool {tool_name}: {str(e)}")
    
    def add_event_listener(self, listener: Callable[[str, Dict[str, Any]], None]):
        """Add an event listener to the agent.
        
        Args:
            listener: A function that takes an event name and data
        """
        self._listeners.add(listener)
    
    def remove_event_listener(self, listener: Callable[[str, Dict[str, Any]], None]):
        """Remove an event listener from the agent.
        
        Args:
            listener: The listener to remove
        """
        self._listeners.discard(listener)
    
    def _emit_event(self, event_name: str, data: Dict[str, Any] = None):
        """Emit an event to all listeners.
        
        Args:
            event_name: The name of the event
            data: The event data
        """
        data = data or {}
        for listener in self._listeners:
            try:
                listener(event_name, {
                    "agent_id": self.id,
                    "agent_name": self.config.name,
                    "timestamp": datetime.utcnow().isoformat(),
                    "event": event_name,
                    **data
                })
            except Exception as e:
                logger.error(f"Error in event listener: {str(e)}")
    
    async def execute(self, context: Context) -> Context:
        """Execute the agent with the given context.
        
        Args:
            context: The execution context containing inputs and history
            
        Returns:
            The updated context with agent outputs
        """
        self.state = AgentState.STARTING
        self._emit_event("agent_starting", {"context_id": context.id})
        
        try:
            # Set start time
            context.metadata["start_time"] = datetime.utcnow().isoformat()
            
            # Run with timeout
            self.state = AgentState.RUNNING
            self._emit_event("agent_running")
            
            # Set up the timeout
            try:
                result = await asyncio.wait_for(
                    self._execute(context),
                    timeout=self.config.timeout_seconds
                )
                self.state = AgentState.SUCCEEDED
                context.metadata["end_time"] = datetime.utcnow().isoformat()
                self._emit_event("agent_succeeded")
                return result
            except asyncio.TimeoutError:
                self.state = AgentState.TIMEOUT
                error_msg = f"Agent {self.config.name} timed out after {self.config.timeout_seconds} seconds"
                context.metadata["error"] = error_msg
                context.metadata["end_time"] = datetime.utcnow().isoformat()
                self._emit_event("agent_timeout", {"error": error_msg})
                raise TimeoutError(error_msg)
            
        except Exception as e:
            self.state = AgentState.FAILED
            error_msg = f"Agent {self.config.name} failed: {str(e)}"
            context.metadata["error"] = error_msg
            context.metadata["end_time"] = datetime.utcnow().isoformat()
            self._emit_event("agent_failed", {"error": error_msg})
            raise
    
    @abstractmethod
    async def _execute(self, context: Context) -> Context:
        """Implement the actual execution logic of the agent.
        
        Args:
            context: The execution context
            
        Returns:
            The updated context with agent outputs
        """
        pass
    
    def add_thought(self, context: Context, content: str, category: str = "general") -> Thought:
        """Add a thought to the context.
        
        Args:
            context: The execution context
            content: The thought content
            category: The thought category
            
        Returns:
            The created thought
        """
        thought = Thought(
            content=content,
            category=category,
            agent_id=self.id,
            agent_name=self.config.name
        )
        context.thoughts.append(thought)
        self._emit_event("agent_thought", {
            "thought": thought.dict(exclude={"metadata": {"callable"}})
        })
        return thought
    
    def add_action(self, context: Context, tool_name: str, parameters: Dict[str, Any] = None) -> Action:
        """Add an action to the context.
        
        Args:
            context: The execution context
            tool_name: The name of the tool to use
            parameters: The parameters for the tool
            
        Returns:
            The created action
        """
        action = Action(
            tool_name=tool_name,
            parameters=parameters or {},
            agent_id=self.id,
            agent_name=self.config.name
        )
        context.actions.append(action)
        self._emit_event("agent_action", {
            "action": action.dict(exclude={"metadata": {"callable"}})
        })
        return action
    
    async def use_tool(self, context: Context, tool_name: str, parameters: Dict[str, Any] = None) -> Any:
        """Use a tool and record the action.
        
        Args:
            context: The execution context
            tool_name: The name of the tool to use
            parameters: The parameters for the tool
            
        Returns:
            The result of the tool execution
        """
        action = self.add_action(context, tool_name, parameters)
        
        try:
            # Find the tool
            tool = next((t for t in self.tools if t.name == tool_name), None)
            if not tool:
                raise ValueError(f"Tool {tool_name} not found or not loaded for this agent")
            
            # Execute the tool
            start_time = datetime.utcnow()
            result = await tool.execute(parameters or {})
            end_time = datetime.utcnow()
            
            # Update the action
            action.success = True
            action.result = result
            action.metadata["execution_time_ms"] = (end_time - start_time).total_seconds() * 1000
            
            self._emit_event("tool_success", {
                "tool": tool_name,
                "execution_time_ms": action.metadata["execution_time_ms"]
            })
            
            return result
        except Exception as e:
            # Update the action with the error
            action.success = False
            action.error = str(e)
            
            self._emit_event("tool_error", {
                "tool": tool_name,
                "error": str(e)
            })
            
            raise
