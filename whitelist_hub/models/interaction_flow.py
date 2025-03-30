"""User interaction flow data models."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class ErrorCase(BaseModel):
    """Error case for an interaction step."""
    
    condition: str
    error_message: str
    mitigation: Optional[str] = None


class InteractionStep(BaseModel):
    """Step in an interaction flow."""
    
    step: int
    description: str
    contract_address: str
    function_name: str
    inputs: List[Any] = []
    expected_outcome: str
    error_cases: List[ErrorCase] = []
    gas_estimation: Optional[int] = None


class InteractionFlow(BaseModel):
    """User interaction flow."""
    
    name: str
    description: str
    tags: List[str] = []
    category: str  # "whitelist", "token-sale", "staking", etc.
    steps: List[InteractionStep] = []
    prerequisites: List[str] = []
    example_transactions: List[str] = []
    estimated_completion_time: Optional[str] = None
    user_level: Optional[str] = None  # "beginner", "intermediate", "advanced"
    diagram_url: Optional[str] = None
    success_criteria: Optional[str] = None
    validation: Optional[Dict] = None  # Results of flow validation
