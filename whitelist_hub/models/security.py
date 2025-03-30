"""Security assessment data models."""

from typing import Dict, List, Optional
from pydantic import BaseModel

from .function_item import PrivilegedRole


class SecurityFinding(BaseModel):
    """Security finding in a contract."""
    
    type: str  # "access-control", "reentrancy", "overflow", etc.
    severity: str  # "critical", "high", "medium", "low", "informational"
    title: str
    description: str
    affected_functions: List[str] = []
    vulnerable_patterns: List[str] = []
    impact: str
    recommendation: str
    confidence: str  # "high", "medium", "low"
    cwe_id: Optional[str] = None  # Common Weakness Enumeration ID if applicable
    references: List[str] = []  # Similar vulnerabilities or documentation links


class SecurityAssessment(BaseModel):
    """Security assessment for a contract."""
    
    risk_level: str  # "high", "medium", "low"
    findings: List[SecurityFinding] = []
    privileged_roles: List[PrivilegedRole] = []
