"""Crawler agent for gathering project information."""

import logging
import json
import re
from typing import Dict, Any, List, Optional, Tuple, Set

from crewai import Agent

from ...utils.ai_client import AIClient
from ...prompts.prompt_manager import PromptManager
from ...utils.blockchain_client import BlockchainClient
from ...utils.firecrawl_client import FirecrawlClient
from ...services.defillama_service import DefiLlamaService

logger = logging.getLogger(__name__)


class CrawlerAgent:
    """Crawler agent responsible for gathering project information."""
    
    def __init__(
        self,
        ai_client: AIClient,
        prompt_manager: PromptManager,
        blockchain_client: BlockchainClient,
        firecrawl_client: FirecrawlClient,
        defillama_service: DefiLlamaService
    ):
        """Initialize crawler agent.
        
        Args:
            ai_client: AI client for agent
            prompt_manager: Prompt manager for agent templates
            blockchain_client: Blockchain client for interactions
            firecrawl_client: Firecrawl client for web crawling
            defillama_service: DeFiLlama service for project data
        """
        self.ai_client = ai_client
        self.prompt_manager = prompt_manager
        self.blockchain_client = blockchain_client
        self.firecrawl_client = firecrawl_client
        self.defillama_service = defillama_service
        self._agent = None
    
    def create_agent(
        self,
        name: str = "Crawler",
        goal: str = "Gather comprehensive information about blockchain projects, including contracts, documentation, and technical details",
        backstory: Optional[str] = None,
        verbose: bool = True
    ) -> Agent:
        """Create a CrewAI agent for the crawler.
        
        Args:
            name: Agent name
            goal: Agent goal
            backstory: Agent backstory
            verbose: Whether to enable verbose logging
            
        Returns:
            CrewAI Agent instance
        """
        if not backstory:
            backstory = """You are a specialized crawler agent with expertise in extracting
            blockchain project information from multiple sources. You have extensive knowledge
            of cryptocurrency project structures, smart contract patterns, and documentation styles.
            You can efficiently navigate project websites, GitHub repositories, blockchain explorers,
            and other sources to gather relevant information about contracts, whitelist mechanisms,
            and project architecture. You are detail-oriented and thorough in your data collection."""
        
        # Custom callback to use ai_client
        async def callback_function(message):
            response = await self.ai_client.get_completion(message, temperature=0.1, max_tokens=4000)
            return response["choices"][0]["message"]["content"]
        
        # Create the agent
        self._agent = Agent(
            name=name,
            role="Blockchain Project Crawler",
            goal=goal,
            backstory=backstory,
            verbose=verbose,
            allow_delegation=False,
            tools=[
                self.crawl_project_website,
                self.crawl_github_repository,
                self.search_for_project_info,
                self.extract_contract_addresses,
                self.get_project_tvl_data
            ],
            async_callbacks=[callback_function]
        )
        
        return self._agent
    
    def get_agent(self) -> Agent:
        """Get the CrewAI agent instance.
        
        Returns:
            CrewAI Agent instance
        """
        if not self._agent:
            return self.create_agent()
        return self._agent
    
    async def crawl_project_website(self, website_url: str) -> Dict[str, Any]:
        """Crawl project website to extract information.
        
        Args:
            website_url: Project website URL
            
        Returns:
            Extracted website information
        """
        try:
            # First scrape the main page
            main_page = await self.firecrawl_client.scrape_url(
                website_url,
                formats=["markdown", "links"],
                only_main_content=True
            )
            
            # Get all links from the main page
            links = main_page.get("links", [])
            
            # Filter for documentation, whitepaper, and other relevant pages
            docs_links = [link for link in links if any(term in link.lower() 
                         for term in ["docs", "whitepaper", "documentation", "about", "tokenomics"])]
            
            # Limit to top 5 most relevant docs links
            docs_links = docs_links[:5]
            
            # Scrape each documentation page
            docs_content = []
            for link in docs_links:
                try:
                    # Ensure absolute URL
                    if not link.startswith(("http://", "https://")):
                        if link.startswith("/"):
                            # Absolute path
                            parts = website_url.split("/")
                            base = parts[0] + "//" + parts[2]
                            link = base + link
                        else:
                            # Relative path
                            link = website_url.rstrip("/") + "/" + link
                    
                    # Scrape the documentation page
                    doc_page = await self.firecrawl_client.scrape_url(
                        link,
                        formats=["markdown"],
                        only_main_content=True
                    )
                    
                    # Add to docs content
                    if "markdown" in doc_page:
                        docs_content.append({
                            "url": link,
                            "content": doc_page["markdown"]
                        })
                except Exception as e:
                    logger.warning(f"Error scraping documentation page {link}: {e}")
            
            # Extract potential contract addresses from all pages
            all_content = main_page.get("markdown", "") + "\n" + "\n".join(
                doc["content"] for doc in docs_content
            )
            
            # Extract contract addresses
            contract_addresses = self._extract_addresses_from_text(all_content)
            
            # Extract social links
            social_links = self._extract_social_links(links)
            
            # Compose the result
            result = {
                "website_url": website_url,
                "main_content": main_page.get("markdown", ""),
                "documentation_pages": docs_content,
                "potential_contract_addresses": list(contract_addresses),
                "social_links": social_links,
                "all_links": links
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error crawling website {website_url}: {e}")
            return {
                "website_url": website_url,
                "error": str(e),
                "main_content": "",
                "documentation_pages": [],
                "potential_contract_addresses": [],
                "social_links": {},
                "all_links": []
            }
    
    async def crawl_github_repository(self, github_url: str) -> Dict[str, Any]:
        """Crawl GitHub repository for project information.
        
        Args:
            github_url: GitHub repository URL
            
        Returns:
            Extracted GitHub information
        """
        try:
            # Normalize GitHub URL
            if not github_url.startswith(("http://", "https://")):
                github_url = "https://github.com/" + github_url.lstrip("/")
            
            # Scrape the main repository page
            repo_page = await self.firecrawl_client.scrape_url(
                github_url,
                formats=["markdown", "links"],
                only_main_content=False
            )
            
            # Get all links from the repository
            links = repo_page.get("links", [])
            
            # Filter for contract files
            contract_file_links = [link for link in links if any(ext in link.lower() 
                                for ext in [".sol", "/contracts/", "/contracts"])]
            
            # Limit to top 10 most relevant contract files
            contract_file_links = contract_file_links[:10]
            
            # Scrape each contract file
            contract_files = []
            for link in contract_file_links:
                try:
                    # Ensure absolute URL
                    if not link.startswith(("http://", "https://")):
                        if link.startswith("/"):
                            # Absolute path
                            parts = github_url.split("/")
                            base = parts[0] + "//" + parts[2]
                            link = base + link
                        else:
                            # Relative path
                            link = github_url.rstrip("/") + "/" + link
                    
                    # Adjust link for raw content if needed
                    if "github.com" in link and "/blob/" in link:
                        # Convert to raw content URL
                        link = link.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
                    
                    # Scrape the contract file
                    contract_page = await self.firecrawl_client.scrape_url(
                        link,
                        formats=["rawHtml"],  # Use rawHtml to get the code
                        only_main_content=False
                    )
                    
                    # Add to contract files
                    if "rawHtml" in contract_page:
                        # Extract just the code from the raw HTML
                        code = contract_page["rawHtml"]
                        # Clean up HTML if needed
                        if "<" in code and ">" in code:
                            # Simple HTML stripping for code display
                            code = re.sub(r'<[^>]+>', '', code)
                        
                        contract_files.append({
                            "url": link,
                            "code": code
                        })
                except Exception as e:
                    logger.warning(f"Error scraping contract file {link}: {e}")
            
            # Look for README file
            readme_content = ""
            for content_type in ["markdown", "rawHtml"]:
                if content_type in repo_page and repo_page[content_type]:
                    readme_content = repo_page[content_type]
                    break
            
            # Extract contract addresses from all files
            all_content = readme_content + "\n" + "\n".join(
                contract["code"] for contract in contract_files
            )
            
            # Extract contract addresses
            contract_addresses = self._extract_addresses_from_text(all_content)
            
            # Compose the result
            result = {
                "github_url": github_url,
                "readme_content": readme_content,
                "contract_files": contract_files,
                "potential_contract_addresses": list(contract_addresses),
                "all_links": links
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error crawling GitHub repository {github_url}: {e}")
            return {
                "github_url": github_url,
                "error": str(e),
                "readme_content": "",
                "contract_files": [],
                "potential_contract_addresses": [],
                "all_links": []
            }
    
    async def search_for_project_info(self, project_name: str) -> Dict[str, Any]:
        """Search for project information using Firecrawl search.
        
        Args:
            project_name: Name of the project
            
        Returns:
            Search results
        """
        try:
            # Search queries
            queries = [
                f"{project_name} blockchain project",
                f"{project_name} whitelist smart contract",
                f"{project_name} github repository",
                f"{project_name} documentation"
            ]
            
            all_results = []
            for query in queries:
                # Search with Firecrawl
                search_results = await self.firecrawl_client.search(
                    query,
                    limit=5,
                    scrape_options={
                        "onlyMainContent": True,
                        "formats": ["markdown"]
                    }
                )
                
                # Add results
                if "results" in search_results:
                    all_results.extend(search_results["results"])
            
            # Extract unique URLs
            unique_urls = {}
            for result in all_results:
                url = result.get("url", "")
                if url and url not in unique_urls:
                    unique_urls[url] = result
            
            # Extract website and GitHub URLs
            website_url = None
            github_url = None
            
            for url in unique_urls.keys():
                if not website_url and self._is_project_website(url, project_name):
                    website_url = url
                
                if not github_url and "github.com" in url.lower():
                    # Check if this is likely the project's repository
                    if project_name.lower().replace(" ", "") in url.lower().replace("-", "").replace("_", ""):
                        github_url = url
            
            # Compose the result
            result = {
                "project_name": project_name,
                "website_url": website_url,
                "github_url": github_url,
                "search_results": list(unique_urls.values())
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error searching for project info {project_name}: {e}")
            return {
                "project_name": project_name,
                "error": str(e),
                "website_url": None,
                "github_url": None,
                "search_results": []
            }
    
    async def extract_contract_addresses(self, content: str) -> List[Dict[str, str]]:
        """Extract contract addresses from text content.
        
        Args:
            content: Text content to extract addresses from
            
        Returns:
            List of contract addresses with blockchains
        """
        addresses = self._extract_addresses_from_text(content)
        
        # Verify each address and determine blockchain
        verified_addresses = []
        for address in addresses:
            for blockchain in ["ethereum", "bsc", "polygon", "arbitrum", "optimism"]:
                try:
                    # Check if address exists on this blockchain
                    is_valid = await self.blockchain_client.is_valid_contract(address, blockchain)
                    if is_valid:
                        verified_addresses.append({
                            "address": address,
                            "blockchain": blockchain
                        })
                        break  # Found the right blockchain
                except Exception as e:
                    logger.debug(f"Error validating address {address} on {blockchain}: {e}")
        
        return verified_addresses
    
    async def get_project_tvl_data(self, project_name: str) -> Dict[str, Any]:
        """Get project TVL data from DeFiLlama.
        
        Args:
            project_name: Name of the project
            
        Returns:
            Project TVL data
        """
        try:
            tvl_data = await self.defillama_service.fetch_project_data(project_name)
            
            if not tvl_data:
                return {
                    "project_name": project_name,
                    "tvl_found": False,
                    "tvl_data": None
                }
            
            return {
                "project_name": project_name,
                "tvl_found": True,
                "tvl_data": tvl_data
            }
            
        except Exception as e:
            logger.error(f"Error getting TVL data for {project_name}: {e}")
            return {
                "project_name": project_name,
                "error": str(e),
                "tvl_found": False,
                "tvl_data": None
            }
    
    def _extract_addresses_from_text(self, text: str) -> Set[str]:
        """Extract Ethereum-like addresses from text.
        
        Args:
            text: Text to extract addresses from
            
        Returns:
            Set of unique addresses
        """
        # Ethereum address pattern
        pattern = r'0x[a-fA-F0-9]{40}'
        
        # Find all matches
        addresses = set(re.findall(pattern, text))
        
        return addresses
    
    def _extract_social_links(self, links: List[str]) -> Dict[str, str]:
        """Extract social media links from a list of URLs.
        
        Args:
            links: List of URLs
            
        Returns:
            Dictionary of social media links
        """
        social_links = {}
        
        for link in links:
            link_lower = link.lower()
            
            if "twitter.com" in link_lower or "x.com" in link_lower:
                social_links["twitter"] = link
            elif "t.me" in link_lower or "telegram.org" in link_lower:
                social_links["telegram"] = link
            elif "discord.com" in link_lower or "discord.gg" in link_lower:
                social_links["discord"] = link
            elif "medium.com" in link_lower:
                social_links["medium"] = link
            elif "github.com" in link_lower:
                social_links["github"] = link
            elif "linkedin.com" in link_lower:
                social_links["linkedin"] = link
            elif "youtube.com" in link_lower:
                social_links["youtube"] = link
            elif "reddit.com" in link_lower:
                social_links["reddit"] = link
            elif "facebook.com" in link_lower:
                social_links["facebook"] = link
            elif "instagram.com" in link_lower:
                social_links["instagram"] = link
        
        return social_links
    
    def _is_project_website(self, url: str, project_name: str) -> bool:
        """Check if a URL is likely the project's website.
        
        Args:
            url: URL to check
            project_name: Project name
            
        Returns:
            True if likely the project website, False otherwise
        """
        # Extract domain
        domain = url.lower()
        for prefix in ["https://", "http://", "www."]:
            domain = domain.replace(prefix, "")
        
        domain = domain.split("/")[0]  # Remove path
        
        # Clean project name for comparison
        clean_name = project_name.lower().replace(" ", "").replace("-", "").replace("_", "")
        clean_domain = domain.replace(".", "").replace("-", "").replace("_", "")
        
        # Check if project name is in domain
        if clean_name in clean_domain:
            return True
        
        # Handle special cases for common domains
        if domain.endswith(".finance") or domain.endswith(".io") or domain.endswith(".org"):
            # Extract the subdomain
            subdomain = domain.split(".")[0]
            if clean_name == subdomain or clean_name in subdomain:
                return True
        
        return False
