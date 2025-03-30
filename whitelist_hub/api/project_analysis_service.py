"""Project analysis service for Whitelist Hub."""

import logging
import asyncio
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from ..models.message import MessageStructure
from ..agents.agent_factory import create_agent
from ..utils.ai_client import AIClient
from ..utils.firecrawl_client import FirecrawlClient
from ..prompts.prompt_manager import PromptManager
from ..services.defillama_service import DefiLlamaService
from ..utils.blockchain_client import BlockchainClient

logger = logging.getLogger(__name__)


class ProjectAnalysisService:
    """Service for project analysis."""
    
    def __init__(
        self,
        ai_client: Optional[AIClient] = None,
        prompt_manager: Optional[PromptManager] = None,
        blockchain_client: Optional[BlockchainClient] = None,
        firecrawl_client: Optional[FirecrawlClient] = None,
        defillama_service: Optional[DefiLlamaService] = None,
        framework: str = "custom"
    ):
        """Initialize project analysis service.
        
        Args:
            ai_client: AI client for LLM interactions
            prompt_manager: Prompt template manager
            blockchain_client: Blockchain client for interactions
            firecrawl_client: Firecrawl client for web crawling
            defillama_service: DeFiLlama service for project data
            framework: Agent framework to use (custom, langchain, auto)
        """
        self.ai_client = ai_client or AIClient()
        self.prompt_manager = prompt_manager or PromptManager(use_db=False, templates_dir="whitelist_hub/prompts/templates")
        self.blockchain_client = blockchain_client or BlockchainClient()
        self.firecrawl_client = firecrawl_client or FirecrawlClient()
        self.defillama_service = defillama_service or DefiLlamaService()
        self.framework = framework
        
        # Initialize agents
        self.coordinator_agent = create_agent(
            "coordinator",
            ai_client=self.ai_client,
            prompt_manager=self.prompt_manager
        )
        
        self.crawler_agent = create_agent(
            "crawler",
            ai_client=self.ai_client,
            prompt_manager=self.prompt_manager,
            blockchain_client=self.blockchain_client,
            firecrawl_client=self.firecrawl_client,
            defillama_service=self.defillama_service
        )
        
        self.analysis_agent = create_agent(
            "analyzer",
            ai_client=self.ai_client,
            prompt_manager=self.prompt_manager,
            blockchain_client=self.blockchain_client
        )
        
        self.verifier_agent = create_agent(
            "verifier",
            ai_client=self.ai_client,
            prompt_manager=self.prompt_manager,
            blockchain_client=self.blockchain_client
        )
        
        # Project data cache
        self.project_cache: Dict[str, Dict[str, Any]] = {}
    
    async def analyze_project(
        self,
        project_name: str,
        website: Optional[str] = None,
        github_url: Optional[str] = None,
        session_id: Optional[str] = None,
        message_callback = None
    ) -> Dict[str, Any]:
        """Analyze a project.
        
        Args:
            project_name: Project name
            website: Project website
            github_url: Project GitHub URL
            session_id: Session ID for callback progress updates
            message_callback: Callback function for messages
            
        Returns:
            Analysis result
        """
        # Check if project is already analyzed
        cache_key = f"{project_name.lower()}"
        if cache_key in self.project_cache:
            # Return cached result
            if message_callback:
                await message_callback(
                    MessageStructure.format_system(f"Using cached analysis for {project_name}")
                )
            return self.project_cache[cache_key]
        
        # Send initial status update
        if message_callback:
            await message_callback(
                MessageStructure.format_system(f"Starting analysis of {project_name}...")
            )
        
        # Step 1: Crawl initial data
        if message_callback:
            await message_callback(
                MessageStructure.format_system("Step 1: Crawling project information...")
            )
        
        project_data, crawl_log = await self.crawler_agent.crawl_project_information(
            project_name=project_name,
            website=website,
            github_url=github_url
        )
        
        if message_callback:
            await message_callback(
                MessageStructure.format_system("Project information crawled successfully")
            )
        
        # Step 2: Create analysis plan
        if message_callback:
            await message_callback(
                MessageStructure.format_system("Step 2: Creating analysis plan...")
            )
        
        analysis_plan, plan_log = await self.coordinator_agent.create_analysis_plan(
            project_name=project_name,
            project_data=project_data
        )
        
        if message_callback:
            await message_callback(
                MessageStructure.format_system("Analysis plan created successfully")
            )
        
        # Step 3: Analyze contracts
        if message_callback:
            await message_callback(
                MessageStructure.format_system("Step 3: Analyzing contracts...")
            )
        
        contract_analyses = []
        
        for i, contract_info in enumerate(project_data.get("contract_addresses", [])):
            address = contract_info.get("address")
            blockchain = contract_info.get("blockchain", "ethereum")
            
            if not address:
                continue
            
            if message_callback:
                await message_callback(
                    MessageStructure.format_system(f"Analyzing contract {i+1}/{len(project_data.get('contract_addresses', []))}: {address} on {blockchain}")
                )
            
            # Get contract ABI
            abi = await self.blockchain_client.fetch_contract_abi(address, blockchain)
            
            # Analyze ABI
            abi_analysis, abi_log = await self.analysis_agent.analyze_contract_abi(
                contract_address=address,
                blockchain=blockchain,
                abi_json=abi
            )
            
            # Detect if proxy
            proxy_detection, proxy_log = await self.analysis_agent.detect_proxy_pattern(
                contract_address=address,
                blockchain=blockchain
            )
            
            # Combine analyses
            contract_analysis = {
                "address": address,
                "blockchain": blockchain,
                "abi_analysis": abi_analysis,
                "proxy_detection": proxy_detection,
                "is_proxy": proxy_detection.get("is_proxy", False)
            }
            
            # If whitelist functionality detected, analyze it
            whitelist_detected = False
            if isinstance(abi_analysis, dict):
                whitelist_detected = any("whitelist" in category.lower() for category in abi_analysis.get("function_categories", {}))
            elif hasattr(abi_analysis, "data") and hasattr(abi_analysis.data, "function_categories"):
                whitelist_detected = any("whitelist" in category.lower() for category in abi_analysis.data.function_categories)
            
            if whitelist_detected:
                if message_callback:
                    await message_callback(
                        MessageStructure.format_system(f"Whitelist functionality detected in {address}. Analyzing...")
                    )
                
                whitelist_analysis, whitelist_log = await self.analysis_agent.analyze_whitelist_mechanism(
                    contract_address=address,
                    contract_data=abi_analysis,
                    blockchain=blockchain
                )
                
                contract_analysis["whitelist_analysis"] = whitelist_analysis
            
            contract_analyses.append(contract_analysis)
        
        if message_callback:
            await message_callback(
                MessageStructure.format_system(f"Analyzed {len(contract_analyses)} contracts")
            )
        
        # Step 4: Verify and validate analyses
        if message_callback:
            await message_callback(
                MessageStructure.format_system("Step 4: Verifying analyses...")
            )
        
        verified_analyses = []
        
        for contract_analysis in contract_analyses:
            # Define a simple schema for validation
            schema = {
                "type": "object",
                "required": ["address", "blockchain"],
                "properties": {
                    "address": {"type": "string"},
                    "blockchain": {"type": "string"}
                }
            }
            
            verified_result, verification_log = await self.verifier_agent.verify_analysis_result(
                analysis_result=contract_analysis,
                contract_schema=schema
            )
            
            verified_analyses.append(verified_result)
        
        if message_callback:
            await message_callback(
                MessageStructure.format_system("Analyses verified successfully")
            )
        
        # Step 5: Synthesize final results
        if message_callback:
            await message_callback(
                MessageStructure.format_system("Step 5: Synthesizing results...")
            )
        
        # Prepare data for synthesis
        synthesis_data = {
            "project_overview": project_data,
            "contract_analyses": verified_analyses,
            "whitelist_mechanisms": [
                analysis.get("whitelist_analysis") 
                for analysis in verified_analyses 
                if "whitelist_analysis" in analysis
            ],
            "user_flows": [],  # Would be populated in a full implementation
            "security_assessment": {
                "risk_level": "medium",  # Simplified for this example
                "findings": []
            }
        }
        
        final_synthesis, synthesis_log = await self.coordinator_agent.synthesize_analysis_results(
            project_name=project_name,
            project_overview=synthesis_data["project_overview"],
            contract_analyses=synthesis_data["contract_analyses"],
            whitelist_mechanisms=synthesis_data["whitelist_mechanisms"],
            user_flows=synthesis_data["user_flows"],
            security_assessment=synthesis_data["security_assessment"]
        )
        
        if message_callback:
            await message_callback(
                MessageStructure.format_system("Results synthesis completed")
            )
        
        # Generate project rating
        rating = await self.generate_project_rating(
            project_name=project_name,
            synthesis=final_synthesis
        )
        
        # Add rating to final result
        final_synthesis["rating"] = rating
        
        # Store in cache
        self.project_cache[cache_key] = final_synthesis
        
        if message_callback:
            await message_callback(
                MessageStructure.format_system(f"Analysis of {project_name} completed successfully")
            )
        
        return final_synthesis
    
    async def analyze_specific_contract(
        self,
        contract_address: str,
        blockchain: str = "ethereum",
        message_callback = None
    ) -> Dict[str, Any]:
        """Analyze a specific contract.
        
        Args:
            contract_address: Contract address
            blockchain: Blockchain name
            message_callback: Callback function for messages
            
        Returns:
            Analysis result
        """
        # Send initial status update
        if message_callback:
            await message_callback(
                MessageStructure.format_system(f"Starting analysis of contract {contract_address} on {blockchain}...")
            )
        
        # Get contract ABI
        abi = await self.blockchain_client.fetch_contract_abi(contract_address, blockchain)
        
        # Analyze ABI
        abi_analysis, abi_log = await self.analysis_agent.analyze_contract_abi(
            contract_address=contract_address,
            blockchain=blockchain,
            abi_json=abi
        )
        
        if message_callback:
            await message_callback(
                MessageStructure.format_system("ABI analysis completed")
            )
        
        # Detect if proxy
        proxy_detection, proxy_log = await self.analysis_agent.detect_proxy_pattern(
            contract_address=contract_address,
            blockchain=blockchain
        )
        
        if message_callback:
            await message_callback(
                MessageStructure.format_system("Proxy detection completed")
            )
        
        # Combine analyses
        contract_analysis = {
            "address": contract_address,
            "blockchain": blockchain,
            "abi_analysis": abi_analysis,
            "proxy_detection": proxy_detection,
            "is_proxy": proxy_detection.get("is_proxy", False)
        }
        
        # If whitelist functionality detected, analyze it
        whitelist_detected = False
        if isinstance(abi_analysis, dict):
            whitelist_detected = any("whitelist" in category.lower() for category in abi_analysis.get("function_categories", {}))
        elif hasattr(abi_analysis, "data") and hasattr(abi_analysis.data, "function_categories"):
            whitelist_detected = any("whitelist" in category.lower() for category in abi_analysis.data.function_categories)
        
        if whitelist_detected:
            if message_callback:
                await message_callback(
                    MessageStructure.format_system(f"Whitelist functionality detected in {contract_address}. Analyzing...")
                )
            
            whitelist_analysis, whitelist_log = await self.analysis_agent.analyze_whitelist_mechanism(
                contract_address=contract_address,
                contract_data=abi_analysis,
                blockchain=blockchain
            )
            
            contract_analysis["whitelist_analysis"] = whitelist_analysis
        
        # Verify analysis
        schema = {
            "type": "object",
            "required": ["address", "blockchain"],
            "properties": {
                "address": {"type": "string"},
                "blockchain": {"type": "string"}
            }
        }
        
        verified_result, verification_log = await self.verifier_agent.verify_analysis_result(
            analysis_result=contract_analysis,
            contract_schema=schema
        )
        
        if message_callback:
            await message_callback(
                MessageStructure.format_system("Contract analysis completed")
            )
        
        return verified_result
    
    async def get_project_info(self, project_name: str) -> Optional[Dict[str, Any]]:
        """Get project information from DeFiLlama or cache.
        
        Args:
            project_name: Project name
            
        Returns:
            Project information if available
        """
        # Check cache first
        cache_key = f"{project_name.lower()}"
        if cache_key in self.project_cache:
            return self.project_cache[cache_key]
        
        # Try to get from DeFiLlama
        try:
            project_info = await self.defillama_service.fetch_project_data(project_name)
            if project_info:
                return project_info
        except Exception as e:
            logger.error(f"Error fetching project info from DeFiLlama: {e}")
        
        return None
    
    async def generate_project_rating(self, project_name: str, synthesis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a rating for the project based on the analysis.
        
        Args:
            project_name: Project name
            synthesis: Synthesis of all analyses
            
        Returns:
            Project rating
        """
        # Extract relevant information for rating
        contract_count = len(synthesis.get("contract_analyses", []))
        whitelist_count = len(synthesis.get("whitelist_mechanisms", []))
        
        # Factors to consider in rating
        factors = {
            "contract_quality": 0.0,
            "documentation": 0.0,
            "whitelist_implementation": 0.0,
            "security": 0.0,
            "code_quality": 0.0
        }
        
        # Rate contract quality (0-10)
        if contract_count > 0:
            verified_contracts = sum(1 for c in synthesis.get("contract_analyses", []) 
                                  if c.get("verification", {}).get("verified", False))
            factors["contract_quality"] = (verified_contracts / contract_count) * 10
        
        # Rate documentation (0-10)
        project_overview = synthesis.get("project_overview", {})
        if project_overview:
            doc_factors = [
                1 if project_overview.get("website") else 0,
                2 if project_overview.get("github_url") else 0,
                2 if project_overview.get("documentation_links", []) else 0,
                2 if project_overview.get("description") else 0,
                3 if project_overview.get("whitepaper_url") else 0
            ]
            factors["documentation"] = sum(doc_factors)
        
        # Rate whitelist implementation (0-10)
        if whitelist_count > 0:
            whitelist_scores = []
            for wl in synthesis.get("whitelist_mechanisms", []):
                score = 0
                # Add points for different aspects of whitelist implementation
                if wl.get("mechanism_type") != "unknown":
                    score += 3
                if wl.get("tiered"):
                    score += 2
                if wl.get("time_limited"):
                    score += 2
                if wl.get("data_storage") == "merkle":
                    score += 3  # Merkle trees are more gas-efficient
                whitelist_scores.append(score)
            
            if whitelist_scores:
                factors["whitelist_implementation"] = sum(whitelist_scores) / len(whitelist_scores)
        
        # Rate security (0-10)
        security_assessment = synthesis.get("security_assessment", {})
        if security_assessment:
            risk_level = security_assessment.get("risk_level", "medium")
            if risk_level == "low":
                factors["security"] = 9.0
            elif risk_level == "medium":
                factors["security"] = 6.0
            else:  # high risk
                factors["security"] = 3.0
            
            # Adjust for findings
            finding_count = len(security_assessment.get("findings", []))
            if finding_count > 0:
                factors["security"] = max(0, factors["security"] - (finding_count * 0.5))
        
        # Rate code quality (0-10)
        # This would normally involve more sophisticated metrics
        # For now, use a simple heuristic based on proxy usage and verification
        if contract_count > 0:
            code_quality_factors = [
                3 if any(c.get("is_proxy", False) for c in synthesis.get("contract_analyses", [])) else 0,  # Using proxies is good practice
                7 * (sum(1 for c in synthesis.get("contract_analyses", []) if c.get("verification", {}).get("verified", False)) / contract_count)  # Percentage of verified contracts
            ]
            factors["code_quality"] = sum(code_quality_factors)
        
        # Calculate overall rating (0-100)
        weights = {
            "contract_quality": 0.2,
            "documentation": 0.2,
            "whitelist_implementation": 0.3,
            "security": 0.2,
            "code_quality": 0.1
        }
        
        overall_score = sum(factors[k] * weights[k] * 10 for k in factors.keys())
        
        # Determine rating based on score
        rating = "F"
        if overall_score >= 90:
            rating = "A+"
        elif overall_score >= 80:
            rating = "A"
        elif overall_score >= 70:
            rating = "B+"
        elif overall_score >= 60:
            rating = "B"
        elif overall_score >= 50:
            rating = "C+"
        elif overall_score >= 40:
            rating = "C"
        elif overall_score >= 30:
            rating = "D+"
        elif overall_score >= 20:
            rating = "D"
        
        return {
            "overall_score": round(overall_score, 2),
            "rating": rating,
            "factors": {k: round(v, 2) for k, v in factors.items()},
            "explanation": f"The project received a {rating} rating with a score of {round(overall_score, 2)}/100. " + 
                           f"Key strengths include {max(factors, key=factors.get)} while {min(factors, key=factors.get)} could be improved.",
            "timestamp": datetime.now().isoformat()
        }
