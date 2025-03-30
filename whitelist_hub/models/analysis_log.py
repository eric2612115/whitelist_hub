"""Analysis log models for Whitelist Hub."""

from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field


class AnalysisStep(BaseModel):
    """Model for an analysis step."""
    
    step: int = Field(..., description="Step number")
    state: str = Field(..., description="Agent state during this step")
    observation: str = Field(..., description="Observation from the environment")
    reasoning: str = Field(..., description="Agent's reasoning process")
    action: Dict[str, Any] = Field(..., description="Action taken by the agent")
    result: Optional[Any] = Field(None, description="Result of the action")
    confidence: float = Field(..., description="Confidence in the step's output (0-1)")
    execution_time_ms: int = Field(..., description="Execution time in milliseconds")


class AgentChallenge(BaseModel):
    """Model for an agent challenge."""
    
    type: str = Field(..., description="Type of challenge")
    description: str = Field(..., description="Description of the challenge")
    resolution: Optional[str] = Field(None, description="How the challenge was resolved")
    impact_on_analysis: Optional[str] = Field(None, description="Impact on the analysis")


class AgentPerformanceMetrics(BaseModel):
    """Model for agent performance metrics."""
    
    decisiveness: float = Field(..., description="How effectively the agent progressed to a solution (0-1)")
    thoroughness: float = Field(..., description="Level of detail and completeness in the analysis (0-1)")
    accuracy: Optional[float] = Field(None, description="Accuracy of the analysis results (0-1)")
    adaptation: float = Field(..., description="How well the agent adapted to challenges (0-1)")


class AnalysisLog(BaseModel):
    """Model for an analysis log."""
    
    project_id: str = Field(..., description="Project identifier")
    contract_id: str = Field(..., description="Contract identifier")
    analysis_id: str = Field(..., description="Analysis identifier")
    agent_type: str = Field(..., description="Type of agent that performed the analysis")
    timestamp: datetime = Field(..., description="Analysis timestamp")
    analysis_steps: List[AnalysisStep] = Field([], description="Steps in the analysis process")
    challenges: List[AgentChallenge] = Field([], description="Challenges encountered during analysis")
    prompt_statistics: Dict[str, Any] = Field(..., description="Statistics about prompts used")
    final_result: Dict[str, Any] = Field(..., description="Final analysis result")
    execution_time_ms: int = Field(..., description="Total execution time in milliseconds")
    agent_performance_metrics: AgentPerformanceMetrics = Field(..., description="Agent performance metrics")


class ContractAnalysisResult(BaseModel):
    """Model for contract analysis result."""
    
    contract_address: str = Field(..., description="Contract address")
    blockchain: str = Field(..., description="Blockchain name")
    has_abi: bool = Field(..., description="Whether ABI is available")
    function_count: int = Field(..., description="Number of functions in the contract")
    function_categories: Dict[str, List[str]] = Field(..., description="Function categories")
    has_whitelist: bool = Field(..., description="Whether the contract has whitelist functionality")
    has_owner: bool = Field(..., description="Whether the contract has owner functionality")
    is_proxy: bool = Field(False, description="Whether the contract is a proxy")
    proxy_type: Optional[str] = Field(None, description="Type of proxy contract")
    implementation_address: Optional[str] = Field(None, description="Implementation contract address")
    whitelist_analysis: Optional[Dict[str, Any]] = Field(None, description="Whitelist mechanism analysis")
    verification: Optional[Dict[str, Any]] = Field(None, description="Verification results")
    security_assessment: Optional[Dict[str, Any]] = Field(None, description="Security assessment")


class WhitelistMechanism(BaseModel):
    """Model for whitelist mechanism."""
    
    contract_address: str = Field(..., description="Contract address")
    blockchain: str = Field(..., description="Blockchain name")
    mechanism_type: str = Field(..., description="Type of whitelist mechanism")
    whitelist_functions: List[Dict[str, Any]] = Field(..., description="Whitelist-related functions")
    is_tiered: bool = Field(False, description="Whether the whitelist has tiers")
    is_time_limited: bool = Field(False, description="Whether the whitelist has time limitations")
    data_storage: str = Field(..., description="How whitelist data is stored")
    description: str = Field(..., description="Description of the whitelist mechanism")


class ProjectAnalysisResult(BaseModel):
    """Model for project analysis result."""
    
    project_name: str = Field(..., description="Project name")
    analysis_timestamp: str = Field(..., description="Analysis timestamp")
    website: Optional[str] = Field(None, description="Project website")
    github_url: Optional[str] = Field(None, description="Project GitHub URL")
    project_overview: Dict[str, Any] = Field(..., description="Project overview")
    executive_summary: str = Field(..., description="Executive summary")
    contract_analyses: List[ContractAnalysisResult] = Field(..., description="Contract analyses")
    whitelist_mechanisms: List[WhitelistMechanism] = Field(..., description="Whitelist mechanisms")
    security_assessment: Dict[str, Any] = Field(..., description="Security assessment")
    rating: Dict[str, Any] = Field(..., description="Project rating")
    conclusion_and_recommendations: Dict[str, Any] = Field(..., description="Conclusion and recommendations")
