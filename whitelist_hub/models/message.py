"""Message models for Whitelist Hub."""

import uuid
from enum import Enum
from typing import Dict, Any, List, Optional
from datetime import datetime


class MessageType(str, Enum):
    """Enum for message types."""
    
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    ERROR = "error"
    THINKING = "thinking"
    RAW = "raw"


class MessageStructure:
    """Helper class for formatting messages."""
    
    @staticmethod
    def format_message(role: str, content: str, message_id: Optional[str] = None) -> Dict[str, Any]:
        """Format a message.
        
        Args:
            role: Message role (user/assistant/system)
            content: Message content
            message_id: Optional message ID
            
        Returns:
            Formatted message
        """
        return {
            "id": message_id or str(uuid.uuid4()),
            "type": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
    
    @staticmethod
    def format_ai_response(content: str, message_id: Optional[str] = None) -> Dict[str, Any]:
        """Format an AI response message.
        
        Args:
            content: Message content
            message_id: Optional message ID
            
        Returns:
            Formatted message
        """
        return MessageStructure.format_message(MessageType.ASSISTANT, content, message_id)
    
    @staticmethod
    def format_system(content: str, message_id: Optional[str] = None) -> Dict[str, Any]:
        """Format a system message.
        
        Args:
            content: Message content
            message_id: Optional message ID
            
        Returns:
            Formatted message
        """
        return MessageStructure.format_message(MessageType.SYSTEM, content, message_id)
    
    @staticmethod
    def format_error(content: str, message_id: Optional[str] = None) -> Dict[str, Any]:
        """Format an error message.
        
        Args:
            content: Message content
            message_id: Optional message ID
            
        Returns:
            Formatted message
        """
        return MessageStructure.format_message(MessageType.ERROR, content, message_id)
    
    @staticmethod
    def format_thinking(message_id: Optional[str] = None) -> Dict[str, Any]:
        """Format a thinking message.
        
        Args:
            message_id: Optional message ID
            
        Returns:
            Formatted message
        """
        return {
            "id": message_id or str(uuid.uuid4()),
            "type": MessageType.THINKING,
            "timestamp": datetime.now().isoformat()
        }
    
    @staticmethod
    def format_raw(data: Dict[str, Any], message_id: Optional[str] = None) -> Dict[str, Any]:
        """Format a raw message.
        
        Args:
            data: Raw message data
            message_id: Optional message ID
            
        Returns:
            Formatted message
        """
        data["id"] = message_id or str(uuid.uuid4())
        data["type"] = MessageType.RAW
        data["timestamp"] = datetime.now().isoformat()
        return data
