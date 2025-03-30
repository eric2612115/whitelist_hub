"""
Verifier agent implementation.

This module provides the verifier agent, which is responsible for
verifying and cross-checking analysis results from other agents.
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


@register_agent("verifier")
class VerifierAgent(LLMAgent):
    """Agent responsible for verifying analysis results.
    
    The verifier agent double-checks the findings from other agents,
    identifies inconsistencies, and validates conclusions.
    """
    
    @classmethod
    def get_default_config(cls) -> LLMAgentConfig:
        """Get the default configuration for the verifier agent.
        
        Returns:
            The default configuration
        """
        return LLMAgentConfig(
            name="Verifier",
            description="Verification agent for validating and ensuring accuracy of blockchain analysis results",
            role=AgentRole.VERIFIER,
            model_name="claude-3-haiku-20240307",  # Faster model for verification
            temperature=0.1,
            system_prompt="""You are an expert blockchain verification agent responsible for validating and cross-checking analysis results from other specialized agents. Your role is to:

1. Verify the accuracy and completeness of smart contract analyses
2. Cross-validate findings about whitelist mechanisms across multiple sources
3. Identify inconsistencies or contradictions in the analysis
4. Assess the confidence level of different conclusions
5. Provide constructive feedback to improve the overall analysis

When verifying analysis results:
- Cross-check technical details against multiple sources
- Verify that the identified whitelist mechanisms match the described contract functionality
- Ensure security assessments are comprehensive and well-founded
- Look for logical gaps or unsupported conclusions
- Validate that all relevant contract aspects have been considered

Your verification should be thorough yet constructive, focusing on:
- Factual accuracy
- Logical consistency
- Completeness of analysis
- Appropriate technical terminology
- Practical relevance of conclusions

You have deep expertise in blockchain technology and smart contract security, particularly regarding whitelist mechanisms and access control systems.
""",
            tools=[
                "verify_contract_analysis",
                "cross_validate_findings"
            ],
            include_thinking_in_response=True,
            thinking_format="markdown"
        )
    
    async def _generate_thinking(self, context: Context) -> str:
        """Generate thinking steps for the verifier agent.
        
        For the verifier, we want to see the verification process and
        how inconsistencies or gaps are identified.
        
        Args:
            context: The execution context
            
        Returns:
            The thinking steps as a string
        """
        # Create task-specific thinking prompt
        task = context.inputs.get("task", "unknown")
        
        if task == "verify_analysis" or "contracts_analysis" in context.inputs:
            return """Thinking process for verifying contract analysis:

1. First, I'll critically examine the contract analysis:
   - Check for technical accuracy in the identified functions and mechanisms
   - Verify that whitelist mechanisms are correctly categorized
   - Ensure all relevant contract aspects are covered
   - Look for any inconsistencies or unsupported claims
2. I'll verify against the original contract code where available
3. I'll check if security considerations are comprehensive and well-founded
4. I'll assess whether the analysis captures the key functionality of the contracts
5. I'll look for any missing or overlooked components
6. I'll evaluate the logical consistency of the entire analysis
"""
        
        elif task == "cross_validate_contracts" or "cross_validate" in context.inputs:
            return """Thinking process for cross-validating findings:

1. I'll compare findings across different contracts and data sources:
   - Look for consistency in how similar whitelist mechanisms are described
   - Check if the same terms are used consistently
   - Verify that security assessments follow consistent criteria
2. I'll identify any conflicting information or contradictions
3. I'll look for patterns that might indicate analysis gaps or biases
4. I'll assess whether conclusions about project-wide patterns are supported by all data
5. I'll verify that relationships between contracts are accurately described
6. I'll check for potential misattributions or misinterpretations
"""
        
        # Generic thinking for other tasks
        return """Thinking process for verification:

