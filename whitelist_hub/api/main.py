"""FastAPI API for Whitelist Hub."""

import asyncio
import logging
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional, Union

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from motor.motor_asyncio import AsyncIOMotorClient

from ..agents.agent_factory import create_agent
from ..utils.ai_client import AIClient
from ..utils.blockchain_client import BlockchainClient
from ..utils.firecrawl_client import FirecrawlClient
from ..prompts.prompt_manager import PromptManager
from ..core.config import settings
from ..models.analysis_log import AnalysisLog

# Initialize FastAPI app
app = FastAPI(
    title="Whitelist Hub API",
    description="API for automated blockchain project analysis",
    version="0.1.0"
)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("whitelist_hub.api")

# Initialize MongoDB connection
mongo_client = AsyncIOMotorClient(settings.MONGODB_URL)
db = mongo_client[settings.MONGODB_DB_NAME]


# Data models
class Message(BaseModel):
    """Chat message model."""
    role: str = Field(..., description="Role of the message sender (user/assistant)")
    content: str = Field(..., description="Message content")
    timestamp: Optional[datetime] = Field(default_factory=datetime.now)


class ChatRequest(BaseModel):
    """Chat request model."""
    project_id: Optional[str] = Field(None, description="Project ID for existing project")
    message: str = Field(..., description="User message")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for existing conversation")


class ChatResponse(BaseModel):
    """Chat response model."""
    conversation_id: str = Field(..., description="Conversation ID")
    response: str = Field(..., description="Assistant response")
    project_id: Optional[str] = Field(None, description="Project ID if generated")
    messages: List[Message] = Field(..., description="Full conversation history")
    actions: List[Dict[str, Any]] = Field(default_factory=list, description="Actions to perform")


class ProjectAnalysisRequest(BaseModel):
    """Project analysis request model."""
    project_name: str = Field(..., description="Name of the project")
    website: Optional[str] = Field(None, description="Project website URL")
    github_url: Optional[str] = Field(None, description="Project GitHub URL")
    chain_ids: Optional[List[str]] = Field(default_factory=list, description="Blockchain IDs to analyze")
    framework: str = Field("custom", description="Analysis framework to use")


class ProjectRatingRequest(BaseModel):
    """Project rating request model."""
    project_id: str = Field(..., description="Project ID to rate")
    categories: Optional[List[str]] = Field(default=["security", "decentralization", "innovation", "usability"], 
                                           description="Categories to rate")


class ProjectRatingResponse(BaseModel):
    """Project rating response model."""
    project_id: str = Field(..., description="Project ID")
    project_name: str = Field(..., description="Project name")
    overall_rating: float = Field(..., description="Overall project rating (0-100)")
    category_ratings: Dict[str, float] = Field(..., description="Ratings by category (0-100)")
    summary: str = Field(..., description="Rating summary text")
    timestamp: datetime = Field(default_factory=datetime.now)


# Dependencies
async def get_conversation(conversation_id: str):
    """Get conversation by ID."""
    