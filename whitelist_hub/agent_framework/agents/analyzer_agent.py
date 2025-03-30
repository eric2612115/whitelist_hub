"""
Analyzer agent implementation.

This module provides the analyzer agent, which is responsible for
analyzing smart contracts and identifying whitelist mechanisms.
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


@register_agent("analyzer")
class AnalyzerAgent(LLMAgent):
    """Agent responsible for analyzing contracts and their functionality.
    
    The analyzer agent examines smart contract code, identifies whitelist
    mechanisms, and evaluates security considerations.
    """
    
    @classmethod
    def get_default_config(cls) -> LLMAgentConfig:
        """Get the default configuration for the analyzer agent.
        
        Returns:
            The default configuration
        """
        return LLMAgentConfig(
            name="Analyzer",
            description="Smart contract analyzer agent for examining contract code and identifying whitelist mechanisms",
            role=AgentRole.ANALYZER,
            model_name="gemini-2.0-pro-001",  # Gemini is particularly good at code analysis
            temperature=0.1,
            system_prompt="""You are an expert blockchain analyzer agent specializing in smart contract analysis, particularly focused on identifying and understanding whitelist mechanisms. Your role is to:

1. Analyze smart contract code to identify whitelist and access control mechanisms
2. Categorize and explain different types of whitelist implementations
3. Evaluate the security implications of different whitelist approaches
4. Detect proxy patterns and contract upgradeability
5. Provide detailed technical insights into contract functionality

When analyzing smart contracts:
- Focus on functions related to access control, whitelisting, and permissioning
- Identify common patterns like allowlists, mappings of addresses to booleans, role-based access control
- Detect different whitelist types (direct mapping, Merkle tree-based, role-based, tiered, etc.)
- Understand the broader contract architecture and how whitelist components interact
- Consider gas efficiency and security implications of different implementations

