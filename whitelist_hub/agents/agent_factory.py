"""Factory for creating agents."""

from typing import Optional, Dict, Any

from .base_agent import BaseAgent
from .coordinator_agent import CoordinatorAgent
from .crawler.crawler_agent import CrawlerAgent
from .analysis_agent import AnalysisAgent
from .verification_agent import VerificationAgent
from ..prompts.prompt_manager import PromptManager
from ..utils.ai_client import AIClient
from ..utils.blockchain_client import BlockchainClient
from ..services.defillama_service import DefiLlamaService


def create_agent(
    agent_type: str,
    ai_client: Optional[AIClient] = None,
    prompt_manager: Optional[PromptManager] = None,
    blockchain_client: Optional[BlockchainClient] = None,
    defillama_service: Optional[DefiLlamaService] = None,
    max_iterations: int = 10,
    **kwargs
) -> BaseAgent:
    """Create an agent of the specified type.
    
    Args:
        agent_type: Type of agent to create
        ai_client: AI client
        prompt_manager: Prompt manager
        blockchain_client: Blockchain client
        defillama_service: DeFiLlama service
        max_iterations: Maximum iterations for agent
        **kwargs: Additional arguments for agent constructor
        
    Returns:
        Agent instance
        
    Raises:
        ValueError: If agent type is not supported
    """
    # Create default clients if not provided
    if not ai_client:
        ai_client = AIClient()
    
    if not prompt_manager:
        prompt_manager = PromptManager()
    
    if not blockchain_client:
        blockchain_client = BlockchainClient()
    
    if not defillama_service:
        defillama_service = DefiLlamaService()
    
    # Create agent based on type
    if agent_type.lower() == "coordinator":
        return CoordinatorAgent(
            ai_client=ai_client,
            prompt_manager=prompt_manager,
            max_iterations=max_iterations,
            **kwargs
        )
    elif agent_type.lower() == "crawler":
        return CrawlerAgent(
            ai_client=ai_client,
            prompt_manager=prompt_manager,
            blockchain_client=blockchain_client,
            defillama_service=defillama_service,
            max_iterations=max_iterations,
            **kwargs
        )
    elif agent_type.lower() == "analyzer" or agent_type.lower() == "analysis":
        return AnalysisAgent(
            ai_client=ai_client,
            prompt_manager=prompt_manager,
            blockchain_client=blockchain_client,
            max_iterations=max_iterations,
            **kwargs
        )
    elif agent_type.lower() == "verifier" or agent_type.lower() == "verification":
        return VerificationAgent(
            ai_client=ai_client,
            prompt_manager=prompt_manager,
            blockchain_client=blockchain_client,
            max_iterations=max_iterations,
            **kwargs
        )
    else:
        raise ValueError(f"Unsupported agent type: {agent_type}")
