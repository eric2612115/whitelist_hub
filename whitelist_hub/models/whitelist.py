"""Whitelist mechanism data models."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class WhitelistProperties(BaseModel):
    """Properties of a whitelist mechanism."""
    
    time_limited: bool = False
    tiered: bool = False
    transferable: bool = False
    additional_requirements: List[str] = []


class WhitelistMechanism(BaseModel):
    """Whitelist mechanism details."""
    
    name: str
    description: str
    contract_address: str
    mechanism_type: Optional[str] = None  # "merkle", "mapping", "token-based", etc.
    properties: WhitelistProperties = Field(default_factory=WhitelistProperties)


class WhitelistImplementation(BaseModel):
    """Technical details of whitelist implementation."""
    
    mechanism: Optional[str] = None  # "merkle", "mapping", "token-based", etc.
    key_functions: List[str] = []
    data_storage: Optional[str] = None  # "onchain", "merkle", "hybrid"
    access_control: Optional[str] = None  # "role-based", "ownership", "multisig"
    
    # Additional technical details
    known_members: Optional[List[str]] = None
    known_non_members: Optional[List[str]] = None
    checker_function: Optional[Dict] = None
    merkle_root: Optional[str] = None
    test_results: Optional[Dict] = None