When identifying whitelist mechanisms, look for:
- Mappings storing address => bool or address => uint (access flags)
- Modifiers like "onlyWhitelisted" or similar
- Functions for adding/removing addresses from whitelists
- Merkle tree verification for efficient whitelisting
- Role-based systems (like OpenZeppelin's AccessControl)
- ERC standards related to permissioning

Your analysis should be thorough, technically precise, and focus on how the contract handles access control and whitelisting.
""",
            tools=[
                "analyze_contract",
                "identify_whitelist_mechanism",
                "evaluate_security"
            ],
            include_thinking_in_response=True,
            thinking_format="markdown"
        )
    
    async def _generate_thinking(self, context: Context) -> str:
        """Generate thinking steps for the analyzer agent.
        
        For the analyzer, we want to see the code examination process
        and whitelist mechanism identification approach.
        
        Args:
            context: The execution context
            
        Returns:
            The thinking steps as a string
        """
        # Create task-specific thinking prompt
        task = context.inputs.get("task", "unknown")
        
        if task == "analyze_contracts" or "contracts" in context.inputs:
            return """Thinking process for analyzing smart contracts:

1. First, I'll examine the contract's overall structure and inheritance
2. I'll identify key components:
   - State variables (especially mappings and access flags)
   - Modifiers related to access control
   - Functions for whitelist management
   - Events related to whitelist changes
3. I'll look for specific whitelist patterns:
   - Direct mappings (address => bool)
   - Role-based access control
   - Merkle tree verification
   - Tiered access systems
4. I'll analyze how the whitelist integrates with core contract functionality
5. I'll check for proxy patterns and contract upgradeability
6. I'll evaluate gas efficiency and potential optimizations
7. I'll identify any security concerns in the implementation
"""
        
        elif task == "identify_whitelist" or "whitelist_mechanisms" in context.inputs:
            return """Thinking process for identifying whitelist mechanisms:

1. I'll categorize the whitelist implementations I've found:
   - By type (direct mapping, Merkle, role-based, etc.)
   - By functionality (who can modify, how addresses are added/removed)
   - By security level (centralized vs. decentralized control)
2. For each mechanism, I'll analyze:
   - How addresses are added and removed
   - Who has authority to modify the whitelist
   - How whitelist checks are performed
   - What functions or actions are gated by the whitelist
3. I'll compare implementations across contracts to identify patterns
4. I'll evaluate the pros and cons of each approach
5. I'll note any innovative or unusual whitelist techniques
"""
        
        elif task == "security_assessment" or "security" in context.inputs:
            return """Thinking process for security assessment of whitelist mechanisms:

1. I'll evaluate potential vulnerabilities in each whitelist implementation:
   - Centralization risks (single admin control)
   - Front-running possibilities
   - Potential for griefing attacks
   - Gas optimization issues
   - Logical flaws in access control
2. I'll assess upgradeability risks if present
3. I'll check for proper event emission for whitelist changes
4. I'll evaluate the impact of whitelist failures on overall contract security
5. I'll compare against best practices for whitelist implementations
6. I'll rate the overall security posture of each mechanism
"""
        
        # Generic thinking for other tasks
        return """Thinking process for contract analysis:

1. Understand the specific requirements of this analysis task
2. Examine the available contract information systematically
3. Focus on identifying access control and whitelist patterns
4. Analyze code structure and interactions between components
5. Evaluate security implications and potential vulnerabilities
6. Organize findings into a clear and structured response
"""
    
    async def _process_response(self, response: str, context: Context) -> str:
        """Process the response from the AI model.
        
        For the analyzer, we want to extract structured data about
        contract analysis and whitelist mechanisms.
        
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
        if task == "analyze_contracts" or "contracts" in context.inputs:
            if "contracts_analysis" not in context.outputs:
                # Extract contract analysis into structured output
                try:
                    # Look for JSON blocks or structured content
                    import re
                    json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
                    
                    if json_match:
                        try:
                            contracts_analysis = json.loads(json_match.group(1))
                            context.outputs["contracts_analysis"] = contracts_analysis
                        except json.JSONDecodeError:
                            # Create structured data from text
                            context.outputs["contracts_analysis"] = {
                                "summary": self._extract_summary(response),
                                "functions": self._extract_functions(response),
                                "content": response
                            }
                    else:
                        # Create structured data from text
                        context.outputs["contracts_analysis"] = {
                            "summary": self._extract_summary(response),
                            "functions": self._extract_functions(response),
                            "content": response
                        }
                except Exception as e:
                    logger.warning(f"Error extracting contract analysis: {str(e)}")
        
        elif task == "identify_whitelist" or "whitelist_mechanisms" in context.inputs:
            if "whitelist_mechanisms" not in context.outputs:
                # Extract whitelist mechanisms into structured output
                try:
                    # Look for JSON blocks or structured content
                    import re
                    json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
                    
                    if json_match:
                        try:
                            whitelist_mechanisms = json.loads(json_match.group(1))
                            context.outputs["whitelist_mechanisms"] = whitelist_mechanisms
                        except json.JSONDecodeError:
                            # Create structured data from text
                            context.outputs["whitelist_mechanisms"] = {
                                "mechanisms": self._extract_whitelist_mechanisms(response),
                                "content": response
                            }
                    else:
                        # Create structured data from text
                        context.outputs["whitelist_mechanisms"] = {
                            "mechanisms": self._extract_whitelist_mechanisms(response),
                            "content": response
                        }
                except Exception as e:
                    logger.warning(f"Error extracting whitelist mechanisms: {str(e)}")
        
        elif task == "security_assessment" or "security" in context.inputs:
            if "security_assessment" not in context.outputs:
                # Extract security assessment into structured output
                try:
                    # Look for JSON blocks or structured content
                    import re
                    json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
                    
                    if json_match:
                        try:
                            security_assessment = json.loads(json_match.group(1))
                            context.outputs["security_assessment"] = security_assessment
                        except json.JSONDecodeError:
                            # Create structured data from text
                            context.outputs["security_assessment"] = {
                                "issues": self._extract_security_issues(response),
                                "risk_level": self._extract_risk_level(response),
                                "content": response
                            }
                    else:
                        # Create structured data from text
                        context.outputs["security_assessment"] = {
                            "issues": self._extract_security_issues(response),
                            "risk_level": self._extract_risk_level(response),
                            "content": response
                        }
                except Exception as e:
                    logger.warning(f"Error extracting security assessment: {str(e)}")
        
        return response
    
    def _extract_summary(self, text: str) -> str:
        """Extract a summary from the text.
        
        Args:
            text: The text to extract from
            
        Returns:
            The extracted summary
        """
        # Look for summary sections
        patterns = [
            r"(?:Contract|Analysis) Summary:(.*?)(?:\n\n|\n#|\Z)",
            r"Summary:(.*?)(?:\n\n|\n#|\Z)",
            r"Overview:(.*?)(?:\n\n|\n#|\Z)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                summary = match.group(1).strip()
                # Limit to a reasonable length
                if len(summary) > 500:
                    summary = summary[:500] + "..."
                return summary
        
        # If no specific section found, use the first paragraph
        paragraphs = text.split("\n\n")
        if paragraphs:
            first_para = paragraphs[0].strip()
            if len(first_para) > 500:
                first_para = first_para[:500] + "..."
            return first_para
        
        return "No summary available"
    
    def _extract_functions(self, text: str) -> List[Dict[str, str]]:
        """Extract function information from text.
        
        Args:
            text: The text to extract from
            
        Returns:
            List of function dictionaries
        """
        # Look for function descriptions
        function_pattern = r'(?:function|method)[\s:]+`?(\w+)`?[^\n]*(?:\n+)((?:(?!\n\n).)*)'
        functions = re.findall(function_pattern, text, re.DOTALL | re.IGNORECASE)
        
        result = []
        for name, description in functions:
            result.append({
                "name": name.strip(),
                "description": description.strip()
            })
        
        return result
    
    def _extract_whitelist_mechanisms(self, text: str) -> List[Dict[str, Any]]:
        """Extract whitelist mechanism information from text.
        
        Args:
            text: The text to extract from
            
        Returns:
            List of whitelist mechanism dictionaries
        """
        # Look for whitelist mechanism descriptions
        mechanism_pattern = r'(?:Whitelist|Access Control) (?:Mechanism|Type)[\s:]+`?([^`\n]+)`?[^\n]*(?:\n+)((?:(?!\n\n).)*)'
        mechanisms = re.findall(mechanism_pattern, text, re.DOTALL | re.IGNORECASE)
        
        result = []
        if mechanisms:
            for name, description in mechanisms:
                result.append({
                    "type": name.strip(),
                    "description": description.strip()
                })
        else:
            # Try to identify mechanisms from the overall text
            if re.search(r'direct\s+mapping|address\s*=>\s*bool', text, re.IGNORECASE):
                result.append({
                    "type": "direct_mapping",
                    "description": "Uses a direct mapping of addresses to boolean values."
                })
            
            if re.search(r'merkle\s+tree|merkle\s+proof', text, re.IGNORECASE):
                result.append({
                    "type": "merkle_tree",
                    "description": "Uses a Merkle tree for efficient whitelist verification."
                })
            
            if re.search(r'role[- ]based|rbac|access ?control', text, re.IGNORECASE):
                result.append({
                    "type": "role_based",
                    "description": "Uses a role-based access control system."
                })
            
            if re.search(r'tier(?:ed)?|level', text, re.IGNORECASE):
                result.append({
                    "type": "tiered",
                    "description": "Uses a tiered system with different access levels."
                })
        
        return result
    
    def _extract_security_issues(self, text: str) -> List[Dict[str, str]]:
        """Extract security issues from text.
        
        Args:
            text: The text to extract from
            
        Returns:
            List of security issue dictionaries
        """
        # Look for security issue descriptions
        issue_pattern = r'(?:Issue|Vulnerability|Security Concern)[\s:]+`?([^`\n]+)`?[^\n]*(?:\n+)((?:(?!\n\n).)*)'
        issues = re.findall(issue_pattern, text, re.DOTALL | re.IGNORECASE)
        
        result = []
        for name, description in issues:
            result.append({
                "name": name.strip(),
                "description": description.strip()
            })
        
        return result
    
    def _extract_risk_level(self, text: str) -> str:
        """Extract risk level from text.
        
        Args:
            text: The text to extract from
            
        Returns:
            The extracted risk level
        """
        # Look for risk level statements
        risk_pattern = r'(?:Risk Level|Security Level|Overall Risk)[\s:]+`?(\w+)`?'
        match = re.search(risk_pattern, text, re.IGNORECASE)
        
        if match:
            risk = match.group(1).lower()
            # Normalize risk levels
            if risk in ['critical', 'very high', 'severe']:
                return "critical"
            elif risk in ['high', 'elevated']:
                return "high"
            elif risk in ['medium', 'moderate', 'mid']:
                return "medium"
            elif risk in ['low', 'minor']:
                return "low"
            elif risk in ['minimal', 'very low', 'negligible']:
                return "minimal"
            else:
                return risk
        
        # If no explicit risk level found, try to infer from text
        if re.search(r'critical|\bsevere\b|extremely dangerous|urgent', text, re.IGNORECASE):
            return "critical"
        elif re.search(r'\bhigh\b|significant|serious', text, re.IGNORECASE):
            return "high"
        elif re.search(r'medium|moderate|\bmid\b', text, re.IGNORECASE):
            return "medium"
        elif re.search(r'\blow\b|minor|minimal', text, re.IGNORECASE):
            return "low"
        
        # Default risk level
        return "unknown"
