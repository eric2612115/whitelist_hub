"""Data extraction components for Crawler Agent."""

import re
from typing import Dict, List, Any, Optional, Set
import logging

from ...utils.blockchain_client import BlockchainClient

logger = logging.getLogger(__name__)


class ContractExtractor:
    """Component for extracting contract addresses and information."""
    
    def __init__(self, blockchain_client: BlockchainClient):
        """Initialize contract extractor.
        
        Args:
            blockchain_client: Client for blockchain interactions
        """
        self.blockchain_client = blockchain_client
    
    def extract_addresses(self, content: str, blockchain: Optional[str] = None) -> List[Dict[str, str]]:
        """Extract contract addresses from content.
        
        Args:
            content: Content to extract from
            blockchain: Blockchain name to filter addresses
            
        Returns:
            List of found contract addresses with context
        """
        found_addresses = []
        
        # Ethereum address pattern
        eth_pattern = r'0x[a-fA-F0-9]{40}'
        
        # Find all Ethereum addresses
        addresses = re.findall(eth_pattern, content)
        
        # Deduplicate addresses
        unique_addresses = set(addresses)
        
        for address in unique_addresses:
            # Find context around the address
            context_pattern = r'(.{0,100}' + re.escape(address) + r'.{0,100})'
            context_matches = re.findall(context_pattern, content, re.DOTALL)
            
            context = context_matches[0] if context_matches else ""
            
            # Try to determine blockchain from context
            detected_blockchain = self._detect_blockchain(context)
            
            # If specific blockchain requested, filter by it
            if blockchain and detected_blockchain and blockchain.lower() != detected_blockchain.lower():
                continue
            
            found_addresses.append({
                "address": address,
                "blockchain": detected_blockchain or blockchain or "ethereum",
                "context": context.strip()
            })
        
        return found_addresses
    
    def _detect_blockchain(self, context: str) -> Optional[str]:
        """Detect blockchain from context.
        
        Args:
            context: Context string around an address
            
        Returns:
            Detected blockchain name or None
        """
        # Chain keywords
        chain_keywords = {
            "ethereum": ["ethereum", "mainnet", "eth"],
            "bsc": ["binance", "bsc", "bnb chain"],
            "polygon": ["polygon", "matic"],
            "arbitrum": ["arbitrum"],
            "optimism": ["optimism"],
            "avalanche": ["avalanche", "avax"]
        }
        
        context_lower = context.lower()
        
        for chain, keywords in chain_keywords.items():
            if any(keyword in context_lower for keyword in keywords):
                return chain
        
        return None
    
    def extract_contract_name(self, context: str) -> Optional[str]:
        """Extract contract name from context.
        
        Args:
            context: Context string around an address
            
        Returns:
            Contract name if found, None otherwise
        """
        # Patterns for contract names
        patterns = [
            r'contract\s+([A-Za-z0-9_]+)',
            r'([A-Za-z0-9_]+)\s+contract',
            r'([A-Za-z0-9_]+)\s+Contract',
            r'([A-Za-z0-9_]+)\.sol'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, context)
            if matches:
                return matches[0]
        
        return None
    
    def extract_deployment_data(self, content: str) -> Dict[str, Any]:
        """Extract contract deployment data from content.
        
        Args:
            content: Content to extract from
            
        Returns:
            Extracted deployment data
        """
        # Define patterns for contract deployments
        deploy_patterns = [
            (r'deployed to[: ]+(0x[a-fA-F0-9]{40})', "deployed"),
            (r'contract address[: ]+(0x[a-fA-F0-9]{40})', "address"),
            (r'contract[: ]+(0x[a-fA-F0-9]{40})', "contract"),
            (r'address[: ]+(0x[a-fA-F0-9]{40})', "general")
        ]
        
        deployments = []
        
        # Apply each pattern
        for pattern, pattern_type in deploy_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for address in matches:
                # Find context around the address
                context_pattern = r'(.{0,100}' + re.escape(address) + r'.{0,100})'
                context_matches = re.findall(context_pattern, content, re.DOTALL)
                
                context = context_matches[0] if context_matches else ""
                
                # Try to determine blockchain and contract name
                blockchain = self._detect_blockchain(context) or "ethereum"
                contract_name = self.extract_contract_name(context)
                
                deployments.append({
                    "address": address,
                    "blockchain": blockchain,
                    "contract_name": contract_name,
                    "context": context.strip(),
                    "pattern_type": pattern_type
                })
        
        return {
            "deployments": deployments,
            "count": len(deployments)
        }
    
    async def verify_contract(self, address: str, blockchain: str) -> Dict[str, Any]:
        """Verify if address is a valid contract.
        
        Args:
            address: Contract address
            blockchain: Blockchain name
            
        Returns:
            Verification result
        """
        try:
            # Check if address has code
            bytecode = await self.blockchain_client.fetch_contract_bytecode(address, blockchain)
            
            if bytecode and bytecode != "0x":
                # Try to fetch ABI if verified
                abi = await self.blockchain_client.fetch_contract_abi(address, blockchain)
                
                return {
                    "success": True,
                    "is_contract": True,
                    "has_verified_source": bool(abi),
                    "bytecode_length": len(bytecode) // 2,  # Convert hex length to bytes
                    "abi": abi if abi else None
                }
            else:
                return {
                    "success": True,
                    "is_contract": False,
                    "message": "Address does not contain code"
                }
            
        except Exception as e:
            logger.error(f"Error verifying contract address: {e}")
            return {
                "success": False,
                "message": str(e)
            }


