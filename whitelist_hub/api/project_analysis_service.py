"""Project analysis service for Whitelist Hub."""

import logging
import asyncio
import json
import os
from typing import Dict, List, Any, Optional, Tuple, Callable
from datetime import datetime

from ..models.message import MessageStructure
from ..utils.ai_client import AIClient
from ..utils.blockchain_client import BlockchainClient
from ..utils.firecrawl_client import FirecrawlClient
from ..prompts.prompt_manager import PromptManager
from ..services.defillama_service import DefiLlamaService
from ..agents.crew_factory import create_crew, WhitelistAnalysisCrew
from ..db.mongodb import get_collection, PROJECTS_COLLECTION

logger = logging.getLogger(__name__)


class ProjectAnalysisService:
    """Service for project analysis using CrewAI agents."""
    
    def __init__(
        self,
        ai_client: AIClient,
        prompt_manager: PromptManager,
        blockchain_client: BlockchainClient,
        firecrawl_client: FirecrawlClient,
        defillama_service: DefiLlamaService
    ):
        """Initialize project analysis service.
        
        Args:
            ai_client: AI client for crew agents
            prompt_manager: Prompt manager for crew agents
            blockchain_client: Blockchain client for contract interactions
            firecrawl_client: Firecrawl client for web crawling
            defillama_service: DeFiLlama service for project data
        """
        self.ai_client = ai_client
        self.prompt_manager = prompt_manager
        self.blockchain_client = blockchain_client
        self.firecrawl_client = firecrawl_client
        self.defillama_service = defillama_service
        
        # Project data cache
        self.project_cache: Dict[str, Dict[str, Any]] = {}
        
        # Base crew for on-demand analysis
        self.base_crew = create_crew(
            crew_type="whitelist_analysis",
            ai_client=self.ai_client,
            prompt_manager=self.prompt_manager,
            blockchain_client=self.blockchain_client,
            firecrawl_client=self.firecrawl_client,
            defillama_service=self.defillama_service,
            verbose=True
        )
    
    @classmethod
    async def create(cls) -> 'ProjectAnalysisService':
        """Create a project analysis service instance.
        
        Returns:
            ProjectAnalysisService instance
        """
        # Initialize dependencies
        ai_client = AIClient()
        prompt_manager = PromptManager(use_db=False, templates_dir="whitelist_hub/prompts/templates")
        blockchain_client = BlockchainClient()
        firecrawl_client = FirecrawlClient()
        defillama_service = DefiLlamaService()
        
        # Create service
        return cls(
            ai_client=ai_client,
            prompt_manager=prompt_manager,
            blockchain_client=blockchain_client,
            firecrawl_client=firecrawl_client,
            defillama_service=defillama_service
        )
    
    async def analyze_project(
        self,
        project_name: str,
        website: Optional[str] = None,
        github_url: Optional[str] = None,
        session_id: Optional[str] = None,
        message_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """Analyze a blockchain project.
        
        Args:
            project_name: Name of the project
            website: Project website URL
            github_url: Project GitHub URL
            session_id: Session ID for messaging
            message_callback: Callback for sending progress messages
            
        Returns:
            Analysis result
        """
        # Check if project is already analyzed
        cache_key = project_name.lower()
        if cache_key in self.project_cache:
            # Return cached result
            if message_callback:
                await message_callback(
                    MessageStructure.format_system(f"Using cached analysis for {project_name}")
                )
            return self.project_cache[cache_key]
        
        # Check database for existing analysis
        try:
            collection = await get_collection(PROJECTS_COLLECTION)
            existing_analysis = await collection.find_one({"project_name": cache_key})
            if existing_analysis and "analysis_result" in existing_analysis:
                # Return database result
                if message_callback:
                    await message_callback(
                        MessageStructure.format_system(f"Using existing analysis for {project_name}")
                    )
                
                # Update cache
                self.project_cache[cache_key] = existing_analysis["analysis_result"]
                return existing_analysis["analysis_result"]
        except Exception as e:
            logger.warning(f"Error checking database for existing analysis: {e}")
        
        # Send initial status update
        if message_callback:
            await message_callback(
                MessageStructure.format_system(f"Starting analysis of {project_name}...")
            )
        
        try:
            # Create a full analysis crew
            crew = self.base_crew.create_full_analysis_crew(project_name)
            
            # Prepare context
            context = {
                "project_name": project_name,
                "website": website,
                "github_url": github_url,
                "session_id": session_id,
                "analysis_timestamp": datetime.now().isoformat()
            }
            
            # Report progress
            if message_callback:
                await message_callback(
                    MessageStructure.format_system("Analysis in progress... This may take several minutes.")
                )
            
            # Run the crew
            result = await crew.run(context)
            
            # Ensure the result is a dictionary
            if not isinstance(result, dict):
                if isinstance(result, str):
                    try:
                        result = json.loads(result)
                    except:
                        result = {"result": result}
                else:
                    result = {"result": str(result)}
            
            # Add metadata
            result["project_name"] = project_name
            result["analysis_timestamp"] = datetime.now().isoformat()
            if website:
                result["website"] = website
            if github_url:
                result["github_url"] = github_url
            
            # Get summary
            crew_summary = crew.get_summary()
            result["analysis_summary"] = crew_summary
            
            # Save result to output directory
            output_dir = "output"
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"{project_name}_analysis_result.json")
            with open(output_path, "w") as f:
                json.dump(result, f, indent=2)
            
            # Save to cache
            self.project_cache[cache_key] = result
            
            # Report completion
            if message_callback:
                await message_callback(
                    MessageStructure.format_system(f"Analysis of {project_name} completed successfully")
                )
                
                # Send analysis completed message
                await message_callback(
                    {
                        "type": "analysis_completed",
                        "project_name": project_name,
                        "timestamp": datetime.now().isoformat()
                    }
                )
            
            return result
            
        except Exception as e:
            logger.exception(f"Error analyzing project: {e}")
            
            # Report error
            if message_callback:
                await message_callback(
                    MessageStructure.format_error(f"Error analyzing project: {str(e)}")
                )
            
            # Return error result
            return {
                "project_name": project_name,
                "error": str(e),
                "analysis_timestamp": datetime.now().isoformat(),
                "status": "error"
            }
    
    async def analyze_contract(
        self,
        contract_address: str,
        blockchain: str = "ethereum",
        session_id: Optional[str] = None,
        message_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """Analyze a specific smart contract.
        
        Args:
            contract_address: Contract address
            blockchain: Blockchain name
            session_id: Session ID for messaging
            message_callback: Callback for sending progress messages
            
        Returns:
            Contract analysis result
        """
        # Send initial status update
        if message_callback:
            await message_callback(
                MessageStructure.format_system(f"Starting analysis of contract {contract_address} on {blockchain}...")
            )
        
        try:
            # Create a contract analysis crew
            crew = self.base_crew.create_contract_analysis_crew([
                {"address": contract_address, "blockchain": blockchain}
            ])
            
            # Prepare context
            context = {
                "contract_address": contract_address,
                "blockchain": blockchain,
                "session_id": session_id,
                "analysis_timestamp": datetime.now().isoformat()
            }
            
            # Report progress
            if message_callback:
                await message_callback(
                    MessageStructure.format_system("Contract analysis in progress...")
                )
            
            # Run the crew
            result = await crew.run(context)
            
            # Ensure the result is a dictionary
            if not isinstance(result, dict):
                if isinstance(result, str):
                    try:
                        result = json.loads(result)
                    except:
                        result = {"result": result}
                else:
                    result = {"result": str(result)}
            
            # Add metadata
            result["contract_address"] = contract_address
            result["blockchain"] = blockchain
            result["analysis_timestamp"] = datetime.now().isoformat()
            
            # Get summary
            crew_summary = crew.get_summary()
            result["analysis_summary"] = crew_summary
            
            # Save result to output directory
            output_dir = "output"
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"{blockchain}_{contract_address}_analysis_result.json")
            with open(output_path, "w") as f:
                json.dump(result, f, indent=2)
            
            # Report completion
            if message_callback:
                await message_callback(
                    MessageStructure.format_system(f"Analysis of contract {contract_address} completed successfully")
                )
                
                # Send contract analysis completed message
                await message_callback(
                    {
                        "type": "contract_analysis_completed",
                        "contract_address": contract_address,
                        "blockchain": blockchain,
                        "timestamp": datetime.now().isoformat()
                    }
                )
            
            return result
            
        except Exception as e:
            logger.exception(f"Error analyzing contract: {e}")
            
            # Report error
            if message_callback:
                await message_callback(
                    MessageStructure.format_error(f"Error analyzing contract: {str(e)}")
                )
            
            # Return error result
            return {
                "contract_address": contract_address,
                "blockchain": blockchain,
                "error": str(e),
                "analysis_timestamp": datetime.now().isoformat(),
                "status": "error"
            }
    
    async def process_message(
        self,
        session_id: str,
        message: str
    ) -> str:
        """Process a message in a session.
        
        Args:
            session_id: Session ID
            message: User message
            
        Returns:
            Response message
        """
        try:
            # Simple AI response for now - this would be enhanced with conversational capabilities
            prompt = f"""
            You are a helpful assistant specializing in blockchain project analysis, particularly whitelist mechanisms.
            The user is asking about blockchain projects, smart contracts, or whitelist mechanisms.
            
            User message: {message}
            
            Provide a helpful response. Keep it concise but informative.
            """
            
            response = await self.ai_client.get_completion(prompt, temperature=0.7, max_tokens=1000)
            content = response["choices"][0]["message"]["content"]
            
            return content
            
        except Exception as e:
            logger.exception(f"Error processing message: {e}")
            return f"I'm sorry, I encountered an error processing your message: {str(e)}"
    
    async def get_project_data(self, project_name: str) -> Optional[Dict[str, Any]]:
        """Get project data from cache or database.
        
        Args:
            project_name: Project name
            
        Returns:
            Project data if available
        """
        # Check cache first
        cache_key = project_name.lower()
        if cache_key in self.project_cache:
            return self.project_cache[cache_key]
        
        # Check database
        try:
            collection = await get_collection(PROJECTS_COLLECTION)
            project_data = await collection.find_one({"project_name": cache_key})
            if project_data and "analysis_result" in project_data:
                # Add to cache
                self.project_cache[cache_key] = project_data["analysis_result"]
                return project_data["analysis_result"]
        except Exception as e:
            logger.error(f"Error fetching project data from database: {e}")
        
        return None
