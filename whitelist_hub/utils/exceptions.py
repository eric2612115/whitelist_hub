"""
Custom exceptions for the Whitelist Hub application.
"""


class WhitelistHubError(Exception):
    """Base class for all Whitelist Hub exceptions."""
    pass


class AgentError(WhitelistHubError):
    """Base class for agent-related errors."""
    pass


class AgentTimeoutError(AgentError):
    """Raised when an agent execution times out."""
    pass


class AgentExecutionError(AgentError):
    """Raised when an agent execution fails."""
    pass


class ToolError(WhitelistHubError):
    """Base class for tool-related errors."""
    pass


class ToolExecutionError(ToolError):
    """Raised when a tool execution fails."""
    pass


class ToolNotFoundError(ToolError):
    """Raised when a tool is not found."""
    pass


class TaskError(WhitelistHubError):
    """Base class for task-related errors."""
    pass


class WorkflowError(WhitelistHubError):
    """Base class for workflow-related errors."""
    pass


class SessionError(WhitelistHubError):
    """Base class for session-related errors."""
    pass


class ContextError(WhitelistHubError):
    """Base class for context-related errors."""
    pass


class AIModelError(WhitelistHubError):
    """Base class for AI model-related errors."""
    pass


class AIModelExecutionError(AIModelError):
    """Raised when an AI model execution fails."""
    pass


class AIModelTimeoutError(AIModelError):
    """Raised when an AI model execution times out."""
    pass


class ConfigurationError(WhitelistHubError):
    """Raised when there is a configuration error."""
    pass


class DatabaseError(WhitelistHubError):
    """Base class for database-related errors."""
    pass


class ValidationError(WhitelistHubError):
    """Raised when validation fails."""
    pass
