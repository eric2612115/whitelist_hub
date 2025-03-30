"""Source crawlers for different platforms."""

import logging
import json
import re
from typing import Dict, List, Any, Optional
import aiohttp
import asyncio

logger = logging.getLogger(__name__)


class WebsiteCrawler:
    """Crawler for project websites."""
    
    def __init__(self, user_agent: Optional[str] = None):
        """Initialize website crawler.
        
        Args:
            user_agent: User agent for HTTP requests
        """
        self.user_agent = user_agent or "WhitelistHub/0.1.0 (Data Collection Bot)"
        
    async def crawl(self, url: str) -> Dict[str, Any]:
        """Crawl a website for information.
        
        Args:
            url: Website URL
            
        Returns:
            Crawled website data
        """
        if not url:
            return {"success": False, "message": "No URL provided"}
        
        try:
            headers = {
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=30) as response:
                    if response.status != 200:
                        return {
                            "success": False, 
                            "message": f"Failed to fetch website: {response.status}"
                        }
                    
                    html_content = await response.text()
                    
                    # Extract links 
                    from .data_extractors import ProjectDetailsExtractor
                    project_details_extractor = ProjectDetailsExtractor()
                    
                    links = project_details_extractor.extract_links(html_content, url)
                    
                    # Find documentation links
                    docs_links = project_details_extractor.find_documentation_links(links, url)
                    
                    # Find blog link
                    blog_link = project_details_extractor.find_blog_link(links, url)
                    
                    # Extract contract addresses
                    from .data_extractors import ContractExtractor
                    contract_extractor = ContractExtractor(None)  # Pass None as we don't need blockchain_client here
                    
                    contract_addresses = contract_extractor.extract_addresses(html_content)
                    
                    # Extract project details
                    project_details = project_details_extractor.extract(html_content)
                    
                    # Extract whitelist information
                    from .data_extractors import WhitelistExtractor
                    whitelist_extractor = WhitelistExtractor()
                    
                    whitelist_info = whitelist_extractor.extract(html_content)
                    
                    return {
                        "success": True,
                        "url": url,
                        "title": project_details.get("title"),
                        "description": project_details.get("description"),
                        "categories": project_details.get("categories", []),
                        "links": links,
                        "documentation_links": docs_links,
                        "blog_link": blog_link,
                        "contract_addresses": contract_addresses,
                        "whitelist_info": whitelist_info,
                        "has_whitelist_info": bool(whitelist_info.get("whitelist_paragraphs"))
                    }
            
        except asyncio.TimeoutError:
            return {"success": False, "message": "Timeout while crawling website"}
        except Exception as e:
            logger.error(f"Error crawling website: {e}")
            return {"success": False, "message": str(e)}
    
    async def crawl_documentation(self, url: str) -> Dict[str, Any]:
        """Crawl documentation page.
        
        Args:
            url: Documentation URL
            
        Returns:
            Crawled documentation data
        """
        result = await self.crawl(url)
        
        if not result.get("success"):
            return result
        
        # Enhance result with documentation-specific information
        result["is_documentation"] = True
        
        # Extract more contract addresses
        html_content = result.get("html_content", "")
        
        # Look for deployment info
        from .data_extractors import ContractExtractor
        contract_extractor = ContractExtractor(None)
        
        deployment_data = contract_extractor.extract_deployment_data(html_content)
        result["deployment_data"] = deployment_data
        
        return result


