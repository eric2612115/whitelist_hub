"""Contract models."""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from .security import SecurityFinding, SecurityAssessment
from .function_item import FunctionItem


class InteractionFlow(BaseModel):
    """User interaction flow model."""
    
    name: str
    description: Optional[str] = None
    tags: List[str] = []
    category: Optional[str] = None
    steps: List[Dict[str, Any]] = []
    prerequisites: List[str] = []
    example_transactions: List[str] = []
    estimated_completion_time: Optional[str] = None
    user_level: Optional[str] = None
    diagram_url: Optional[str] = None
    success_criteria: Optional[str] = None


class Contract(BaseModel):
    """Contract model."""
    
    address: str
    blockchain: str
    name: Optional[str] = None
    type: List[str] = []
    bytecode: Optional[str] = None
    abi: List[Dict[str, Any]] = []
    implementation_addresses: List[str] = []
    related_contracts: List[Dict[str, Any]] = []
    function_categories: Dict[str, List[FunctionItem]] = {}
    whitelist_implementation: Optional[Dict[str, Any]] = None
    user_interaction_flows: List[InteractionFlow] = []
    security_assessment: Optional[SecurityAssessment] = None
    metadata: Dict[str, Any] = {}
    transaction_history: Optional[Dict[str, Any]] = None


class ContractCreate(BaseModel):
    """Contract creation model."""
    
    address: str
    blockchain: str
    name: Optional[str] = None
    type: List[str] = []
    bytecode: Optional[str] = None
    abi: List[Dict[str, Any]] = []
    
    class Config:
        """Pydantic config."""
        
        schema_extra = {
            "example": {
                "address": "0x123abc...",
                "blockchain": "ethereum",
                "name": "MyToken",
                "type": ["token", "erc20"],
                "abi": []
            }
        }


class ContractUpdate(BaseModel):
    """Contract update model."""
    
    name: Optional[str] = None
    type: Optional[List[str]] = None
    implementation_addresses: Optional[List[str]] = None
    related_contracts: Optional[List[Dict[str, Any]]] = None
    function_categories: Optional[Dict[str, List[FunctionItem]]] = None
    whitelist_implementation: Optional[Dict[str, Any]] = None
    user_interaction_flows: Optional[List[InteractionFlow]] = None
    security_assessment: Optional[SecurityAssessment] = None
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        """Pydantic config."""
        
        schema_extra = {
            "example": {
                "name": "UpdatedTokenName",
                "type": ["token", "erc20", "upgradeable"],
                "implementation_addresses": ["0x456def..."]
            }
        }


class ContractInDB(Contract):
    """Contract model with DB fields."""
    
    id: str = Field(..., alias="_id")
    project_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
