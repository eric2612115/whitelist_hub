"""
Task model for agent execution.

This module defines the Task class, which represents a specific task
that should be executed by an agent.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Type, ClassVar, Union
from pydantic import BaseModel, Field, validator


class TaskState(str, Enum):
    """States for task execution."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


class TaskConfig(BaseModel):
    """Configuration for a task."""
    name: str
    description: str = ""
    agent_name: str
    inputs: Dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: int = 300
    retry_count: int = 3
    priority: int = 0
    dependencies: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Task(BaseModel):
    """A task to be executed by an agent.
    
    A task represents a specific job that should be done by an agent.
    It contains all the information needed to execute the task, including
    the agent to use, inputs, dependencies, etc.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    config: TaskConfig
    state: TaskState = TaskState.PENDING
    workflow_id: Optional[str] = None
    context_id: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retries: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @property
    def name(self) -> str:
        """Get the task name."""
        return self.config.name
    
    @property
    def agent_name(self) -> str:
        """Get the agent name."""
        return self.config.agent_name
    
    @property
    def inputs(self) -> Dict[str, Any]:
        """Get the task inputs."""
        return self.config.inputs
    
    @property
    def dependencies(self) -> List[str]:
        """Get the task dependencies."""
        return self.config.dependencies
    
    def set_running(self):
        """Set the task state to running."""
        self.state = TaskState.RUNNING
        self.started_at = datetime.utcnow()
    
    def set_succeeded(self, result: Dict[str, Any]):
        """Set the task state to succeeded.
        
        Args:
            result: The task result
        """
        self.state = TaskState.SUCCEEDED
        self.completed_at = datetime.utcnow()
        self.result = result
    
    def set_failed(self, error: str):
        """Set the task state to failed.
        
        Args:
            error: The error message
        """
        self.state = TaskState.FAILED
        self.completed_at = datetime.utcnow()
        self.error = error
    
    def set_canceled(self):
        """Set the task state to canceled."""
        self.state = TaskState.CANCELED
        self.completed_at = datetime.utcnow()
    
    def is_completed(self) -> bool:
        """Check if the task is completed (succeeded or failed).
        
        Returns:
            True if the task is completed, False otherwise
        """
        return self.state in (TaskState.SUCCEEDED, TaskState.FAILED, TaskState.CANCELED)
    
    def is_runnable(self) -> bool:
        """Check if the task is ready to run.
        
        A task is runnable if it is pending and has not exceeded its retry count.
        
        Returns:
            True if the task is runnable, False otherwise
        """
        return (
            self.state == TaskState.PENDING and
            self.retries < self.config.retry_count
        )
    
    def increment_retry(self):
        """Increment the retry counter."""
        self.retries += 1
        if self.retries >= self.config.retry_count:
            self.set_failed(f"Exceeded retry count ({self.config.retry_count})")
        else:
            self.state = TaskState.PENDING
