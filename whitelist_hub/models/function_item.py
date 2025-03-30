"""Function and parameter data models."""

from typing import Any, List, Optional
from pydantic import BaseModel, Field


class ParameterItem(BaseModel):
    """Smart contract function parameter."""
    
    name: str
    type: str
    description: Optional[str] = None
    indexed: bool = False  # For event parameters
    components: Optional[List["ParameterItem"]] = None  # For complex types
    example_value: Optional[Any] = None
    constraints: Optional[str] = None  # Any constraints on the parameter


class RiskAssessment(BaseModel):
    """Risk assessment for a function."""
    
    level: str  # "high", "medium", "low", "none"
    description: Optional[str] = None


class FunctionItem(BaseModel):
    """Smart contract function details."""
    
    name: str
    signature: str
    inputs: List[ParameterItem] = []
    outputs: List[ParameterItem] = []
    state_mutability: Optional[str] = None
    description: Optional[str] = None
    purpose: Optional[str] = None
    is_entry_point: bool = False
    requires_auth: bool = False
    auth_role: Optional[str] = None
    user_accessible: bool = False
    gas_estimate: Optional[int] = None
    related_functions: List[str] = []
    usage_frequency: Optional[str] = None  # "high", "medium", "low"
    risk_assessment: Optional[RiskAssessment] = None


# Resolve forward reference for ParameterItem components
ParameterItem.model_rebuild()
