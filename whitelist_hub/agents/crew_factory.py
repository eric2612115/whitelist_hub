"""Factory for creating agent crews."""

import logging
from typing import Dict, Any, List, Optional, Type, Union
from crewai import Crew, Agent, Task, Process

from .base_crew import BaseCrew
from .coordinator import CoordinatorAgent
from .crawler.crawler_agent import CrawlerAgent
from .analyzer.analysis_agent import AnalysisAgent
from .verification_agent import VerificationAgent
from ..utils.ai_client import AIClient
from ..prompts.prompt_manager import PromptManager
from ..utils.blockchain_client import BlockchainClient
from ..utils.firecrawl_client import FirecrawlClient
from ..services.defillama_service import DefiLlamaService

logger = logging.getLogger(__name__)


class WhitelistAnalysisCrew(BaseCrew):
    """Crew specialized for whitelist analysis."""
    
    def __init__(
        self,
        ai_client: AIClient,
        prompt_manager: PromptManager,
        blockchain_client: BlockchainClient,
        firecrawl_client: FirecrawlClient,
        defillama_service: DefiLlamaService,
        process: Process = Process.sequential,
        verbose: bool = True
    ):
        """Initialize whitelist analysis crew.
        
        Args:
            ai_client: AI client for crew agents
            prompt_manager: Prompt manager for crew agents
            blockchain_client: Blockchain client for contract interactions
            firecrawl_client: Firecrawl client for web crawling
            defillama_service: DeFiLlama service for project data
            process: CrewAI process type (sequential, hierarchical)
            verbose: Whether to enable verbose logging
        """
        super().__init__(
            ai_client=ai_client,
            prompt_manager=prompt_manager,
            process=process,
            verbose=verbose
        )
        
        self.blockchain_client = blockchain_client
        self.firecrawl_client = firecrawl_client
        self.defillama_service = defillama_service
        
        # Create agents
        self._create_agents()
        
        # Create tasks (but don't add them yet - they will be added when needed)
        self.available_tasks = self._create_tasks()
    
    def _create_agents(self):
        """Create all required agents."""
        # Create coordinator agent
        coordinator_agent = CoordinatorAgent(
            ai_client=self.ai_client,
            prompt_manager=self.prompt_manager
        )
        self.add_agent("coordinator", coordinator_agent.create_agent())
        
        # Create crawler agent
        crawler_agent = CrawlerAgent(
            ai_client=self.ai_client,
            prompt_manager=self.prompt_manager,
            blockchain_client=self.blockchain_client,
            firecrawl_client=self.firecrawl_client,
            defillama_service=self.defillama_service
        )
        self.add_agent("crawler", crawler_agent.create_agent())
        
        # Create analysis agent
        analysis_agent = AnalysisAgent(
            ai_client=self.ai_client,
            prompt_manager=self.prompt_manager,
            blockchain_client=self.blockchain_client
        )
        self.add_agent("analyzer", analysis_agent.create_agent())
        
        # Create verification agent
        verification_agent = VerificationAgent(
            ai_client=self.ai_client,
            prompt_manager=self.prompt_manager,
            blockchain_client=self.blockchain_client
        )
        self.add_agent("verifier", verification_agent.create_agent())
    
    def _create_tasks(self) -> Dict[str, Task]:
        """Create all potential tasks.
        
        Returns:
            Dictionary of tasks by key
        """
        tasks = {}
        
        # Coordinator tasks
        tasks["create_analysis_plan"] = Task(
            description="Create a comprehensive analysis plan for the blockchain project, including which contracts to analyze and what aspects to focus on",
            expected_output="A structured analysis plan with prioritized contracts and analysis tasks",
            agent=self.get_agent("coordinator")
        )
        
        tasks["synthesize_results"] = Task(
            description="Synthesize all analysis results into a comprehensive report about the project's whitelist mechanisms and overall architecture",
            expected_output="A complete synthesis of all analyses, including executive summary, detailed findings, and recommendations",
            agent=self.get_agent("coordinator")
        )
        
        # Crawler tasks
        tasks["crawl_project_website"] = Task(
            description="Crawl the project's website to gather information about its purpose, architecture, and whitelist mechanisms",
            expected_output="Extracted information from the project website, including potential contract addresses and documentation",
            agent=self.get_agent("crawler")
        )
        
        tasks["crawl_github_repository"] = Task(
            description="Analyze the project's GitHub repository to identify smart contracts and understand their implementation details",
            expected_output="List of contract files with their code and important implementation details",
            agent=self.get_agent("crawler")
        )
        
        tasks["discover_contract_addresses"] = Task(
            description="Discover and validate all contract addresses associated with the project across different blockchains",
            expected_output="List of verified contract addresses with their respective blockchains",
            agent=self.get_agent("crawler")
        )
        
        # Analyzer tasks
        tasks["analyze_contracts"] = Task(
            description="Analyze the identified smart contracts to understand their functionality, categorize functions, and detect proxy patterns",
            expected_output="Detailed analysis of each contract including function categorization and proxy detection",
            agent=self.get_agent("analyzer")
        )
        
        tasks["identify_whitelist_mechanisms"] = Task(
            description="Identify and classify whitelist mechanisms in the project's smart contracts",
            expected_output="Detailed analysis of whitelist mechanisms, including their type, implementation details, and functionality",
            agent=self.get_agent("analyzer")
        )
        
        tasks["analyze_security_patterns"] = Task(
            description="Analyze security patterns and potential vulnerabilities in the whitelist implementations",
            expected_output="Security assessment of the whitelist mechanisms and other key contract functionalities",
            agent=self.get_agent("analyzer")
        )
        
        # Verifier tasks
        tasks["verify_analyses"] = Task(
            description="Verify the accuracy and completeness of all contract analyses",
            expected_output="Verification results for each analysis, highlighting any inconsistencies or issues",
            agent=self.get_agent("verifier")
        )
        
        tasks["cross_validate_contracts"] = Task(
            description="Cross-validate the analyses of different contracts to identify relationships and ensure consistent findings",
            expected_output="Cross-validation results highlighting relationships between contracts and any inconsistencies",
            agent=self.get_agent("verifier")
        )
        
        return tasks
    
    def create_full_analysis_crew(self, project_name: str) -> 'WhitelistAnalysisCrew':
        """Create a crew with all tasks for full project analysis.
        
        Args:
            project_name: Name of the project to analyze
            
        Returns:
            Configured crew instance
        """
        # Clear any existing tasks
        self.tasks = []
        
        # Add tasks in sequence for full analysis
        self.add_task(self.available_tasks["create_analysis_plan"])
        self.add_task(self.available_tasks["crawl_project_website"])
        self.add_task(self.available_tasks["crawl_github_repository"])
        self.add_task(self.available_tasks["discover_contract_addresses"])
        self.add_task(self.available_tasks["analyze_contracts"])
        self.add_task(self.available_tasks["identify_whitelist_mechanisms"])
        self.add_task(self.available_tasks["analyze_security_patterns"])
        self.add_task(self.available_tasks["verify_analyses"])
        self.add_task(self.available_tasks["cross_validate_contracts"])
        self.add_task(self.available_tasks["synthesize_results"])
        
        return self
    
    def create_contract_analysis_crew(self, contract_addresses: List[Dict[str, str]]) -> 'WhitelistAnalysisCrew':
        """Create a crew for analyzing specific contracts.
        
        Args:
            contract_addresses: List of contract addresses with blockchains
            
        Returns:
            Configured crew instance
        """
        # Clear any existing tasks
        self.tasks = []
        
        # Add tasks for contract analysis
        self.add_task(self.available_tasks["analyze_contracts"])
        self.add_task(self.available_tasks["identify_whitelist_mechanisms"])
        self.add_task(self.available_tasks["analyze_security_patterns"])
        self.add_task(self.available_tasks["verify_analyses"])
        
        if len(contract_addresses) > 1:
            self.add_task(self.available_tasks["cross_validate_contracts"])
        
        return self
    
    def create_website_analysis_crew(self, website_url: str) -> 'WhitelistAnalysisCrew':
        """Create a crew for analyzing a project's website.
        
        Args:
            website_url: Website URL to analyze
            
        Returns:
            Configured crew instance
        """
        # Clear any existing tasks
        self.tasks = []
        
        # Add tasks for website analysis
        self.add_task(self.available_tasks["crawl_project_website"])
        self.add_task(self.available_tasks["discover_contract_addresses"])
        
        return self


