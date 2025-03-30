"""Prompt template models and utilities."""

from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class PromptTemplateMetadata(BaseModel):
    """Metadata for a prompt template."""
    
    name: str = Field(..., description="Template name")
    current_version: int = Field(..., description="Current version")
    versions: List[Dict[str, Any]] = Field([], description="Version history")


class PromptTemplate(BaseModel):
    """Model for a prompt template."""
    
    name: str = Field(..., description="Template name")
    version: int = Field(..., description="Template version")
    content: str = Field(..., description="Template content")
    author: str = Field(..., description="Author of the template")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    change_notes: Optional[str] = Field(None, description="Notes about the change")
    effectiveness_metrics: Dict[str, Any] = Field(
        default_factory=lambda: {
            "avg_score": None,
            "uses": 0,
            "successes": 0,
            "success_rate": None
        },
        description="Effectiveness metrics"
    )
    
    def dict(self, *args, **kwargs):
        """Convert to dictionary.
        
        Args:
            *args: Additional arguments
            **kwargs: Additional keyword arguments
            
        Returns:
            Dictionary representation
        """
        result = super().dict(*args, **kwargs)
        # Convert datetime to string for proper serialization
        if isinstance(result.get("created_at"), datetime):
            result["created_at"] = result["created_at"].isoformat()
        return result
