"""Contract data models."""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

from .function_item import FunctionItem
from .interaction_flow import InteractionFlow
from .security import SecurityFinding, SecurityAssessment
from .whitelist import WhitelistImplementation


class RelatedContract(BaseModel):
    """Relationship to another contract."""
    
    address: str
    relationship: str  # "calls", "implements", "factory", etc.
    relationship_details: Optional[str] = None


class ContractMetadata(BaseModel):
    """Metadata for a contract."""
    
    discovered_at: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)
    analysis_confidence: Dict[str, float] = {
        "overall": 0.0,
        "proxy_detection": 0.0,
        "function_classification": 0.0,
        "whitelist_analysis": 0.0
    }
    verified_source: bool = False
    compiler_version: Optional[str] = None


class SignificantEvent(BaseModel):
    """Significant event in contract history."""
    
    date: datetime
    tx_hash: str
    description: str
    impact: str  # "high", "medium", "low"


class TransactionHistory(BaseModel):
    """Transaction history for a contract."""
    
    first_transaction: Optional[datetime] = None
    latest_transaction: Optional[datetime] = None
    transaction_count: int = 0
    significant_events: List[SignificantEvent] = []


class PrivilegedRole(BaseModel):
    """Role with special privileges in the contract."""
    
    role: str
    capabilities: List[str] = []
    controller: str  # Address or description


class ContractBase(BaseModel):
    """Base contract data."""
    
    address: str
    blockchain: str
    name: Optional[str] = None
    type: List[str] = []  # "proxy", "implementation", "router", "factory", etc.


class ContractCreate(ContractBase):
    """Contract data for creation."""
    
    project_id: str
    bytecode: Optional[str] = None
    abi: Optional[List[dict]] = None


class ContractUpdate(BaseModel):
    """Contract data for updates."""
    
    name: Optional[str] = None
    type: Optional[List[str]] = None
    bytecode: Optional[str] = None
    abi: Optional[List[dict]] = None
    implementation_addresses: Optional[List[str]] = None


class Contract(ContractBase):
    """Contract data with relationships and analysis."""
    
    id: str = Field(alias="_id")
    project_id: str
    bytecode: Optional[str] = None
    abi: Optional[List[dict]] = None
    implementation_addresses: List[str] = []
    related_contracts: List[RelatedContract] = []
    function_categories: Dict[str, List[FunctionItem]] = Field(default_factory=dict)
    whitelist_implementation: Optional[WhitelistImplementation] = None
    user_interaction_flows: List[InteractionFlow] = []
    security_assessment: Optional[SecurityAssessment] = None
    metadata: ContractMetadata = Field(default_factory=ContractMetadata)
    transaction_history: TransactionHistory = Field(default_factory=TransactionHistory)
    
    class Config:
        """Pydantic model configuration."""
        
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class ContractInDB(Contract):
    """Contract data as stored in database."""
    
    pass
