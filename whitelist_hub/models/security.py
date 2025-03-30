"""Security models."""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel

from .function_item import PrivilegedRole


class SecurityFinding(BaseModel):
    """Security finding model."""
    
    type: str
    severity: str
    title: str
    description: str
    affected_functions: List[str] = []
    vulnerable_patterns: List[str] = []
    impact: Optional[str] = None
    recommendation: Optional[str] = None
    confidence: Optional[str] = None
    cwe_id: Optional[str] = None
    references: List[str] = []


class SecurityAssessment(BaseModel):
    """Security assessment model."""
    
    risk_level: str
    findings: List[SecurityFinding] = []
    privileged_roles: List[PrivilegedRole] = []