class WhitelistExtractor:
    """Component for extracting whitelist-related information."""
    
    def extract(self, content: str) -> Dict[str, Any]:
        """Extract whitelist-related data from content.
        
        Args:
            content: Content to extract from
            
        Returns:
            Extracted whitelist data
        """
        # Whitelist-related keywords
        whitelist_keywords = [
            "whitelist", "allowlist", "white list", "allow list",
            "presale", "pre-sale", "private sale"
        ]
        
        # Time-related keywords
        time_keywords = [
            "opens", "closes", "deadline", "date", "time", "schedule",
            "registration", "starts", "ends"
        ]
        
        # Extract whitelist paragraphs
        whitelist_paragraphs = []
        paragraphs = re.split(r'\n\s*\n', content)
        
        for paragraph in paragraphs:
            if any(keyword in paragraph.lower() for keyword in whitelist_keywords):
                whitelist_paragraphs.append(paragraph.strip())
        
        # Extract dates
        date_pattern = r'(\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)|(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?)\s+\d{4}'
        dates = []
        
        for paragraph in whitelist_paragraphs:
            dates.extend(re.findall(date_pattern, paragraph, re.IGNORECASE))
        
        # Try to find time information
        times = []
        time_pattern = r'\d{1,2}:\d{2}\s*(?:AM|PM|UTC|GMT|EST|EDT)?'
        
        for paragraph in whitelist_paragraphs:
            times.extend(re.findall(time_pattern, paragraph, re.IGNORECASE))
        
        # Look for requirements
        requirements = []
        req_keywords = ["require", "requirement", "criteria", "eligible", "eligibility"]
        
        for paragraph in whitelist_paragraphs:
            if any(keyword in paragraph.lower() for keyword in req_keywords):
                # Extract sentences with requirements
                sentences = re.split(r'[.!?]+', paragraph)
                for sentence in sentences:
                    if any(keyword in sentence.lower() for keyword in req_keywords):
                        requirements.append(sentence.strip())
        
        return {
            "whitelist_paragraphs": whitelist_paragraphs,
            "dates": dates,
            "times": times,
            "requirements": requirements,
            "time_limited": bool(dates or times)
        }
    
    def extract_tiers(self, content: str) -> List[Dict[str, Any]]:
        """Extract tiered whitelist information from content.
        
        Args:
            content: Content to extract from
            
        Returns:
            List of extracted tiers
        """
        tiers = []
        
        # Tier-related keywords
        tier_keywords = [
            "tier", "level", "phase", "round", "group"
        ]
        
        # Look for tier mentions in paragraphs
        paragraphs = re.split(r'\n\s*\n', content)
        
        tier_pattern = r'(?:tier|level|phase|round|group)\s*(?:[:#-]|\s+)\s*(\d+|[a-zA-Z]+)'
        
        for paragraph in paragraphs:
            paragraph_lower = paragraph.lower()
            
            if any(keyword in paragraph_lower for keyword in tier_keywords):
                # Try to extract tier names
                tier_matches = re.findall(tier_pattern, paragraph_lower, re.IGNORECASE)
                
                for tier_name in tier_matches:
                    # Extract surrounding context for this tier
                    context_pattern = r'(.{0,200}' + re.escape(tier_name) + r'.{0,200})'
                    context_matches = re.findall(context_pattern, paragraph, re.DOTALL | re.IGNORECASE)
                    
                    context = context_matches[0] if context_matches else paragraph
                    
                    # Extract requirements and benefits for this tier
                    requirements = self._extract_tier_requirements(context)
                    benefits = self._extract_tier_benefits(context)
                    
                    tiers.append({
                        "tier_name": tier_name,
                        "context": context.strip(),
                        "requirements": requirements,
                        "benefits": benefits
                    })
        
        return tiers
    
    def _extract_tier_requirements(self, context: str) -> List[str]:
        """Extract requirements for a tier from context.
        
        Args:
            context: Context around a tier mention
            
        Returns:
            List of requirements
        """
        requirement_keywords = [
            "require", "requirement", "need", "must", "minimum", "at least"
        ]
        
        requirements = []
        sentences = re.split(r'[.!?]+', context)
        
        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in requirement_keywords):
                requirements.append(sentence.strip())
        
        return requirements
    
    def _extract_tier_benefits(self, context: str) -> List[str]:
        """Extract benefits for a tier from context.
        
        Args:
            context: Context around a tier mention
            
        Returns:
            List of benefits
        """
        benefit_keywords = [
            "benefit", "receive", "get", "eligible for", "allocation", "max"
        ]
        
        benefits = []
        sentences = re.split(r'[.!?]+', context)
        
        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in benefit_keywords):
                benefits.append(sentence.strip())
        
        return benefits


