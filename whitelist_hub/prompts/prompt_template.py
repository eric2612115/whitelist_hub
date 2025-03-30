"""Prompt template management."""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class EffectivenessMetrics(BaseModel):
    """Metrics for prompt template effectiveness."""
    
    avg_score: Optional[float] = None
    uses: int = 0
    successes: int = 0
    success_rate: Optional[float] = None


class PromptTemplate(BaseModel):
    """Prompt template model."""
    
    id: Optional[str] = Field(None, alias="_id")
    name: str
    version: int = 1
    content: str
    author: str = "system"
    change_notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    effectiveness_metrics: EffectivenessMetrics = Field(default_factory=EffectivenessMetrics)
    
    class Config:
        """Pydantic model configuration."""
        
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class PromptTemplateMetadata(BaseModel):
    """Metadata for prompt templates."""
    
    id: Optional[str] = Field(None, alias="_id")
    name: str
    current_version: int = 1
    category: Optional[str] = None
    agent_type: Optional[str] = None
    state: Optional[str] = None
    description: Optional[str] = None
    
    class Config:
        """Pydantic model configuration."""
        
        populate_by_name = True
