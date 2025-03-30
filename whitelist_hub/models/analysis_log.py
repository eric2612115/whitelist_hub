"""Analysis log data models."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AnalysisStep(BaseModel):
    """Step in an analysis process."""
    
    step: int
    state: str
    observation: str
    reasoning: str
    action: str
    result: Optional[Any] = None
    confidence: float
    execution_time_ms: int


class AgentChallenge(BaseModel):
    """Challenge encountered during analysis."""
    
    type: str
    description: str
    resolution: Optional[str] = None
    impact_on_analysis: Optional[str] = None


class PromptStatistics(BaseModel):
    """Statistics about prompts used in analysis."""
    
    total_tokens: int
    prompt_versions_used: List[str] = []
    average_response_time_ms: float


class AgentPerformanceMetrics(BaseModel):
    """Performance metrics for an agent."""
    
    decisiveness: float  # How quickly agent reached conclusions
    thoroughness: float  # How comprehensive the analysis was
    accuracy: Optional[float] = None  # If verifiable, how accurate the results were
    adaptation: float  # How well agent adapted to challenges


class AnalysisLog(BaseModel):
    """Log of an analysis process."""
    
    id: Optional[str] = Field(None, alias="_id")
    project_id: str
    contract_id: str
    analysis_id: str
    agent_type: str
    timestamp: datetime = Field(default_factory=datetime.now)
    analysis_steps: List[AnalysisStep] = []
    challenges: List[AgentChallenge] = []
    prompt_statistics: Optional[PromptStatistics] = None
    final_result: Optional[Any] = None
    execution_time_ms: int
    agent_performance_metrics: Optional[AgentPerformanceMetrics] = None
    version: int = 1
    
    class Config:
        """Pydantic model configuration."""
        
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
