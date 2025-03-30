"""API endpoints for Whitelist Hub."""

import os
import json
import logging
import asyncio
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .connection_manager import ProjectAnalysisManager
from .project_analysis_service import ProjectAnalysisService
from ..models.message import MessageStructure
from ..utils.ai_client import AIClient
from ..utils.firecrawl_client import FirecrawlClient
from ..prompts.prompt_manager import PromptManager
from ..services.defillama_service import DefiLlamaService
from ..utils.blockchain_client import BlockchainClient
from ..agents.agent_factory import create_agent
from ..core.config import settings
from ..models.message import MessageType

logger = logging.getLogger(__name__)

# Initialize services
prompt_manager = PromptManager(use_db=False, templates_dir="whitelist_hub/prompts/templates")
ai_client = AIClient()
blockchain_client = BlockchainClient()
firecrawl_client = FirecrawlClient()
defillama_service = DefiLlamaService()

# Initialize project analysis service
project_analysis_service = ProjectAnalysisService(
    ai_client=ai_client,
    prompt_manager=prompt_manager,
    blockchain_client=blockchain_client,
    firecrawl_client=firecrawl_client,
    defillama_service=defillama_service
)

# Initialize connection manager
connection_manager = ProjectAnalysisManager()

# Define API models
class ProjectStartRequest(BaseModel):
    """Request model for starting a project analysis."""
    
    project_name: str = Field(..., description="Project name to analyze")
    website: Optional[str] = Field(None, description="Project website URL")
    github_url: Optional[str] = Field(None, description="Project GitHub URL")

class MessageRequest(BaseModel):
    """Request model for sending a message."""
    
    text: str = Field(..., description="Message text")

class ContractAnalysisRequest(BaseModel):
    """Request model for analyzing a contract."""
    
    contract_address: str = Field(..., description="Contract address to analyze")
    blockchain: str = Field("ethereum", description="Blockchain name (e.g., ethereum, bsc)")

class SessionResponse(BaseModel):
    """Response model for session creation."""
    
    session_id: str = Field(..., description="Session ID")
    created_at: str = Field(..., description="Session creation timestamp")

