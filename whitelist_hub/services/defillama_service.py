"""Service for interacting with DeFiLlama API."""

import logging
from typing import Dict, List, Any, Optional
import aiohttp

logger = logging.getLogger(__name__)


class DefiLlamaService:
    """Service for fetching data from DeFiLlama."""
    
    BASE_URL = "https://api.llama.fi"
    
    async def get_all_protocols(self) -> List[Dict[str, Any]]:
        """Fetch all protocols from DeFiLlama.
        
        Returns:
            List of all protocols
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.BASE_URL}/protocols") as response:
                    if response.status != 200:
                        logger.error(f"Failed to fetch protocols: {response.status}")
                        return []
                    
                    return await response.json()
        except Exception as e:
            logger.error(f"Error fetching protocols: {e}")
            return []
    
    async def search_projects(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for projects by name.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching projects
        """
        protocols = await self.get_all_protocols()
        
        query_lower = query.lower()
        exact_matches = []
        partial_matches = []
        
        for protocol in protocols:
            name = protocol.get("name", "").lower()
            
            if name == query_lower:
                exact_matches.append(protocol)
            elif query_lower in name:
                partial_matches.append(protocol)
        
        # Prioritize exact matches
        results = exact_matches + partial_matches
        
        # Limit results
        return results[:limit]
    
    async def get_project_details(self, slug: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a project.
        
        Args:
            slug: Project slug
            
        Returns:
            Project details
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.BASE_URL}/protocol/{slug}") as response:
                    if response.status != 200:
                        logger.error(f"Failed to fetch project details: {response.status}")
                        return None
                    
                    return await response.json()
        except Exception as e:
            logger.error(f"Error fetching project details: {e}")
            return None
    
    async def get_project_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get project details by name.
        
        Args:
            name: Project name
            
        Returns:
            Project details
        """
        # Search for the project
        search_results = await self.search_projects(name, limit=1)
        
        if not search_results:
            return None
        
        # Get detailed information
        project = search_results[0]
        slug = project.get("slug")
        
        if not slug:
            return None
        
        return await self.get_project_details(slug)
    
    async def get_tvl_data(self, slug: str) -> Optional[Dict[str, Any]]:
        """Get TVL (Total Value Locked) data for a project.
        
        Args:
            slug: Project slug
            
        Returns:
            TVL data
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.BASE_URL}/tvl/{slug}") as response:
                    if response.status != 200:
                        logger.error(f"Failed to fetch TVL data: {response.status}")
                        return None
                    
                    return await response.json()
        except Exception as e:
            logger.error(f"Error fetching TVL data: {e}")
            return None
    
    async def get_chain_tvl(self, chain: str) -> Optional[Dict[str, Any]]:
        """Get TVL data for a specific blockchain.
        
        Args:
            chain: Blockchain name
            
        Returns:
            Chain TVL data
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.BASE_URL}/chain/{chain}") as response:
                    if response.status != 200:
                        logger.error(f"Failed to fetch chain TVL: {response.status}")
                        return None
                    
                    return await response.json()
        except Exception as e:
            logger.error(f"Error fetching chain TVL: {e}")
            return None
    
    def extract_contract_addresses(self, project_details: Dict[str, Any]) -> Dict[str, List[str]]:
        """Extract contract addresses from project details.
        
        Args:
            project_details: Project details from DeFiLlama
            
        Returns:
            Contract addresses by chain
        """
        addresses = {}
        
        # Extract addresses from tokens
        tokens = project_details.get("tokens", [])
        for token in tokens:
            chain = token.get("chain")
            address = token.get("address")
            
            if chain and address:
                if chain not in addresses:
                    addresses[chain] = []
                
                addresses[chain].append(address)
        
        # Extract addresses from pools
        pools = project_details.get("pools", [])
        for pool in pools:
            chain = pool.get("chain")
            address = pool.get("address")
            
            if chain and address:
                if chain not in addresses:
                    addresses[chain] = []
                
                addresses[chain].append(address)
        
        return addresses