class GithubCrawler:
    """Crawler for GitHub repositories."""
    
    def __init__(self, github_token: Optional[str] = None):
        """Initialize GitHub crawler.
        
        Args:
            github_token: GitHub API token
        """
        self.github_token = github_token
        self.headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        
        if github_token:
            self.headers["Authorization"] = f"token {github_token}"
    
    async def crawl(self, url: str) -> Dict[str, Any]:
        """Crawl a GitHub repository.
        
        Args:
            url: GitHub repository URL
            
        Returns:
            Crawled repository data
        """
        if not url:
            return {"success": False, "message": "No GitHub URL provided"}
        
        # Extract owner and repo from URL
        match = re.match(r"https?://github\.com/([^/]+)/([^/]+)", url)
        if not match:
            return {"success": False, "message": "Invalid GitHub URL"}
        
        owner, repo = match.groups()
        
        try:
            # Fetch repository info
            repo_data = await self._fetch_repo_info(owner, repo)
            if not repo_data.get("success"):
                return repo_data
            
            # Fetch repository contents
            contents = await self._fetch_repo_contents(owner, repo)
            if not contents.get("success"):
                return contents
            
            # Fetch README if available
            readme = await self._fetch_readme(owner, repo)
            
            # Find contract and ABI files
            sol_files, abi_files = self._find_contract_files(contents.get("items", []), owner, repo)
            
            # Find deployment scripts
            deployment_files = self._find_deployment_files(contents.get("items", []), owner, repo)
            
            return {
                "success": True,
                "url": url,
                "owner": owner,
                "repo": repo,
                "repo_data": repo_data.get("data"),
                "readme": readme.get("content") if readme.get("success") else None,
                "sol_files": sol_files,
                "abi_files": abi_files,
                "deployment_files": deployment_files,
                "contract_count": len(sol_files),
                "has_deployment_info": bool(deployment_files)
            }
            
        except Exception as e:
            logger.error(f"Error crawling GitHub repository: {e}")
            return {"success": False, "message": str(e)}
    
    async def _fetch_repo_info(self, owner: str, repo: str) -> Dict[str, Any]:
        """Fetch repository information.
        
        Args:
            owner: Repository owner
            repo: Repository name
            
        Returns:
            Repository information
        """
        url = f"https://api.github.com/repos/{owner}/{repo}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as response:
                if response.status != 200:
                    return {
                        "success": False,
                        "message": f"Failed to fetch repository info: {response.status}"
                    }
                
                data = await response.json()
                return {"success": True, "data": data}
    
    async def _fetch_repo_contents(self, owner: str, repo: str, path: str = "") -> Dict[str, Any]:
        """Fetch repository contents.
        
        Args:
            owner: Repository owner
            repo: Repository name
            path: Path within repository
            
        Returns:
            Repository contents
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as response:
                if response.status != 200:
                    return {
                        "success": False,
                        "message": f"Failed to fetch repository contents: {response.status}"
                    }
                
                items = await response.json()
                return {"success": True, "items": items}
    
    async def _fetch_readme(self, owner: str, repo: str) -> Dict[str, Any]:
        """Fetch repository README.
        
        Args:
            owner: Repository owner
            repo: Repository name
            
        Returns:
            README content
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/readme"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as response:
                if response.status != 200:
                    return {
                        "success": False,
                        "message": f"Failed to fetch README: {response.status}"
                    }
                
                data = await response.json()
                
                # Decode content
                import base64
                content = base64.b64decode(data.get("content", "")).decode("utf-8")
                
                return {"success": True, "content": content}
    
    def _find_contract_files(self, items: List[Dict[str, Any]], owner: str, repo: str) -> tuple:
        """Find Solidity contract files and ABI files.
        
        Args:
            items: Repository contents
            owner: Repository owner
            repo: Repository name
            
        Returns:
            Tuple of (sol_files, abi_files)
        """
        sol_files = []
        abi_files = []
        
        contracts_dir = None
        build_dir = None
        
        # First, find key directories
        for item in items:
            if item.get("type") == "dir":
                name = item.get("name", "").lower()
                if name == "contracts":
                    contracts_dir = item
                elif name in ["build", "artifacts", "abis"]:
                    build_dir = item
        
        # Process all items recursively
        self._process_items_recursively(items, "", sol_files, abi_files, owner, repo)
        
        # Prioritize contracts directory if found
        if contracts_dir:
            # This would be an async call in a real implementation
            # contracts_contents = await self._fetch_repo_contents(owner, repo, contracts_dir.get("path"))
            # self._process_items_recursively(contracts_contents.get("items", []), contracts_dir.get("path"), sol_files, abi_files, owner, repo)
            pass
        
        # Prioritize build directory if found
        if build_dir:
            # This would be an async call in a real implementation
            # build_contents = await self._fetch_repo_contents(owner, repo, build_dir.get("path"))
            # self._process_items_recursively(build_contents.get("items", []), build_dir.get("path"), sol_files, abi_files, owner, repo)
            pass
        
        return sol_files, abi_files
    
    def _process_items_recursively(
        self, 
        items: List[Dict[str, Any]], 
        base_path: str, 
        sol_files: List[Dict[str, Any]], 
        abi_files: List[Dict[str, Any]], 
        owner: str, 
        repo: str
    ):
        """Process repository items recursively.
        
        Args:
            items: Repository contents
            base_path: Base path for items
            sol_files: List to collect Solidity files
            abi_files: List to collect ABI files
            owner: Repository owner
            repo: Repository name
        """
        for item in items:
            if item.get("type") != "file":
                continue
            
            name = item.get("name", "")
            path = item.get("path", "")
            html_url = item.get("html_url", "")
            
            if name.endswith(".sol"):
                sol_files.append({
                    "name": name,
                    "path": path,
                    "url": html_url,
                    "raw_url": f"https://raw.githubusercontent.com/{owner}/{repo}/master/{path}"
                })
            elif name.endswith(".json"):
                # Check if this is likely an ABI file
                if "abi" in name.lower() or "artifact" in name.lower() or "build" in path.lower():
                    abi_files.append({
                        "name": name,
                        "path": path,
                        "url": html_url,
                        "raw_url": f"https://raw.githubusercontent.com/{owner}/{repo}/master/{path}"
                    })
    
    def _find_deployment_files(self, items: List[Dict[str, Any]], owner: str, repo: str) -> List[Dict[str, Any]]:
        """Find deployment script files.
        
        Args:
            items: Repository contents
            owner: Repository owner
            repo: Repository name
            
        Returns:
            List of deployment files
        """
        deployment_files = []
        
        # Keywords that suggest deployment scripts
        deploy_keywords = [
            "deploy", "migration", "script", "config", "network", "address"
        ]
        
        for item in items:
            if item.get("type") != "file":
                continue
            
            name = item.get("name", "").lower()
            path = item.get("path", "").lower()
            
            # Check if file name suggests deployment info
            is_deployment_file = any(keyword in name for keyword in deploy_keywords)
            
            # Check if it's in a deploy-related directory
            is_in_deploy_dir = any(keyword in path for keyword in ["deploy", "script", "migration"])
            
            # Check if it's a common deployment file type
            is_deployment_filetype = name.endswith((".js", ".ts", ".json", ".yaml", ".toml"))
            
            if (is_deployment_file or is_in_deploy_dir) and is_deployment_filetype:
                deployment_files.append({
                    "name": item.get("name"),
                    "path": item.get("path"),
                    "url": item.get("html_url"),
                    "raw_url": f"https://raw.githubusercontent.com/{owner}/{repo}/master/{item.get('path')}"
                })
        
        return deployment_files


