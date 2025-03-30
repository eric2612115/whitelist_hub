"""
Workflow model for orchestrating tasks and agents.

This module defines the Workflow class, which represents a sequence of
tasks to be executed by agents.
"""

import uuid
import asyncio
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Type, ClassVar, Union, Callable
import networkx as nx
from pydantic import BaseModel, Field, validator

from .task import Task, TaskState, TaskConfig
from .context import Context
from .registry import AgentRegistry
from whitelist_hub.utils.observability import Observable, EventEmitter
from whitelist_hub.utils.retryable import retryable


logger = logging.getLogger(__name__)


class WorkflowState(str, Enum):
    """States for workflow execution."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


class WorkflowConfig(BaseModel):
    """Configuration for a workflow."""
    name: str
    description: str = ""
    tasks: List[TaskConfig] = Field(default_factory=list)
    max_concurrent_tasks: int = 5
    timeout_seconds: int = 3600
    abort_on_failure: bool = False
    retry_failed_tasks: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskResult(BaseModel):
    """Result of a task execution."""
    task_id: str
    task_name: str
    agent_name: str
    state: TaskState
    outputs: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Workflow(Observable):
    """A workflow of tasks to be executed by agents.
    
    A workflow represents a sequence of tasks that should be executed
    to accomplish a larger goal. Tasks can have dependencies on each other,
    and the workflow will ensure they are executed in the correct order.
    """
    
    def __init__(self, config: WorkflowConfig):
        """Initialize the workflow with the given configuration.
        
        Args:
            config: The workflow configuration
        """
        super().__init__()
        self.id = str(uuid.uuid4())
        self.created_at = datetime.utcnow()
        self.config = config
        self.state = WorkflowState.PENDING
        self.tasks: Dict[str, Task] = {}
        self.task_results: Dict[str, TaskResult] = {}
        self.started_at = None
        self.completed_at = None
        self.session_id = None
        self.metadata: Dict[str, Any] = {}
        self._task_graph = nx.DiGraph()
        self._running_tasks = set()
        self._task_semaphore = asyncio.Semaphore(config.max_concurrent_tasks)
        self._cancel_event = asyncio.Event()
        
        # Initialize tasks from config
        self._initialize_tasks()
    
    def _initialize_tasks(self):
        """Initialize tasks from the configuration."""
        # Create tasks
        for task_config in self.config.tasks:
            task = Task(
                config=task_config,
                workflow_id=self.id
            )
            self.tasks[task.id] = task
            self._task_graph.add_node(task.id, task=task)
        
        # Add dependencies
        for task_id, task in self.tasks.items():
            for dep_name in task.dependencies:
                # Find dependency task by name
                dep_tasks = [t for t in self.tasks.values() if t.name == dep_name]
                if not dep_tasks:
                    logger.warning(f"Dependency {dep_name} not found for task {task.name}")
                    continue
                
                # Add edge from dependency to dependent
                for dep_task in dep_tasks:
                    self._task_graph.add_edge(dep_task.id, task_id)
        
        # Validate the graph for cycles
        if not nx.is_directed_acyclic_graph(self._task_graph):
            cycles = list(nx.simple_cycles(self._task_graph))
            raise ValueError(f"Workflow has cyclic dependencies: {cycles}")
    
    def get_runnable_tasks(self) -> List[Task]:
        """Get the list of tasks that are ready to run.
        
        A task is ready to run if all its dependencies have completed successfully
        and it is in the PENDING state.
        
        Returns:
            List of runnable tasks
        """
        runnable_tasks = []
        
        for task_id, task in self.tasks.items():
            # Skip tasks that are not in PENDING state or already running
            if task.state != TaskState.PENDING or task_id in self._running_tasks:
                continue
            
            # Check all dependencies
            dependencies_satisfied = True
            for pred in self._task_graph.predecessors(task_id):
                dep_task = self.tasks[pred]
                if dep_task.state != TaskState.SUCCEEDED:
                    dependencies_satisfied = False
                    break
            
            if dependencies_satisfied:
                runnable_tasks.append(task)
        
        return runnable_tasks
    
    def all_tasks_completed(self) -> bool:
        """Check if all tasks have completed.
        
        Returns:
            True if all tasks have completed, False otherwise
        """
        return all(task.is_completed() for task in self.tasks.values())
    
    def any_task_failed(self) -> bool:
        """Check if any task has failed.
        
        Returns:
            True if any task has failed, False otherwise
        """
        return any(task.state == TaskState.FAILED for task in self.tasks.values())
    
    async def execute_task(self, task: Task, global_context: Context) -> TaskResult:
        """Execute a single task.
        
        Args:
            task: The task to execute
            global_context: The global workflow context
            
        Returns:
            The task result
        """
        self._running_tasks.add(task.id)
        task.set_running()
        self.emit_event("task_started", {"task_id": task.id, "task_name": task.name})
        
        start_time = datetime.utcnow()
        
        try:
            # Create task-specific context
            task_context = Context(
                session_id=self.session_id,
                workflow_id=self.id,
                task_id=task.id,
                parent_context_id=global_context.id,
                inputs={
                    **global_context.inputs,  # Global inputs
                    **task.inputs            # Task-specific inputs
                },
                metadata={
                    "workflow_id": self.id,
                    "workflow_name": self.config.name,
                    "task_id": task.id,
                    "task_name": task.name,
                    "agent_name": task.agent_name
                }
            )
            
            # Copy relevant messages from global context
            for msg in global_context.messages:
                if msg.role == "system":
                    task_context.messages.append(msg)
            
            # Get the agent for this task
            agent = AgentRegistry.get_agent(task.agent_name)
            if not agent:
                raise ValueError(f"Agent not found: {task.agent_name}")
            
            # Execute the agent
            result_context = await agent.execute(task_context)
            
            # Check for cancellation
            if self._cancel_event.is_set():
                task.set_canceled()
                self.emit_event("task_canceled", {"task_id": task.id, "task_name": task.name})
                return TaskResult(
                    task_id=task.id,
                    task_name=task.name,
                    agent_name=task.agent_name,
                    state=TaskState.CANCELED,
                    execution_time=(datetime.utcnow() - start_time).total_seconds()
                )
            
            # Update the task with the result
            task.set_succeeded(result_context.outputs)
            
            # Create and return the task result
            task_result = TaskResult(
                task_id=task.id,
                task_name=task.name,
                agent_name=task.agent_name,
                state=TaskState.SUCCEEDED,
                outputs=result_context.outputs,
                execution_time=(datetime.utcnow() - start_time).total_seconds(),
                metadata={
                    "thought_count": len(result_context.thoughts),
                    "action_count": len(result_context.actions)
                }
            )
            
            # Update global context with task outputs and messages
            for key, value in result_context.outputs.items():
                output_key = f"{task.name}.{key}"
                global_context.outputs[output_key] = value
            
            # Add a system message with the task result summary
            result_summary = f"Task '{task.name}' completed successfully.\n"
            for key, value in result_context.outputs.items():
                result_summary += f"- {key}: {value if isinstance(value, (str, int, float, bool)) else 'Complex object'}\n"
            
            global_context.add_system_message(result_summary)
            
            # Emit task completion event
            self.emit_event("task_completed", {
                "task_id": task.id,
                "task_name": task.name,
                "execution_time": task_result.execution_time
            })
            
            return task_result
            
        except Exception as e:
            # Handle task failure
            error_msg = f"Task execution failed: {str(e)}"
            logger.exception(error_msg)
            
            task.set_failed(error_msg)
            
            # Emit task failure event
            self.emit_event("task_failed", {
                "task_id": task.id,
                "task_name": task.name,
                "error": error_msg
            })
            
            # Return failure result
            return TaskResult(
                task_id=task.id,
                task_name=task.name,
                agent_name=task.agent_name,
                state=TaskState.FAILED,
                error=error_msg,
                execution_time=(datetime.utcnow() - start_time).total_seconds()
            )
        finally:
            self._running_tasks.remove(task.id)
            self._task_semaphore.release()
    
    @retryable(max_retries=3, retry_delay=1)
    async def execute(self, context: Context) -> Context:
        """Execute the workflow with the given context.
        
        Args:
            context: The execution context with workflow inputs
            
        Returns:
            The updated context with workflow outputs
        """
        if self.state == WorkflowState.RUNNING:
            raise ValueError("Workflow is already running")
        
        self.state = WorkflowState.RUNNING
        self.started_at = datetime.utcnow()
        self.session_id = context.session_id
        
        # Store the context ID for reference
        workflow_context_id = context.id
        context.metadata["workflow_id"] = self.id
        
        self.emit_event("workflow_started", {
            "task_count": len(self.tasks),
            "context_id": workflow_context_id
        })
        
        try:
            # Execute until all tasks are completed or timeout
            timeout_task = asyncio.create_task(asyncio.sleep(self.config.timeout_seconds))
            execution_task = asyncio.create_task(self._execute_workflow_tasks(context))
            
            done, pending = await asyncio.wait(
                [timeout_task, execution_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Handle timeout
            if timeout_task in done:
                # Cancel execution task
                execution_task.cancel()
                try:
                    await execution_task
                except asyncio.CancelledError:
                    pass
                
                self.state = WorkflowState.FAILED
                error_msg = f"Workflow execution timed out after {self.config.timeout_seconds} seconds"
                context.metadata["error"] = error_msg
                
                self.emit_event("workflow_timeout", {"error": error_msg})
            else:
                # Cancel timeout task
                timeout_task.cancel()
                try:
                    await timeout_task
                except asyncio.CancelledError:
                    pass
                
                # Get result from execution task
                try:
                    result_context = await execution_task
                    # Workflow completed successfully
                    self.state = WorkflowState.SUCCEEDED
                    self.emit_event("workflow_completed", {
                        "execution_time": (datetime.utcnow() - self.started_at).total_seconds()
                    })
                    
                    context = result_context
                except Exception as e:
                    # Workflow failed
                    self.state = WorkflowState.FAILED
                    error_msg = f"Workflow execution failed: {str(e)}"
                    context.metadata["error"] = error_msg
                    
                    self.emit_event("workflow_failed", {"error": error_msg})
            
        except Exception as e:
            # Handle any unexpected exceptions
            self.state = WorkflowState.FAILED
            error_msg = f"Workflow execution failed: {str(e)}"
            context.metadata["error"] = error_msg
            logger.exception(error_msg)
            
            self.emit_event("workflow_failed", {"error": error_msg})
        
        finally:
            self.completed_at = datetime.utcnow()
            execution_time = (self.completed_at - self.started_at).total_seconds()
            
            # Add workflow result summary to context
            if self.state == WorkflowState.SUCCEEDED:
                summary = (
                    f"Workflow '{self.config.name}' completed successfully in {execution_time:.2f} seconds.\n"
                    f"Tasks: {len(self.tasks)} total, "
                    f"{sum(1 for t in self.tasks.values() if t.state == TaskState.SUCCEEDED)} succeeded, "
                    f"{sum(1 for t in self.tasks.values() if t.state == TaskState.FAILED)} failed."
                )
            else:
                summary = (
                    f"Workflow '{self.config.name}' failed after {execution_time:.2f} seconds.\n"
                    f"Tasks: {len(self.tasks)} total, "
                    f"{sum(1 for t in self.tasks.values() if t.state == TaskState.SUCCEEDED)} succeeded, "
                    f"{sum(1 for t in self.tasks.values() if t.state == TaskState.FAILED)} failed."
                )
            
            context.add_system_message(summary)
            
            # Add workflow outputs to context
            context.outputs["workflow_id"] = self.id
            context.outputs["workflow_name"] = self.config.name
            context.outputs["workflow_state"] = self.state.value
            context.outputs["execution_time"] = execution_time
            context.outputs["task_results"] = {
                task_id: {
                    "name": task.name,
                    "state": task.state.value,
                    "result": task.result,
                    "error": task.error
                }
                for task_id, task in self.tasks.items()
            }
            
            return context
    
    async def _execute_workflow_tasks(self, context: Context) -> Context:
        """Execute all tasks in the workflow.
        
        Args:
            context: The execution context
            
        Returns:
            The updated context with workflow outputs
        """
        # Create a semaphore to limit concurrent tasks
        self._task_semaphore = asyncio.Semaphore(self.config.max_concurrent_tasks)
        
        # Reset cancel event
        self._cancel_event = asyncio.Event()
        
        # Keep track of running tasks
        running_tasks = []
        
        while not self.all_tasks_completed():
            # Check for workflow cancellation
            if self._cancel_event.is_set():
                # Cancel all running tasks
                for task_future in running_tasks:
                    task_future.cancel()
                
                # Wait for all tasks to complete
                if running_tasks:
                    await asyncio.gather(*running_tasks, return_exceptions=True)
                
                raise asyncio.CancelledError("Workflow execution was canceled")
            
            # Check if we should abort on failure
            if self.config.abort_on_failure and self.any_task_failed():
                # Cancel all running tasks
                for task_future in running_tasks:
                    task_future.cancel()
                
                # Wait for all tasks to complete
                if running_tasks:
                    await asyncio.gather(*running_tasks, return_exceptions=True)
                
                raise ValueError("Workflow aborted due to task failure")
            
            # Get runnable tasks
            runnable_tasks = self.get_runnable_tasks()
            
            if not runnable_tasks and running_tasks:
                # No new tasks to run, but some are still running
                # Wait for any task to complete
                done, running_tasks = await asyncio.wait(
                    running_tasks, 
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # Process completed tasks
                for task_future in done:
                    try:
                        task_result = await task_future
                        self.task_results[task_result.task_id] = task_result
                    except Exception as e:
                        logger.exception(f"Error processing task result: {str(e)}")
                
                continue
            
            if not runnable_tasks and not running_tasks:
                # No tasks to run and none are running
                # This means we're either done or stuck
                if not self.all_tasks_completed():
                    logger.warning("Workflow is stuck. No runnable tasks, but not all tasks completed.")
                    for task_id, task in self.tasks.items():
                        if task.state != TaskState.SUCCEEDED:
                            logger.warning(f"Task {task.name} ({task_id}) is in state {task.state}")
                    
                    raise ValueError("Workflow execution stuck. No runnable tasks but not all tasks completed.")
                
                # All tasks completed
                break
            
            # Start new runnable tasks (up to max_concurrent_tasks)
            for task in runnable_tasks:
                # Acquire semaphore (will wait if too many tasks are running)
                await self._task_semaphore.acquire()
                
                # Start the task
                task_future = asyncio.create_task(self.execute_task(task, context))
                running_tasks.append(task_future)
            
            # Wait a short time before checking again
            await asyncio.sleep(0.1)
        
        # All tasks have completed
        return context
    
    def cancel(self):
        """Cancel the workflow execution."""
        if self.state == WorkflowState.RUNNING:
            self._cancel_event.set()
            self.state = WorkflowState.CANCELED
            self.emit_event("workflow_canceled")
    
    def get_task_by_name(self, name: str) -> Optional[Task]:
        """Get a task by name.
        
        Args:
            name: The task name
            
        Returns:
            The task, or None if not found
        """
        for task in self.tasks.values():
            if task.name == name:
                return task
        return None
    
    def get_task_dependencies(self, task_id: str) -> List[Task]:
        """Get the dependencies of a task.
        
        Args:
            task_id: The task ID
            
        Returns:
            List of dependency tasks
        """
        if task_id not in self.tasks:
            return []
        
        dependency_ids = list(self._task_graph.predecessors(task_id))
        return [self.tasks[dep_id] for dep_id in dependency_ids]
    
    def get_dependent_tasks(self, task_id: str) -> List[Task]:
        """Get the tasks that depend on a task.
        
        Args:
            task_id: The task ID
            
        Returns:
            List of dependent tasks
        """
        if task_id not in self.tasks:
            return []
        
        dependent_ids = list(self._task_graph.successors(task_id))
        return [self.tasks[dep_id] for dep_id in dependent_ids]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation of the workflow
        """
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat(),
            "name": self.config.name,
            "description": self.config.description,
            "state": self.state.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "tasks": {
                task_id: {
                    "id": task.id,
                    "name": task.name,
                    "agent_name": task.agent_name,
                    "state": task.state.value,
                    "dependencies": task.dependencies,
                    "result": task.result,
                    "error": task.error,
                    "retries": task.retries
                }
                for task_id, task in self.tasks.items()
            },
            "metadata": self.metadata
        }
