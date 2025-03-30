"""
Web crawler agent implementation.

This module provides the crawler agent, which is responsible for
gathering information from websites, GitHub repositories, and blockchain explorers.
"""

import logging
import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

from ..agent import AgentConfig, AgentRole
from ..registry import register_agent
from ..context import Context
from .llm_agent import LLMAgent, LLMAgentConfig

logger = logging.getLogger(__name__)


@register_agent("crawler")
class CrawlerAgent(LLMAgent):
    """Agent responsible for gathering information from external sources.
    
    The crawler agent retrieves information from websites, GitHub repositories,
    blockchain explorers, and other external sources to support project analysis.
    """
    
    @classmethod
    def get_default_config(cls) -> LLMAgentConfig:
        """Get the default configuration for the crawler agent.
        
        Returns:
            The default configuration
        """
        return LLMAgentConfig(
            name="Crawler",
            description="Web crawler agent for gathering blockchain project information",
            role=AgentRole.CRAWLER,
            model_name="gemini-2.0-pro-001",
            temperature=0.2,
            system_prompt="""You are an expert blockchain crawler agent responsible for gathering information about blockchain projects and smart contracts from various sources. Your role is to:

1. Extract relevant information from project websites
2. Analyze GitHub repositories to identify important smart contracts
3. Find and validate contract addresses associated with blockchain projects
4. Gather documentation and specifications for protocols and their whitelist mechanisms

You should focus on:
- Identifying the main smart contracts of a project
- Finding whitelist-related functionality
- Locating official documentation about access control mechanisms
- Discovering verified contract addresses on different blockchains
- Extracting relevant technical details about the project's architecture

When analyzing websites:
- Extract key project information (purpose, features, architecture)
- Identify any whitelist-related documentation or guides
- Find links to official resources (GitHub, docs, block explorers)

When analyzing GitHub repositories:
- Identify the main contract files containing whitelist functionality
- Understand the overall project structure
- Extract relevant code snippets for deeper analysis
- Look for configuration files or deployment scripts that may contain contract addresses

When discovering contract addresses:
- Validate addresses across multiple sources
- Determine which blockchain(s) the contracts are deployed on
- Check for verified contract code on block explorers
- Note any proxy patterns or contract upgradability features

You have access to specialized tools for web crawling and blockchain data retrieval.
""",
            tools=[
                "crawl_website",
                "crawl_github",
                "search_contracts"
            ],
            include_thinking_in_response=True,
            thinking_format="markdown"
        )
    
    async def _generate_thinking(self, context: Context) -> str:
        """Generate thinking steps before producing the final response.
        
        For the crawler, we want to see the exploration strategy and
        information gathering approach.
        
        Args:
            context: The execution context
            
        Returns:
            The thinking steps as a string
        """
        # Create task-specific system prompt
        task = context.inputs.get("task", "unknown")
        
        if task == "crawl_website" or "website" in context.inputs:
            website = context.inputs.get("website", "No website provided")
            project_name = context.inputs.get("project_name", "Unknown project")
            
            return f"""Thinking process for crawling {project_name} website ({website}):

1. First, I'll analyze the main website to understand the project overview
2. I'll look for specific sections related to:
   - Technical documentation
   - Whitelist/access control features
   - Smart contract information
   - Deployed addresses and blockchain integrations
3. I'll identify key pages that might contain relevant information
4. I'll extract the most important details while filtering out marketing content
5. I'll organize information into categories for further analysis
"""
        
        elif task == "crawl_github" or "github_url" in context.inputs:
            github_url = context.inputs.get("github_url", "No GitHub URL provided")
            project_name = context.inputs.get("project_name", "Unknown project")
            
            return f"""Thinking process for analyzing {project_name} GitHub repository ({github_url}):

1. First, I'll identify the main repositories and their structure
2. I'll focus on finding smart contract code files (Solidity, Vyper, etc.)
3. I'll look for files specifically related to:
   - Whitelist implementations
   - Access control mechanisms
   - User role management
   - Contract deployment
4. I'll examine README files, documentation, and contribution guidelines
5. For relevant contracts, I'll analyze their structure and key functions
6. I'll note any contract addresses found in deployment scripts or config files
"""
        
        elif task == "discover_contracts" or "discover_contracts" in context.inputs:
            project_name = context.inputs.get("project_name", "Unknown project")
            
            return f"""Thinking process for discovering contract addresses for {project_name}:

1. I'll gather potential contract addresses from all available sources:
   - Website information
   - GitHub repository data
   - Block explorer searches
   - Documentation references
2. For each potential address, I'll verify:
   - Which blockchain it's deployed on
   - If the code is verified on block explorers
   - If it matches the expected functionality
   - When it was deployed and by whom
3. I'll organize contracts by category and function
4. I'll identify the main contracts vs auxiliary/supporting contracts
5. I'll determine which contracts contain whitelist functionality
"""
        
        # Generic thinking prompt if no specific task matched
        return f"""Thinking process for information gathering:

1. Understand the specific requirements and context
2. Identify the most reliable sources of information
3. Extract relevant details while filtering out noise
4. Organize and structure the gathered information
5. Validate data across multiple sources when possible
6. Prepare a comprehensive summary of findings
"""
    
    async def _process_response(self, response: str, context: Context) -> str:
        """Process the response from the AI model.
        
        For the crawler, we want to extract structured data from the
        response, such as website analysis results or contract addresses.
        
        Args:
            response: The response from the AI model
            context: The execution context
            
        Returns:
            The processed response
        """
        # Extract and execute any function calls
        response = await self._extract_and_execute_function_calls(response, context)
        
        # Determine the task type
        task = context.inputs.get("task", "unknown")
        
        # Extract structured data based on task type
        if task == "crawl_website" or "website" in context.inputs:
            if "website_data" not in context.outputs:
                # Extract website analysis into structured output
                try:
                    # Look for JSON blocks or structured content
                    import re
                    json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
                    
                    if json_match:
                        try:
                            website_data = json.loads(json_match.group(1))
                            context.outputs["website_data"] = website_data
                        except json.JSONDecodeError:
                            # Try to create structured data from text
                            context.outputs["website_data"] = {
                                "description": self._extract_description(response),
                                "potential_contracts": self._extract_contract_addresses(response),
                                "content": response
                            }
                    else:
                        # Create structured data from text
                        context.outputs["website_data"] = {
                            "description": self._extract_description(response),
                            "potential_contracts": self._extract_contract_addresses(response),
                            "content": response
                        }
                except Exception as e:
                    logger.warning(f"Error extracting website data: {str(e)}")
        
        elif task == "crawl_github" or "github_url" in context.inputs:
            if "github_data" not in context.outputs:
                # Extract GitHub analysis into structured output
                try:
                    # Look for JSON blocks or structured content
                    import re
                    json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
                    
                    if json_match:
                        try:
                            github_data = json.loads(json_match.group(1))
                            context.outputs["github_data"] = github_data
                        except json.JSONDecodeError:
                            # Create structured data from text
                            context.outputs["github_data"] = {
                                "repositories": self._extract_repositories(response),
                                "potential_contracts": self._extract_contract_files(response),
                                "content": response
                            }
                    else:
                        # Create structured data from text
                        context.outputs["github_data"] = {
                            "repositories": self._extract_repositories(response),
                            "potential_contracts": self._extract_contract_files(response),
                            "content": response
                        }
                except Exception as e:
                    logger.warning(f"Error extracting GitHub data: {str(e)}")
        
        elif task == "discover_contracts" or "discover_contracts" in context.inputs:
            if "contracts" not in context.outputs:
                # Extract contract addresses into structured output
                try:
                    # Look for JSON blocks or structured content
                    import re
                    json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
                    
                    if json_match:
                        try:
                            contracts = json.loads(json_match.group(1))
                            context.outputs["contracts"] = contracts
                        except json.JSONDecodeError:
                            # Create structured data from text
                            context.outputs["contracts"] = {
                                "addresses": self._extract_contract_addresses(response),
                                "content": response
                            }
                    else:
                        # Create structured data from text
                        context.outputs["contracts"] = {
                            "addresses": self._extract_contract_addresses(response),
                            "content": response
                        }
                except Exception as e:
                    logger.warning(f"Error extracting contract data: {str(e)}")
        
        return response
    
    def _extract_description(self, text: str) -> str:
        """Extract a project description from text.
        
        Args:
            text: The text to extract from
            
        Returns:
            The extracted description
        """
        # Look for description or summary sections
        patterns = [
            r"(?:Project|Protocol) Description:(.*?)(?:\n\n|\n#|\Z)",
            r"(?:Project|Protocol) Summary:(.*?)(?:\n\n|\n#|\Z)",
            r"(?:Project|Protocol) Overview:(.*?)(?:\n\n|\n#|\Z)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                description = match.group(1).strip()
                # Limit to a reasonable length
                if len(description) > 300:
                    description = description[:300] + "..."
                return description
        
        # If no specific section found, use the first paragraph
        paragraphs = text.split("\n\n")
        if paragraphs:
            first_para = paragraphs[0].strip()
            if len(first_para) > 300:
                first_para = first_para[:300] + "..."
            return first_para
        
        return "No description available"
    
    def _extract_contract_addresses(self, text: str) -> List[Dict[str, str]]:
        """Extract contract addresses from text.
        
        Args:
            text: The text to extract from
            
        Returns:
            List of contract address dictionaries
        """
        # Look for Ethereum-style addresses
        address_pattern = r'0x[a-fA-F0-9]{40}'
        addresses = re.findall(address_pattern, text)
        
        # Look for blockchain/type information near addresses
        result = []
        for address in addresses:
            # Look for context around the address
            context_pattern = r'(?i)(?:[\w\s]+?blockchain|ethereum|polygon|bsc|avalanche|fantom|arbitrum|optimism)[\s\w:]*(' + address + ')'
            blockchain = "ethereum"  # Default
            
            context_match = re.search(context_pattern, text)
            if context_match:
                context = context_match.group(0).lower()
                if "polygon" in context:
                    blockchain = "polygon"
                elif "bsc" in context or "binance" in context:
                    blockchain = "bsc"
                elif "avalanche" in context:
                    blockchain = "avalanche"
                elif "fantom" in context:
                    blockchain = "fantom"
                elif "arbitrum" in context:
                    blockchain = "arbitrum"
                elif "optimism" in context:
                    blockchain = "optimism"
            
            result.append({
                "address": address,
                "blockchain": blockchain
            })
        
        return result
    
    def _extract_repositories(self, text: str) -> List[Dict[str, str]]:
        """Extract GitHub repositories from text.
        
        Args:
            text: The text to extract from
            
        Returns:
            List of repository dictionaries
        """
        # Look for GitHub repository URLs
        repo_pattern = r'https://github\.com/[\w\-\.]+/[\w\-\.]+'
        repos = re.findall(repo_pattern, text)
        
        result = []
        for repo in repos:
            # Try to find description near the URL
            desc_pattern = r'(?:' + re.escape(repo) + r')\s*[:\-]?\s*([^#\n]+)'
            desc_match = re.search(desc_pattern, text)
            description = desc_match.group(1).strip() if desc_match else "No description available"
            
            result.append({
                "url": repo,
                "description": description
            })
        
        return result
    
    def _extract_contract_files(self, text: str) -> List[Dict[str, str]]:
        """Extract contract file information from text.
        
        Args:
            text: The text to extract from
            
        Returns:
            List of contract file dictionaries
        """
        # Look for Solidity/Vyper file paths
        file_patterns = [
            r'(?:[\w\-\.\/]+\.sol)(?:\b|$)',
            r'(?:[\w\-\.\/]+\.vy)(?:\b|$)',
            r'(?:contracts/[\w\-\.\/]+)(?:\b|$)'
        ]
        
        result = []
        for pattern in file_patterns:
            files = re.findall(pattern, text)
            for file in files:
                # Try to find description near the filename
                desc_pattern = r'(?:' + re.escape(file) + r')\s*[:\-]?\s*([^#\n]+)'
                desc_match = re.search(desc_pattern, text)
                description = desc_match.group(1).strip() if desc_match else ""
                
                result.append({
                    "file": file,
                    "description": description
                })
        
        return result