class ProjectDetailsExtractor:
    """Component for extracting project details."""
    
    def extract(self, content: str) -> Dict[str, Any]:
        """Extract project details from content.
        
        Args:
            content: Content to extract from
            
        Returns:
            Extracted project details
        """
        # Define patterns for project details
        title_pattern = r'<h1[^>]*>(.*?)</h1>'
        description_pattern = r'<meta\s+name="description"\s+content="([^"]+)"'
        
        # Extract title
        title_matches = re.findall(title_pattern, content, re.IGNORECASE)
        title = title_matches[0] if title_matches else None
        
        if title:
            # Clean HTML tags
            title = re.sub(r'<[^>]+>', '', title).strip()
        
        # Extract description
        description_matches = re.findall(description_pattern, content, re.IGNORECASE)
        description = description_matches[0] if description_matches else None
        
        # Try to find categories
        category_keywords = {
            "defi": ["defi", "decentralized finance", "yield", "staking", "lending", "borrowing"],
            "nft": ["nft", "non-fungible", "collectible"],
            "dao": ["dao", "governance", "voting"],
            "exchange": ["exchange", "dex", "swap", "amm"],
            "lending": ["lending", "borrow", "loan"],
            "derivatives": ["derivative", "option", "future", "synthetic"],
            "gaming": ["game", "gaming", "metaverse"]
        }
        
        categories = []
        content_lower = content.lower()
        
        for category, keywords in category_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                categories.append(category)
        
        return {
            "title": title,
            "description": description,
            "categories": categories
        }
    
    def extract_links(self, html_content: str, base_url: str) -> List[Dict[str, str]]:
        """Extract links from HTML content.
        
        Args:
            html_content: HTML content
            base_url: Base URL for resolving relative links
            
        Returns:
            List of links with URL and text
        """
        links = []
        
        # Simple regex for a elements
        # In a real implementation, this would use a proper HTML parser
        pattern = r'<a\s+(?:[^>]*?\s+)?href="([^"]*)"[^>]*>(.*?)</a>'
        matches = re.findall(pattern, html_content, re.IGNORECASE)
        
        for href, text in matches:
            # Skip empty or javascript links
            if not href or href.startswith("javascript:") or href == "#":
                continue
            
            # Resolve relative URLs
            if not href.startswith("http"):
                if href.startswith("/"):
                    # Absolute path
                    base_parts = base_url.split("/", 3)
                    if len(base_parts) >= 3:
                        href = f"{base_parts[0]}//{base_parts[2]}{href}"
                else:
                    # Relative path
                    href = f"{base_url.rstrip('/')}/{href}"
            
            # Extract text content (remove HTML tags)
            text = re.sub(r"<[^>]+>", "", text).strip()
            
            links.append({
                "url": href,
                "text": text
            })
        
        return links
    
    def find_documentation_links(self, links: List[Dict[str, str]], base_url: str) -> List[Dict[str, str]]:
        """Find documentation links in a list of links.
        
        Args:
            links: List of links
            base_url: Base URL
            
        Returns:
            List of documentation links
        """
        doc_links = []
        
        # Keywords for documentation links
        doc_keywords = ["docs", "documentation", "whitepaper", "paper", "gitbook", "wiki"]
        
        for link in links:
            url = link.get("url", "")
            text = link.get("text", "").lower()
            
            # Check if URL contains doc keywords
            if any(keyword in url.lower() for keyword in doc_keywords):
                doc_links.append(link)
                continue
            
            # Check if text contains doc keywords
            if any(keyword in text for keyword in doc_keywords):
                doc_links.append(link)
                continue
        
        # If no explicit doc links, try common patterns
        if not doc_links:
            common_doc_paths = ["docs", "documentation", "whitepaper", "paper", "about"]
            
            for path in common_doc_paths:
                doc_url = f"{base_url.rstrip('/')}/{path}"
                doc_links.append({
                    "url": doc_url,
                    "text": f"Possible documentation at {path}",
                    "confidence": "low"
                })
        
        return doc_links
    
    def find_blog_link(self, links: List[Dict[str, str]], base_url: str) -> Optional[Dict[str, str]]:
        """Find blog or announcements link.
        
        Args:
            links: List of links
            base_url: Base URL
            
        Returns:
            Blog link if found, None otherwise
        """
        # Keywords for blog links
        blog_keywords = ["blog", "news", "announcements", "updates"]
        
        for link in links:
            url = link.get("url", "")
            text = link.get("text", "").lower()
            
            # Check if URL contains blog keywords
            if any(keyword in url.lower() for keyword in blog_keywords):
                return link
            
            # Check if text contains blog keywords
            if any(keyword in text for keyword in blog_keywords):
                return link
        
        # Try common patterns
        for keyword in blog_keywords:
            blog_url = f"{base_url.rstrip('/')}/{keyword}"
            
            # Check if this URL is in the links list
            if any(link.get("url") == blog_url for link in links):
                return next(link for link in links if link.get("url") == blog_url)
        
        # No blog found
        return None
