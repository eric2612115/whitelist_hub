"""
Context and message objects for agent execution.

This module defines the data models for context, messages, thoughts, and actions
that are used during agent execution.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union
from pydantic import BaseModel, Field, validator


class MessageRole(str, Enum):
    """Roles for messages in the context."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"


class Message(BaseModel):
    """A message in the agent conversation."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: MessageRole
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    name: Optional[str] = None
    function_call: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Thought(BaseModel):
    """A thought produced by an agent during execution."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    category: str = "general"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Action(BaseModel):
    """An action taken by an agent during execution."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tool_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None
    success: bool = False
    result: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Context(BaseModel):
    """The execution context for an agent.
    
    Contains the input, messages, thoughts, actions, and output of an agent execution.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    session_id: Optional[str] = None
    workflow_id: Optional[str] = None
    task_id: Optional[str] = None
    parent_context_id: Optional[str] = None
    
    # Input and output
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    
    # Messages, thoughts, and actions
    messages: List[Message] = Field(default_factory=list)
    thoughts: List[Thought] = Field(default_factory=list)
    actions: List[Action] = Field(default_factory=list)
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def add_message(self, role: Union[MessageRole, str], content: str, 
                   name: Optional[str] = None) -> Message:
        """Add a message to the context.
        
        Args:
            role: The role of the message sender
            content: The message content
            name: Optional name of the sender
            
        Returns:
            The created message
        """
        if isinstance(role, str):
            role = MessageRole(role)
            
        message = Message(
            role=role,
            content=content,
            name=name
        )
        self.messages.append(message)
        return message
    
    def add_system_message(self, content: str) -> Message:
        """Add a system message to the context.
        
        Args:
            content: The message content
            
        Returns:
            The created message
        """
        return self.add_message(MessageRole.SYSTEM, content)
    
    def add_user_message(self, content: str) -> Message:
        """Add a user message to the context.
        
        Args:
            content: The message content
            
        Returns:
            The created message
        """
        return self.add_message(MessageRole.USER, content)
    
    def add_assistant_message(self, content: str) -> Message:
        """Add an assistant message to the context.
        
        Args:
            content: The message content
            
        Returns:
            The created message
        """
        return self.add_message(MessageRole.ASSISTANT, content)
    
    def get_messages_for_llm(self) -> List[Dict[str, Any]]:
        """Get the messages in a format suitable for LLM API calls.
        
        Returns:
            List of message dictionaries
        """
        return [
            {
                "role": msg.role,
                "content": msg.content,
                **({"name": msg.name} if msg.name else {}),
                **({"function_call": msg.function_call} if msg.function_call else {})
            }
            for msg in self.messages
        ]
    
    def copy_with_empty_messages(self) -> 'Context':
        """Create a copy of this context with empty messages list.
        
        This is useful when you want to create a new context for an agent
        with the same inputs but without the message history.
        
        Returns:
            A new context with the same inputs but empty messages
        """
        return Context(
            session_id=self.session_id,
            workflow_id=self.workflow_id,
            task_id=self.task_id,
            parent_context_id=self.id,
            inputs=self.inputs.copy(),
            metadata={
                **self.metadata.copy(),
                "parent_context_id": self.id
            }
        )