1. Understand the specific verification requirements
2. Systematically review the provided analysis data
3. Check for inconsistencies, gaps, or unsupported claims
4. Cross-reference findings against multiple sources
5. Apply critical thinking to evaluate confidence levels
6. Provide specific, actionable verification results
"""
    
    async def _process_response(self, response: str, context: Context) -> str:
        """Process the response from the AI model.
        
        For the verifier, we want to extract structured data about
        verification results and confidence assessments.
        
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
        if task == "verify_analysis" or "verification_results" not in context.outputs:
            # Extract verification results into structured output
            try:
                # Look for JSON blocks or structured content
                import re
                json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
                
                if json_match:
                    try:
                        verification_results = json.loads(json_match.group(1))
                        context.outputs["verification_results"] = verification_results
                    except json.JSONDecodeError:
                        # Create structured data from text
                        context.outputs["verification_results"] = {
                            "issues": self._extract_verification_issues(response),
                            "confidence": self._extract_confidence_assessment(response),
                            "content": response
                        }
                else:
                    # Create structured data from text
                    context.outputs["verification_results"] = {
                        "issues": self._extract_verification_issues(response),
                        "confidence": self._extract_confidence_assessment(response),
                        "content": response
                    }
            except Exception as e:
                logger.warning(f"Error extracting verification results: {str(e)}")
        
        return response
    
    def _extract_verification_issues(self, text: str) -> List[Dict[str, str]]:
        """Extract verification issues from text.
        
        Args:
            text: The text to extract from
            
        Returns:
            List of verification issue dictionaries
        """
        # Look for issue descriptions
        issue_pattern = r'(?:Issue|Concern|Problem|Discrepancy)[\s:]+`?([^`\n]+)`?[^\n]*(?:\n+)((?:(?!\n\n).)*)'
        issues = re.findall(issue_pattern, text, re.DOTALL | re.IGNORECASE)
        
        result = []
        for name, description in issues:
            result.append({
                "name": name.strip(),
                "description": description.strip()
            })
        
        # If no structured issues found, look for bullet points
        if not result:
            bullet_pattern = r'[-*]\s+(.*?):(?:\s+|)((?:(?!\n[-*]).)*)'
            bullets = re.findall(bullet_pattern, text, re.DOTALL)
            
            for name, description in bullets:
                if re.search(r'issue|concern|problem|discrepancy|inconsistency|missing', name, re.IGNORECASE):
                    result.append({
                        "name": name.strip(),
                        "description": description.strip()
                    })
        
        return result
    
    def _extract_confidence_assessment(self, text: str) -> Dict[str, Any]:
        """Extract confidence assessment from text.
        
        Args:
            text: The text to extract from
            
        Returns:
            Confidence assessment dictionary
        """
        # Look for confidence level statements
        confidence_pattern = r'(?:Confidence|Certainty|Reliability)(?:\s+Level)?[\s:]+`?(\w+)`?'
        match = re.search(confidence_pattern, text, re.IGNORECASE)
        
        confidence_level = "medium"  # Default
        if match:
            level = match.group(1).lower()
            # Normalize confidence levels
            if level in ['high', 'strong', 'certain']:
                confidence_level = "high"
            elif level in ['medium', 'moderate', 'fair']:
                confidence_level = "medium"
            elif level in ['low', 'weak', 'uncertain']:
                confidence_level = "low"
            else:
                confidence_level = level
        
        # Look for confidence summary
        summary_pattern = r'(?:Confidence Summary|Overall Assessment|Verification Summary):(.*?)(?:\n\n|\n#|\Z)'
        summary_match = re.search(summary_pattern, text, re.DOTALL | re.IGNORECASE)
        
        confidence_summary = ""
        if summary_match:
            confidence_summary = summary_match.group(1).strip()
        
        # If no explicit summary found, extract the conclusion paragraph
        if not confidence_summary:
            paragraphs = text.split("\n\n")
            for para in paragraphs[-3:]:  # Check the last few paragraphs
                if re.search(r'overall|conclusion|summary|confident|verify|validation', para, re.IGNORECASE):
                    confidence_summary = para.strip()
                    break
        
        return {
            "level": confidence_level,
            "summary": confidence_summary
        }