class DefiLlamaCrawler:
    """Crawler for DeFiLlama project data."""
    
    async def fetch_project_data(self, project_name: str) -> Dict[str, Any]:
        """Fetch project data from DeFiLlama.
        
        Args:
            project_name: Name of the project
            
        Returns:
            Project data from DeFiLlama
        """
        try:
            # Fetch the list of all protocols
            async with aiohttp.ClientSession() as session:
                async with session.get("https://api.llama.fi/protocols") as response:
                    if response.status != 200:
                        return {
                            "success": False,
                            "message": f"Failed to fetch protocols: {response.status}"
                        }
                    
                    protocols = await response.json()
            
            # Find the project by name
            found_project = None
            for project in protocols:
                if project.get("name", "").lower() == project_name.lower():
                    found_project = project
                    break
            
            # If exact match not found, try partial match
            if not found_project:
                for project in protocols:
                    if project_name.lower() in project.get("name", "").lower():
                        found_project = project
                        break
            
            if not found_project:
                return {
                    "success": False,
                    "message": f"Project '{project_name}' not found in DeFiLlama"
                }
            
            # Get detailed project information
            slug = found_project.get("slug")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://api.llama.fi/protocol/{slug}") as response:
                    if response.status != 200:
                        return {
                            "success": False,
                            "message": f"Failed to fetch project details: {response.status}"
                        }
                    
                    project_details = await response.json()
            
            # Extract important information
            result = {
                "success": True,
                "name": project_details.get("name"),
                "description": project_details.get("description"),
                "category": project_details.get("category"),
                "tvl": project_details.get("tvl"),
                "chains": project_details.get("chains", []),
                "website": project_details.get("url"),
                "twitter": project_details.get("twitter"),
                "github": project_details.get("github"),
                "audit_links": project_details.get("audit_links", []),
                "addresses": self._extract_addresses(project_details)
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error fetching data from DeFiLlama: {e}")
            return {"success": False, "message": str(e)}
    
    def _extract_addresses(self, project_details: Dict[str, Any]) -> Dict[str, List[str]]:
        """Extract contract addresses from project details.
        
        Args:
            project_details: Project details from DeFiLlama
            
        Returns:
            Contract addresses by chain
        """
        addresses = {}
        
        # Extract addresses from different sources in DeFiLlama data
        
        # Check for addresses in tokens
        tokens = project_details.get("tokens", [])
        for token in tokens:
            chain = token.get("chain")
            address = token.get("address")
            
            if chain and address:
                if chain not in addresses:
                    addresses[chain] = []
                
                addresses[chain].append(address)
        
        # Check for addresses in pool data
        pools = project_details.get("pools", [])
        for pool in pools:
            chain = pool.get("chain")
            address = pool.get("address")
            
            if chain and address:
                if chain not in addresses:
                    addresses[chain] = []
                
                addresses[chain].append(address)
        
        return addresses


class SocialMediaCrawler:
    """Crawler for social media content."""
    
    async def crawl_twitter(self, twitter_handle: str) -> Dict[str, Any]:
        """Crawl Twitter for project information.
        
        Args:
            twitter_handle: Twitter handle
            
        Returns:
            Crawled Twitter data
        """
        # Note: In a real implementation, this would use Twitter API
        # This is a placeholder that would be expanded with actual API calls
        
        if not twitter_handle:
            return {"success": False, "message": "No Twitter handle provided"}
        
        # Remove @ if present
        if twitter_handle.startswith("@"):
            twitter_handle = twitter_handle[1:]
        
        try:
            # Simulate API call
            return {
                "success": True,
                "handle": twitter_handle,
                "url": f"https://twitter.com/{twitter_handle}",
                "tweets": [],  # Would be populated with actual tweets
                "profile": {
                    "name": "",
                    "description": "",
                    "location": "",
                    "website": ""
                }
            }
            
        except Exception as e:
            logger.error(f"Error crawling Twitter: {e}")
            return {"success": False, "message": str(e)}
    
    async def crawl_telegram(self, telegram_group: str) -> Dict[str, Any]:
        """Crawl Telegram for project information.
        
        Args:
            telegram_group: Telegram group name
            
        Returns:
            Crawled Telegram data
        """
        # Note: In a real implementation, this would use Telegram API
        # This is a placeholder that would be expanded with actual API calls
        
        if not telegram_group:
            return {"success": False, "message": "No Telegram group provided"}
        
        try:
            # Simulate API call
            return {
                "success": True,
                "group": telegram_group,
                "url": f"https://t.me/{telegram_group}",
                "messages": [],  # Would be populated with actual messages
                "group_info": {
                    "name": "",
                    "description": "",
                    "member_count": 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error crawling Telegram: {e}")
            return {"success": False, "message": str(e)}
    
    async def crawl_discord(self, discord_invite: str) -> Dict[str, Any]:
        """Crawl Discord for project information.
        
        Args:
            discord_invite: Discord invite code
            
        Returns:
            Crawled Discord data
        """
        # Note: In a real implementation, this would use Discord API
        # This is a placeholder that would be expanded with actual API calls
        
        if not discord_invite:
            return {"success": False, "message": "No Discord invite provided"}
        
        try:
            # Extract invite code if full URL
            if discord_invite.startswith("https://discord.gg/"):
                invite_code = discord_invite.split("/")[-1]
            else:
                invite_code = discord_invite
            
            # Simulate API call
            return {
                "success": True,
                "invite_code": invite_code,
                "url": f"https://discord.gg/{invite_code}",
                "messages": [],  # Would be populated with actual messages
                "server_info": {
                    "name": "",
                    "description": "",
                    "member_count": 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error crawling Discord: {e}")
            return {"success": False, "message": str(e)}