class SecurityAnalysisCrew(BaseCrew):
    """Crew specialized for security analysis."""
    
    def __init__(
        self,
        ai_client: AIClient,
        prompt_manager: PromptManager,
        blockchain_client: BlockchainClient,
        process: Process = Process.sequential,
        verbose: bool = True
    ):
        """Initialize security analysis crew.
        
        Args:
            ai_client: AI client for crew agents
            prompt_manager: Prompt manager for crew agents
            blockchain_client: Blockchain client for contract interactions
            process: CrewAI process type (sequential, hierarchical)
            verbose: Whether to enable verbose logging
        """
        super().__init__(
            ai_client=ai_client,
            prompt_manager=prompt_manager,
            process=process,
            verbose=verbose
        )
        
        self.blockchain_client = blockchain_client
        
        # Create agents (simplified for security focus)
        self._create_agents()
        
        # Create tasks
        self.available_tasks = self._create_tasks()
    
    def _create_agents(self):
        """Create security-focused agents."""
        # Reuse analysis agent
        analysis_agent = AnalysisAgent(
            ai_client=self.ai_client,
            prompt_manager=self.prompt_manager,
            blockchain_client=self.blockchain_client
        )
        self.add_agent("analyzer", analysis_agent.create_agent(
            name="Security Analyzer",
            goal="Identify security vulnerabilities and risks in smart contracts"
        ))
        
        # Reuse verification agent
        verification_agent = VerificationAgent(
            ai_client=self.ai_client,
            prompt_manager=self.prompt_manager,
            blockchain_client=self.blockchain_client
        )
        self.add_agent("verifier", verification_agent.create_agent(
            name="Security Verifier",
            goal="Validate security findings and ensure thorough vulnerability detection"
        ))
    
    def _create_tasks(self) -> Dict[str, Task]:
        """Create security-focused tasks.
        
        Returns:
            Dictionary of tasks by key
        """
        tasks = {}
        
        # Security analyzer tasks
        tasks["analyze_security_patterns"] = Task(
            description="Analyze security patterns and potential vulnerabilities in the smart contracts",
            expected_output="Comprehensive security assessment identifying all potential vulnerabilities",
            agent=self.get_agent("analyzer")
        )
        
        # Verifier tasks
        tasks["verify_security_findings"] = Task(
            description="Verify the security findings and ensure all potential vulnerabilities have been identified",
            expected_output="Verification of security findings with additional insights and validation",
            agent=self.get_agent("verifier")
        )
        
        return tasks
    
    def create_security_crew(self) -> 'SecurityAnalysisCrew':
        """Create a crew for security analysis.
        
        Returns:
            Configured crew instance
        """
        # Clear any existing tasks
        self.tasks = []
        
        # Add tasks for security analysis
        self.add_task(self.available_tasks["analyze_security_patterns"])
        self.add_task(self.available_tasks["verify_security_findings"])
        
        return self