# Create FastAPI app
app = FastAPI(
    title="Whitelist Hub API",
    description="API for blockchain project analysis with focus on whitelist mechanisms",
    version="0.1.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency for getting project analysis service
def get_project_analysis_service():
    """Dependency for getting project analysis service."""
    return project_analysis_service

# API Routes
@app.get("/", tags=["general"])
async def root():
    """Root endpoint for health check."""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/sessions", response_model=SessionResponse, tags=["session"])
async def create_session():
    """Create a new analysis session."""
    session_id = str(uuid.uuid4())
    connection_manager.session_data[session_id] = {
        "messages": [],
        "created_at": datetime.now().isoformat(),
        "last_active": datetime.now().isoformat(),
        "project_data": None,
        "analysis_status": "not_started"
    }
    
    return {
        "session_id": session_id,
        "created_at": connection_manager.session_data[session_id]["created_at"]
    }

@app.get("/api/sessions/{session_id}", tags=["session"])
async def get_session(session_id: str):
    """Get session data."""
    if session_id not in connection_manager.session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return connection_manager.session_data[session_id]

@app.post("/api/sessions/{session_id}/projects", tags=["project"])
async def start_project_analysis(
    session_id: str,
    project_request: ProjectStartRequest,
    background_tasks: BackgroundTasks,
    service: ProjectAnalysisService = Depends(get_project_analysis_service)
):
    """Start a new project analysis."""
    if session_id not in connection_manager.session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Update session data
    connection_manager.update_session_data(session_id, {
        "project_name": project_request.project_name,
        "website": project_request.website,
        "github_url": project_request.github_url,
        "analysis_status": "in_progress"
    })
    
    # Define message callback
    async def message_callback(message):
        await connection_manager.send_message(session_id, message)
    
    # Start analysis in background
    background_tasks.add_task(
        analyze_project_background,
        service=service,
        session_id=session_id,
        project_name=project_request.project_name,
        website=project_request.website,
        github_url=project_request.github_url,
        message_callback=message_callback
    )
    
    return {
        "status": "started",
        "session_id": session_id,
        "project_name": project_request.project_name,
        "timestamp": datetime.now().isoformat()
    }

async def analyze_project_background(
    service: ProjectAnalysisService,
    session_id: str,
    project_name: str,
    website: Optional[str] = None,
    github_url: Optional[str] = None,
    message_callback = None
):
    """Analyze project in background."""
    try:
        # Analyze project
        result = await service.analyze_project(
            project_name=project_name,
            website=website,
            github_url=github_url,
            session_id=session_id,
            message_callback=message_callback
        )
        
        # Update session data
        connection_manager.update_project_data(session_id, result)
        connection_manager.set_analysis_status(session_id, "completed")
        
        # Send completion message
        if message_callback:
            await message_callback(
                {
                    "type": "analysis_completed",
                    "project_name": project_name,
                    "timestamp": datetime.now().isoformat()
                }
            )
    except Exception as e:
        logger.exception(f"Error analyzing project: {e}")
        connection_manager.set_analysis_status(session_id, "error")
        
        # Send error message
        if message_callback:
            await message_callback(
                MessageStructure.format_error(f"Error analyzing project: {str(e)}")
            )

@app.post("/api/sessions/{session_id}/contracts", tags=["contract"])
async def analyze_contract(
    session_id: str,
    contract_request: ContractAnalysisRequest,
    background_tasks: BackgroundTasks,
    service: ProjectAnalysisService = Depends(get_project_analysis_service)
):
    """Analyze a specific contract."""
    if session_id not in connection_manager.session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Define message callback
    async def message_callback(message):
        await connection_manager.send_message(session_id, message)
    
    # Start analysis in background
    background_tasks.add_task(
        analyze_contract_background,
        service=service,
        session_id=session_id,
        contract_address=contract_request.contract_address,
        blockchain=contract_request.blockchain,
        message_callback=message_callback
    )
    
    return {
        "status": "started",
        "session_id": session_id,
        "contract_address": contract_request.contract_address,
        "blockchain": contract_request.blockchain,
        "timestamp": datetime.now().isoformat()
    }

async def analyze_contract_background(
    service: ProjectAnalysisService,
    session_id: str,
    contract_address: str,
    blockchain: str,
    message_callback = None
):
    """Analyze contract in background."""
    try:
        # Analyze contract
        result = await service.analyze_specific_contract(
            contract_address=contract_address,
            blockchain=blockchain,
            message_callback=message_callback
        )
        
        # Update session data
        contracts = connection_manager.get_session_data(session_id).get("contracts", [])
        contracts.append(result)
        connection_manager.update_session_data(session_id, {"contracts": contracts})
        
        # Send completion message
        if message_callback:
            await message_callback(
                {
                    "type": "contract_analysis_completed",
                    "contract_address": contract_address,
                    "blockchain": blockchain,
                    "timestamp": datetime.now().isoformat()
                }
            )
    except Exception as e:
        logger.exception(f"Error analyzing contract: {e}")
        
        # Send error message
        if message_callback:
            await message_callback(
                MessageStructure.format_error(f"Error analyzing contract: {str(e)}")
            )

@app.post("/api/sessions/{session_id}/messages", tags=["message"])
async def send_message(
    session_id: str,
    message_request: MessageRequest,
    service: ProjectAnalysisService = Depends(get_project_analysis_service)
):
    """Send a message in a session."""
    if session_id not in connection_manager.session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Add user message to session
    user_message = MessageStructure.format_message("user", message_request.text)
    await connection_manager.save_message(session_id, "user", message_request.text)
    
    # Process request as a conversation about the project
    # This would typically use a conversational agent specialized for project analysis
    # For now, we'll just echo back a response with some template text
    
    # Send thinking status
    thinking_message = MessageStructure.format_thinking()
    await connection_manager.send_message(session_id, thinking_message)
    
    # Simulate some processing time
    await asyncio.sleep(1)
    
    # Generate a response based on session data
    session_data = connection_manager.get_session_data(session_id)
    project_data = session_data.get("project_data")
    
    if project_data:
        # If we have project data, craft a response about the project
        project_name = session_data.get("project_name", "the project")
        rating = project_data.get("rating", {})
        
        if "whitelist" in message_request.text.lower():
            # Response about whitelist mechanisms
            whitelist_mechanisms = project_data.get("whitelist_mechanisms", [])
            if whitelist_mechanisms:
                response_text = f"I found {len(whitelist_mechanisms)} whitelist mechanism(s) in {project_name}. "
                for i, wl in enumerate(whitelist_mechanisms[:3]):  # Limit to first 3
                    mechanism_type = wl.get("mechanism_type", "unknown")
                    response_text += f"Mechanism {i+1} is a {mechanism_type} implementation. "
                
                if rating:
                    response_text += f"The whitelist implementation received a score of {rating.get('factors', {}).get('whitelist_implementation', 0)}/10."
            else:
                response_text = f"I didn't find any whitelist mechanisms in {project_name}."
        
        elif "contract" in message_request.text.lower():
            # Response about contracts
            contracts = project_data.get("contract_analyses", [])
            if contracts:
                response_text = f"I analyzed {len(contracts)} contract(s) for {project_name}. "
                for i, contract in enumerate(contracts[:3]):  # Limit to first 3
                    address = contract.get("address", "unknown")
                    is_proxy = "a proxy contract" if contract.get("is_proxy") else "a regular contract"
                    response_text += f"Contract {i+1} ({address[:8]}...) is {is_proxy}. "
            else:
                response_text = f"I didn't find any contracts for {project_name}."
        
        elif "rating" in message_request.text.lower() or "score" in message_request.text.lower():
            # Response about rating
            if rating:
                response_text = f"{project_name} received a {rating.get('rating', 'N/A')} rating with a score of {rating.get('overall_score', 0)}/100. "
                response_text += rating.get('explanation', '')
            else:
                response_text = f"I haven't calculated a rating for {project_name} yet."
        
        elif "aave" in message_request.text.lower() and "analyze" in message_request.text.lower():
            # Special case for AAVE analysis request
            response_text = f"I'll analyze AAVE for you. Starting the analysis process now. This will take some time as I need to crawl information about AAVE's contracts, analyze their functionality, and generate a comprehensive report with rating."
            # Start AAVE analysis in a background task
            background_tasks = BackgroundTasks()
            background_tasks.add_task(
                analyze_project_background,
                service=service,
                session_id=session_id,
                project_name="AAVE",
                website="https://aave.com",
                github_url="https://github.com/aave",
                message_callback=lambda msg: connection_manager.send_message(session_id, msg)
            )
        
        else:
            # Generic response about the project
            response_text = f"I've analyzed {project_name} and found it to be "
            if rating:
                score = rating.get('overall_score', 50)
                if score >= 70:
                    response_text += "a well-implemented project with strong technical foundations."
                elif score >= 50:
                    response_text += "a decent project with some good technical aspects."
                else:
                    response_text += "a project with several technical areas that could be improved."
            else:
                response_text += "an interesting project. You can ask me about its contracts, whitelist mechanisms, or overall rating."
    else:
        # If no project data, provide a generic response
        if "aave" in message_request.text.lower() and any(term in message_request.text.lower() for term in ["analyze", "analysis", "study", "investigate"]):
            # Start AAVE analysis
            response_text = "I'll analyze AAVE for you. Starting the analysis process now. This will take some time as I need to crawl information about AAVE's contracts, analyze their functionality, and generate a comprehensive report with rating."
            
            # Create background task for analysis
            background_tasks = BackgroundTasks()
            background_tasks.add_task(
                analyze_project_background,
                service=service,
                session_id=session_id,
                project_name="AAVE",
                website="https://aave.com",
                github_url="https://github.com/aave",
                message_callback=lambda msg: connection_manager.send_message(session_id, msg)
            )
            
            # Update session data
            connection_manager.update_session_data(session_id, {
                "project_name": "AAVE",
                "website": "https://aave.com",
                "github_url": "https://github.com/aave",
                "analysis_status": "in_progress"
            })
        
        elif session_data.get("analysis_status") == "in_progress":
            response_text = "I'm still analyzing the project. Please wait until the analysis is complete."
        else:
            response_text = "I don't have any project data yet. You can ask me to analyze a specific project like AAVE by saying 'Analyze AAVE'."
    
    # Save and send response
    assistant_message = MessageStructure.format_ai_response(response_text)
    await connection_manager.save_message(session_id, "assistant", response_text)
    await connection_manager.send_message(session_id, assistant_message)
    
    return assistant_message

@app.get("/api/sessions/{session_id}/messages", tags=["message"])
async def get_messages(session_id: str):
    """Get all messages in a session."""
    if session_id not in connection_manager.session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "messages": connection_manager.get_messages(session_id)
    }

