"""Main Crawler Agent implementation."""

import logging
from typing import Dict, List, Any, Optional, Tuple, Set

from ...models.analysis_log import AnalysisLog
from ..base_agent import BaseAgent
from .source_crawlers import (
    WebsiteCrawler,
    GithubCrawler,
    DefiLlamaCrawler,
    SocialMediaCrawler
)
from .data_extractors import (
    ContractExtractor,
    WhitelistExtractor,
    ProjectDetailsExtractor
)
from ...utils.blockchain_client import BlockchainClient

logger = logging.getLogger(__name__)


class CrawlerAgent(BaseAgent):
    """Crawler Agent for gathering blockchain project information."""
    
    def __init__(
        self,
        blockchain_client=None,
        website_crawler=None,
        github_crawler=None,
        defillama_crawler=None,
        social_media_crawler=None,
        contract_extractor=None,
        whitelist_extractor=None,
        project_details_extractor=None,
        *args,
        **kwargs
    ):
        """Initialize Crawler Agent with dependency injection.
        
        Args:
            blockchain_client: Client for blockchain interactions
            website_crawler: Component for crawling websites
            github_crawler: Component for crawling GitHub repositories
            defillama_crawler: Component for fetching DeFiLlama data
            social_media_crawler: Component for crawling social media
            contract_extractor: Component for extracting contract info
            whitelist_extractor: Component for extracting whitelist info
            project_details_extractor: Component for extracting project details
        """
        super().__init__(agent_type="crawler", *args, **kwargs)
        
        # Initialize components with dependency injection or defaults
        self.blockchain_client = blockchain_client or BlockchainClient()
        self.website_crawler = website_crawler or WebsiteCrawler()
        self.github_crawler = github_crawler or GithubCrawler()
        self.defillama_crawler = defillama_crawler or DefiLlamaCrawler()
        self.social_media_crawler = social_media_crawler or SocialMediaCrawler()
        self.contract_extractor = contract_extractor or ContractExtractor(self.blockchain_client)
        self.whitelist_extractor = whitelist_extractor or WhitelistExtractor()
        self.project_details_extractor = project_details_extractor or ProjectDetailsExtractor()
    
    async def crawl_project_information(
        self, 
        project_name: str, 
        website: Optional[str] = None,
        github_url: Optional[str] = None
    ) -> Tuple[Dict[str, Any], AnalysisLog]:
        """Crawl project information from various sources.
        
        Args:
            project_name: Name of the project
            website: Project website URL
            github_url: Project GitHub URL
            
        Returns:
            Tuple of (project data, analysis log)
        """
        context = {
            "project_name": project_name,
            "website": website,
            "github_url": github_url,
            "crawled_data": {},
            "contract_addresses": set()
        }
        
        return await self.run(
            task="Collect comprehensive information about this blockchain project",
            context=context,
            initial_state="initial_discovery"
        )
    
    async def analyze_documentation(
        self, 
        project_name: str, 
        documentation_content: str
    ) -> Tuple[Dict[str, Any], AnalysisLog]:
        """Analyze project documentation to extract smart contract information.
        
        Args:
            project_name: Name of the project
            documentation_content: Project documentation content
            
        Returns:
            Tuple of (extracted information, analysis log)
        """
        context = {
            "project_name": project_name,
            "project_category": "",  # To be discovered
            "documentation_content": documentation_content,
            "extracted_information": {
                "contract_addresses": [],
                "architecture_info": {},
                "whitelist_info": {},
                "additional_info": {}
            }
        }
        
        return await self.run(
            task="Analyze project documentation to extract smart contract information",
            context=context,
            initial_state="documentation_analysis"
        )
    
    async def analyze_github_repository(
        self, 
        project_name: str,
        github_url: str,
        repo_structure: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], AnalysisLog]:
        """Analyze GitHub repository to find contract code and ABIs.
        
        Args:
            project_name: Name of the project
            github_url: GitHub repository URL
            repo_structure: Repository file structure
            
        Returns:
            Tuple of (repository analysis, analysis log)
        """
        context = {
            "project_name": project_name,
            "github_url": github_url,
            "repo_structure_json": repo_structure,
            "recent_commits_json": [],  # Would be populated by GitHub API
            "readme_content": "",  # Would be populated by GitHub API
            "extracted_information": {
                "contract_files": [],
                "abi_files": [],
                "deployment_info": [],
                "whitelist_implementations": []
            }
        }
        
        return await self.run(
            task="Analyze GitHub repository to find contract code and ABIs",
            context=context,
            initial_state="github_analysis"
        )
    
    async def analyze_social_content(
        self,
        project_name: str,
        social_content: Dict[str, List[Dict[str, Any]]],
        announcement_channels: Dict[str, str]
    ) -> Tuple[Dict[str, Any], AnalysisLog]:
        """Analyze social media and announcements for contract information.
        
        Args:
            project_name: Name of the project
            social_content: Social media content by platform
            announcement_channels: URLs of announcement channels
            
        Returns:
            Tuple of (social analysis, analysis log)
        """
        context = {
            "project_name": project_name,
            "social_content_json": social_content,
            "announcement_channels_json": announcement_channels,
            "extracted_information": {
                "contract_addresses": [],
                "whitelist_announcements": [],
                "project_milestones": [],
                "community_insights": []
            }
        }
        
        return await self.run(
            task="Analyze social media and announcements for contract information",
            context=context,
            initial_state="social_analysis"
        )
    
    async def _execute_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute crawler-specific actions.
        
        Args:
            action: Action to execute
            
        Returns:
            Result of action execution
        """
        action_type = action.get("type", "").lower()
        params = action.get("params", {})
        
        if action_type == "fetch_defillama_data":
            # Fetch project data from DeFiLlama
            project_name = params.get("project_name") or self.context.get("project_name")
            result = await self.defillama_crawler.fetch_project_data(project_name)
            return {"defillama_data": result}
            
        elif action_type == "crawl_website":
            # Crawl project website
            website_url = params.get("website") or self.context.get("website")
            result = await self.website_crawler.crawl(website_url)
            return {"website_data": result}
            
        elif action_type == "crawl_github":
            # Crawl GitHub repository
            github_url = params.get("github_url") or self.context.get("github_url")
            result = await self.github_crawler.crawl(github_url)
            return {"github_data": result}
            
        elif action_type == "search_contract_addresses":
            # Search for contract addresses in content
            content = params.get("content", "")
            blockchain = params.get("blockchain")
            result = self.contract_extractor.extract_addresses(content, blockchain)
            return {"found_addresses": result}
            
        elif action_type == "extract_structured_data":
            # Extract structured data from content
            content = params.get("content", "")
            data_type = params.get("data_type", "")
            
            if data_type == "whitelist":
                result = self.whitelist_extractor.extract(content)
            elif data_type == "project_details":
                result = self.project_details_extractor.extract(content)
            else:
                result = {"error": f"Unsupported data type: {data_type}"}
                
            return {"extracted_data": result}
            
        elif action_type == "verify_contract_address":
            # Verify if address is a valid contract
            address = params.get("address", "")
            blockchain = params.get("blockchain", "ethereum")
            result = await self.contract_extractor.verify_contract(address, blockchain)
            return {"verification_result": result}
            
        elif action_type == "aggregate_results":
            # Aggregate results from multiple sources
            sources = params.get("sources", {})
            result = self._aggregate_results(sources)
            return {"aggregated_data": result}
            
        else:
            # Fall back to base implementation
            return await super()._execute_action(action)
    
    def _aggregate_results(self, sources: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate results from multiple sources.
        
        Args:
            sources: Results from different sources
            
        Returns:
            Aggregated results
        """
        # Collect contract addresses from all sources
        all_addresses = set()
        address_details = []
        
        for source_name, source_data in sources.items():
            if source_name == "defillama_data" and source_data.get("success"):
                addresses = source_data.get("addresses", {})
                for chain, chain_addresses in addresses.items():
                    for address in chain_addresses:
                        all_addresses.add((address, chain))
                        address_details.append({
                            "address": address,
                            "blockchain": chain,
                            "source": "defillama",
                            "confidence": "high"
                        })
            
            elif source_name == "website_data" and source_data.get("success"):
                for address_info in source_data.get("contract_addresses", []):
                    address = address_info.get("address")
                    blockchain = address_info.get("blockchain")
                    if address and blockchain:
                        all_addresses.add((address, blockchain))
                        address_details.append({
                            "address": address,
                            "blockchain": blockchain,
                            "source": "website",
                            "context": address_info.get("context", ""),
                            "confidence": "medium"
                        })
            
            elif source_name == "github_data" and source_data.get("success"):
                # Extract addresses from deployment files or readmes
                # This would be more complex in a real implementation
                pass
        
        # Collect documentation links
        doc_links = []
        if sources.get("website_data", {}).get("success"):
            doc_links.extend(sources.get("website_data", {}).get("documentation_links", []))
        
        # Collect project details
        project_details = {}
        
        # DeFiLlama is considered high-quality source for project details
        if sources.get("defillama_data", {}).get("success"):
            defillama_data = sources.get("defillama_data", {})
            project_details = {
                "name": defillama_data.get("name"),
                "description": defillama_data.get("description"),
                "category": defillama_data.get("category"),
                "tvl": defillama_data.get("tvl"),
                "chains": defillama_data.get("chains", []),
                "website": defillama_data.get("website"),
                "twitter": defillama_data.get("twitter"),
                "github": defillama_data.get("github"),
                "source": "defillama"
            }
        
        # Return aggregated results
        return {
            "contract_addresses": address_details,
            "unique_address_count": len(all_addresses),
            "documentation_links": doc_links,
            "project_details": project_details,
            "sources_used": list(sources.keys())
        }
