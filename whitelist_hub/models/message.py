"""Message models for project analysis communication."""

import enum
from datetime import datetime
import uuid
from typing import Dict, Any, Optional, List


class MessageType(str, enum.Enum):
    """Message type enumeration."""
    
    NORMAL = "normal"
    THINKING = "thinking"
    ERROR = "error"
    SYSTEM = "system"
    ACTION = "action"
    RESULT = "result"


class MessageStructure:
    """Helper class for message structure."""
    
    @staticmethod
    def format_message(role: str, text: str, message_type: MessageType = MessageType.NORMAL) -> Dict[str, Any]:
        """Format a message.
        
        Args:
            role: Message sender role
            text: Message text
            message_type: Message type
            
        Returns:
            Formatted message
        """
        return {
            "id": str(uuid.uuid4()),
            "message_type": message_type.value,
            "role": role,
            "text": text,
            "timestamp": datetime.now().isoformat()
        }
    
    @staticmethod
    def format_ai_response(text: str) -> Dict[str, Any]:
        """Format an AI response message.
        
        Args:
            text: Message text
            
        Returns:
            Formatted message
        """
        return MessageStructure.format_message("assistant", text)
    
    @staticmethod
    def format_thinking() -> Dict[str, Any]:
        """Format a thinking status message.
        
        Returns:
            Formatted message
        """
        return {
            "id": str(uuid.uuid4()),
            "message_type": MessageType.THINKING.value,
            "role": "assistant",
            "text": "Thinking...",
            "timestamp": datetime.now().isoformat()
        }
    
    @staticmethod
    def format_error(text: str) -> Dict[str, Any]:
        """Format an error message.
        
        Args:
            text: Error message
            
        Returns:
            Formatted message
        """
        return {
            "id": str(uuid.uuid4()),
            "message_type": MessageType.ERROR.value,
            "role": "system",
            "text": text,
            "timestamp": datetime.now().isoformat()
        }
    
    @staticmethod
    def format_system(text: str) -> Dict[str, Any]:
        """Format a system message.
        
        Args:
            text: System message
            
        Returns:
            Formatted message
        """
        return {
            "id": str(uuid.uuid4()),
            "message_type": MessageType.SYSTEM.value,
            "role": "system",
            "text": text,
            "timestamp": datetime.now().isoformat()
        }
    
    @staticmethod
    def format_action(action_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Format an action message.
        
        Args:
            action_type: Action type
            params: Action parameters
            
        Returns:
            Formatted message
        """
        return {
            "id": str(uuid.uuid4()),
            "message_type": MessageType.ACTION.value,
            "role": "assistant",
            "action_type": action_type,
            "params": params,
            "timestamp": datetime.now().isoformat()
        }
    
    @staticmethod
    def format_result(action_type: str, result: Any) -> Dict[str, Any]:
        """Format an action result message.
        
        Args:
            action_type: Action type
            result: Action result
            
        Returns:
            Formatted message
        """
        return {
            "id": str(uuid.uuid4()),
            "message_type": MessageType.RESULT.value,
            "role": "system",
            "action_type": action_type,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