@app.get("/api/projects/{project_name}", tags=["project"])
async def get_project_data(
    project_name: str,
    service: ProjectAnalysisService = Depends(get_project_analysis_service)
):
    """Get project data by name."""
    # Try to get from cache first
    cache_key = project_name.lower()
    if cache_key in service.project_cache:
        return service.project_cache[cache_key]
    
    # Not in cache, return 404
    raise HTTPException(status_code=404, detail="Project not found")

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time communication."""
    # Connect client
    success = await connection_manager.connect(session_id, websocket)
    if not success:
        return
    
    # Send welcome message
    welcome_message = MessageStructure.format_system(
        "Welcome to Whitelist Hub! You can start by analyzing a project or a specific contract. For example, try 'Analyze AAVE'."
    )
    await connection_manager.send_message(session_id, welcome_message)
    
    try:
        # Handle messages
        while True:
            data = await websocket.receive_text()
            try:
                message_data = json.loads(data)
                await connection_manager.handle_client_message(session_id, message_data)
            except json.JSONDecodeError:
                await connection_manager.send_message(
                    session_id,
                    MessageStructure.format_error("Invalid message format. Please send valid JSON.")
                )
    except WebSocketDisconnect:
        connection_manager.disconnect(session_id)
    except Exception as e:
        logger.exception(f"Error in WebSocket handler: {e}")
        try:
            await connection_manager.send_message(
                session_id,
                MessageStructure.format_error(f"Error: {str(e)}")
            )
        except:
            pass
        connection_manager.disconnect(session_id)
