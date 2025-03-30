"""Project data models."""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, HttpUrl

from .whitelist import WhitelistMechanism


class SocialLinks(BaseModel):
    """Social media links for a project."""
    
    twitter: Optional[str] = None
    telegram: Optional[str] = None
    discord: Optional[str] = None
    medium: Optional[str] = None


class ChangeHistory(BaseModel):
    """Record of changes to a project."""
    
    timestamp: datetime = Field(default_factory=datetime.now)
    field_changed: str
    old_value: Any
    new_value: Any
    reason: Optional[str] = None


class AnalysisSummary(BaseModel):
    """Summary of project analysis results."""
    
    has_whitelist: bool = False
    has_token_sale: bool = False
    has_staking: bool = False
    has_governance: bool = False
    security_score: float = 0.0
    complexity_score: float = 0.0
    uniqueness_score: float = 0.0
    whitelist_accessibility: str = "none"  # "none", "open", "moderate", "restricted"


class ProjectMetadata(BaseModel):
    """Metadata for a project."""
    
    discovered_at: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)
    analysis_version: int = 1
    analysis_confidence: float = 0.0
    data_completeness: float = 0.0


class ProjectBase(BaseModel):
    """Base project data."""
    
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    blockchain: Optional[str] = None
    website: Optional[HttpUrl] = None
    github_url: Optional[HttpUrl] = None
    defillama_ranking: Optional[int] = None
    tvl: Optional[float] = None


class ProjectCreate(ProjectBase):
    """Project data for creation."""
    
    pass


class ProjectUpdate(BaseModel):
    """Project data for updates."""
    
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    blockchain: Optional[str] = None
    website: Optional[HttpUrl] = None
    github_url: Optional[HttpUrl] = None
    defillama_ranking: Optional[int] = None
    tvl: Optional[float] = None
    social_links: Optional[SocialLinks] = None


class Project(ProjectBase):
    """Project data with relationships."""
    
    id: str = Field(alias="_id")
    contracts: List[str] = []
    analysis_summary: Optional[AnalysisSummary] = None
    whitelist_mechanisms: List[WhitelistMechanism] = []
    metadata: ProjectMetadata = Field(default_factory=ProjectMetadata)
    social_links: Optional[SocialLinks] = None
    change_history: List[ChangeHistory] = []
    
    class Config:
        """Pydantic model configuration."""
        
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class ProjectInDB(Project):
    """Project data as stored in database."""
    
    pass
