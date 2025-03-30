"""Function item models."""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel


class ParameterItem(BaseModel):
    """Parameter item model."""
    
    name: str
    type: str
    description: Optional[str] = None
    indexed: Optional[bool] = None
    components: Optional[List["ParameterItem"]] = None
    example_value: Optional[Any] = None
    constraints: Optional[str] = None


class PrivilegedRole(BaseModel):
    """Privileged role model."""
    
    role: str
    capabilities: List[str]
    controller: Optional[str] = None


class FunctionItem(BaseModel):
    """Function item model."""
    
    name: str
    signature: str
    inputs: List[ParameterItem] = []
    outputs: List[ParameterItem] = []
    state_mutability: Optional[str] = None
    description: Optional[str] = None
    purpose: Optional[str] = None
    is_entry_point: Optional[bool] = None
    requires_auth: Optional[bool] = None
    auth_role: Optional[str] = None
    user_accessible: Optional[bool] = None
    gas_estimate: Optional[int] = None
    related_functions: List[str] = []
    usage_frequency: Optional[str] = None
    risk_assessment: Optional[Dict[str, Any]] = None


# Update forward references
ParameterItem.update_forward_refs()