def create_crew(
    crew_type: str,
    ai_client: AIClient,
    prompt_manager: PromptManager,
    blockchain_client: Optional[BlockchainClient] = None,
    firecrawl_client: Optional[FirecrawlClient] = None,
    defillama_service: Optional[DefiLlamaService] = None,
    process: Process = Process.sequential,
    verbose: bool = True
) -> BaseCrew:
    """Create a crew instance based on type.
    
    Args:
        crew_type: Type of crew to create
        ai_client: AI client for crew agents
        prompt_manager: Prompt manager for crew agents
        blockchain_client: Blockchain client for contract interactions
        firecrawl_client: Firecrawl client for web crawling
        defillama_service: DeFiLlama service for project data
        process: CrewAI process type (sequential, hierarchical)
        verbose: Whether to enable verbose logging
        
    Returns:
        CrewAI crew instance
    """
    if crew_type == "whitelist_analysis":
        if not blockchain_client:
            blockchain_client = BlockchainClient()
        if not firecrawl_client:
            firecrawl_client = FirecrawlClient()
        if not defillama_service:
            defillama_service = DefiLlamaService()
        
        return WhitelistAnalysisCrew(
            ai_client=ai_client,
            prompt_manager=prompt_manager,
            blockchain_client=blockchain_client,
            firecrawl_client=firecrawl_client,
            defillama_service=defillama_service,
            process=process,
            verbose=verbose
        )
    elif crew_type == "security_analysis":
        if not blockchain_client:
            blockchain_client = BlockchainClient()
        
        return SecurityAnalysisCrew(
            ai_client=ai_client,
            prompt_manager=prompt_manager,
            blockchain_client=blockchain_client,
            process=process,
            verbose=verbose
        )
    else:
        logger.warning(f"Unknown crew type: {crew_type}. Creating empty base crew.")
        return BaseCrew(
            ai_client=ai_client,
            prompt_manager=prompt_manager,
            process=process,
            verbose=verbose
        )
