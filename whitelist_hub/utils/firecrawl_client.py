"""Client for Firecrawl.dev API."""

import logging
import aiohttp
import json
from typing import Dict, List, Any, Optional, Union
from ..core.config import settings

logger = logging.getLogger(__name__)


class FirecrawlClient:
    """Client for firecrawl.dev API for advanced web crawling and scraping."""
    
    def __init__(self, api_key: Optional[str] = None, timeout: int = 60):
        """Initialize Firecrawl client.
        
        Args:
            api_key: API key for Firecrawl
            timeout: Timeout for API calls in seconds
        """
        self.api_key = api_key or settings.FIRECRAWL_API_KEY
        if not self.api_key:
            raise ValueError("Firecrawl API key not provided or not found in settings")
        
        self.timeout = timeout
        self.base_url = "https://api.firecrawl.dev"
    
    async def scrape_url(
        self, 
        url: str, 
        formats: List[str] = ["markdown"], 
        only_main_content: bool = True,
        wait_for: Optional[int] = None,
        actions: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Scrape a single URL.
        
        Args:
            url: The URL to scrape
            formats: Content formats to extract (markdown, html, rawHtml, screenshot, links)
            only_main_content: Extract only the main content, filtering out navigation, footers, etc.
            wait_for: Time in milliseconds to wait for dynamic content
            actions: List of actions to perform before scraping (click, scroll, etc.)
            
        Returns:
            Scraped content in requested formats
        """
        endpoint = f"{self.base_url}/scrape"
        
        payload = {
            "url": url,
            "formats": formats,
            "onlyMainContent": only_main_content
        }
        
        if wait_for:
            payload["waitFor"] = wait_for
            
        if actions:
            payload["actions"] = actions
        
        return await self._make_request("POST", endpoint, payload)
    
    async def map_urls(
        self, 
        url: str, 
        include_subdomains: bool = False,
        ignore_sitemap: bool = False,
        sitemap_only: bool = False,
        limit: Optional[int] = None,
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        """Discover URLs from a starting point.
        
        Args:
            url: Starting URL for URL discovery
            include_subdomains: Include URLs from subdomains
            ignore_sitemap: Skip sitemap.xml discovery
            sitemap_only: Only use sitemap.xml for discovery
            limit: Maximum number of URLs to return
            search: Optional search term to filter URLs
            
        Returns:
            List of discovered URLs
        """
        endpoint = f"{self.base_url}/map"
        
        payload = {
            "url": url,
            "includeSubdomains": include_subdomains,
            "ignoreSitemap": ignore_sitemap,
            "sitemapOnly": sitemap_only
        }
        
        if limit:
            payload["limit"] = limit
            
        if search:
            payload["search"] = search
        
        return await self._make_request("POST", endpoint, payload)
    
    async def crawl_site(
        self, 
        url: str, 
        max_depth: int = 2,
        max_pages: int = 50,
        include_paths: Optional[List[str]] = None,
        exclude_paths: Optional[List[str]] = None,
        scrape_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Start an asynchronous crawl of multiple pages.
        
        Args:
            url: Starting URL for the crawl
            max_depth: Maximum link depth to crawl
            max_pages: Maximum number of pages to crawl
            include_paths: Only crawl these URL paths
            exclude_paths: URL paths to exclude from crawling
            scrape_options: Options for scraping each page
            
        Returns:
            Crawl job information including ID
        """
        endpoint = f"{self.base_url}/crawl"
        
        payload = {
            "url": url,
            "maxDepth": max_depth,
            "limit": max_pages
        }
        
        if include_paths:
            payload["includePaths"] = include_paths
            
        if exclude_paths:
            payload["excludePaths"] = exclude_paths
            
        if scrape_options:
            payload["scrapeOptions"] = scrape_options
        
        return await self._make_request("POST", endpoint, payload)
    
    async def check_crawl_status(self, job_id: str) -> Dict[str, Any]:
        """Check the status of a crawl job.
        
        Args:
            job_id: Crawl job ID to check
            
        Returns:
            Status of the crawl job
        """
        endpoint = f"{self.base_url}/check-crawl-status"
        
        payload = {
            "id": job_id
        }
        
        return await self._make_request("POST", endpoint, payload)
    
    async def search(
        self, 
        query: str, 
        limit: int = 5, 
        scrape_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Search and retrieve content from web pages.
        
        Args:
            query: Search query string
            limit: Maximum number of results to return
            scrape_options: Options for scraping search results
            
        Returns:
            Search results
        """
        endpoint = f"{self.base_url}/search"
        
        payload = {
            "query": query,
            "limit": limit
        }
        
        if scrape_options:
            payload["scrapeOptions"] = scrape_options
        
        return await self._make_request("POST", endpoint, payload)
    
    async def deep_research(
        self, 
        query: str, 
        max_urls: int = 10,
        max_depth: int = 3,
        time_limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Conduct deep research on a query using web crawling and AI analysis.
        
        Args:
            query: The query to research
            max_urls: Maximum number of URLs to analyze
            max_depth: Maximum depth of research iterations
            time_limit: Time limit in seconds
            
        Returns:
            Deep research results
        """
        endpoint = f"{self.base_url}/deep-research"
        
        payload = {
            "query": query,
            "maxUrls": max_urls,
            "maxDepth": max_depth
        }
        
        if time_limit:
            payload["timeLimit"] = time_limit
        
        return await self._make_request("POST", endpoint, payload)
    
    async def extract_structured_data(
        self,
        urls: List[str],
        schema: Dict[str, Any],
        prompt: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract structured information from web pages using LLM.
        
        Args:
            urls: List of URLs to extract information from
            schema: JSON schema for structured data extraction
            prompt: Prompt for the LLM extraction
            system_prompt: System prompt for LLM extraction
            
        Returns:
            Structured data extracted from pages
        """
        endpoint = f"{self.base_url}/extract"
        
        payload = {
            "urls": urls,
            "schema": schema
        }
        
        if prompt:
            payload["prompt"] = prompt
            
        if system_prompt:
            payload["systemPrompt"] = system_prompt
        
        return await self._make_request("POST", endpoint, payload)
    
    async def generate_llms_txt(
        self,
        url: str,
        max_urls: int = 10,
        show_full_text: bool = False
    ) -> Dict[str, Any]:
        """Generate standardized LLMs.txt file for a website.
        
        Args:
            url: The URL to generate LLMs.txt from
            max_urls: Maximum number of URLs to process
            show_full_text: Whether to show the full LLMs-full.txt
            
        Returns:
            Generated LLMs.txt content
        """
        endpoint = f"{self.base_url}/generate-llmstxt"
        
        payload = {
            "url": url,
            "maxUrls": max_urls,
            "showFullText": show_full_text
        }
        
        return await self._make_request("POST", endpoint, payload)
    
    async def _make_request(self, method: str, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make a request to the Firecrawl API.
        
        Args:
            method: HTTP method (GET, POST)
            endpoint: API endpoint
            payload: Request payload
            
        Returns:
            API response
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                if method.upper() == "GET":
                    async with session.get(
                        endpoint,
                        params=payload,
                        headers=headers,
                        timeout=self.timeout
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            raise ValueError(f"API request failed with status {response.status}: {error_text}")
                            
                        return await response.json()
                else:  # POST
                    async with session.post(
                        endpoint,
                        json=payload,
                        headers=headers,
                        timeout=self.timeout
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            raise ValueError(f"API request failed with status {response.status}: {error_text}")
                            
                        return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"Error making request to Firecrawl API: {str(e)}")
            raise
