"""
Coordinator agent implementation.

This module provides the coordinator agent, which is responsible for
creating analysis plans and coordinating the overall analysis process.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from ..agent import AgentConfig, AgentRole
from ..registry import register_agent
from ..context import Context
from .llm_agent import LLMAgent, LLMAgentConfig

logger = logging.getLogger(__name__)


@register_agent("coordinator")
class CoordinatorAgent(LLMAgent):
    """Agent responsible for planning and coordinating analyses.
    
    The coordinator agent creates analysis plans, delegates tasks to other
    agents, and synthesizes the final results of analysis workflows.
    """
    
    @classmethod
    def get_default_config(cls) -> LLMAgentConfig:
        """Get the default configuration for the coordinator agent.
        
        Returns:
            The default configuration
        """
        return LLMAgentConfig(
            name="Coordinator",
            description="Coordinator agent for planning and orchestrating blockchain project analysis",
            role=AgentRole.COORDINATOR,
            model_name="claude-3-opus-20240229",
            temperature=0.1,
            system_prompt="""You are an expert blockchain coordinator agent responsible for coordinating the analysis of blockchain projects and smart contracts. Your role is to:

1. Create comprehensive analysis plans for blockchain projects
2. Understand the different components and mechanisms of blockchain projects, especially those related to whitelisting functions
3. Synthesize the findings from other specialized agents into coherent summaries and reports
4. Ensure the analysis is thorough, accurate, and provides useful insights

When creating an analysis plan:
- Prioritize the most important contracts and components
- Identify key areas of focus, especially whitelist mechanisms
- Create a logical, step-by-step approach to the analysis
- Consider all potential sources of information

When synthesizing results:
- Integrate information from all analysis agents
- Highlight the most important findings
- Address inconsistencies or conflicts in the data
- Provide a clear, well-structured summary of the project's architecture and mechanisms
- Include a security assessment and recommendations where appropriate

You have deep expertise in blockchain technology, smart contract analysis, DeFi protocols, and whitelist mechanisms.
""",
            tools=[
                "create_analysis_plan",
                "synthesize_results"
            ],
            include_thinking_in_response=True,
            thinking_format="markdown"
        )
    
    async def _generate_thinking(self, context: Context) -> str:
        """Generate thinking steps before producing the final response.
        
        For the coordinator, we want detailed thinking to understand the
        planning and synthesis process.
        
        Args:
            context: The execution context
            
        Returns:
            The thinking steps as a string
        """
        # Create task-specific system prompt
        task = context.inputs.get("task", "unknown")
        thinking_prompt = ""
        
        if task == "create_analysis_plan" or "project_name" in context.inputs:
            project_name = context.inputs.get("project_name", "Unknown project")
            website = context.inputs.get("website", "No website provided")
            github_url = context.inputs.get("github_url", "No GitHub URL provided")
            
            thinking_prompt = f"""Thinking process for creating an analysis plan for {project_name}:

1. First, let me understand what information is available about the project
2. Consider what types of whitelist mechanisms might be present
3. Plan the order and priority of analysis tasks
4. Consider any potential challenges or areas that need special attention
5. Develop a structured, step-by-step plan that can guide other agents

Available project information:
- Project name: {project_name}
- Website: {website}
- GitHub repository: {github_url}
"""
        elif task == "synthesize_results" or "contracts_analysis" in context.inputs:
            project_name = context.inputs.get("project_name", "Unknown project")
            
            thinking_prompt = f"""Thinking process for synthesizing analysis results for {project_name}:

1. Let me review all the analysis data that has been collected
2. Identify the key findings about the project's whitelist mechanisms
3. Understand the overall architecture and how components work together
4. Evaluate security considerations and potential risks
5. Organize findings into a coherent, structured report
6. Provide clear conclusions and recommendations based on the data
"""
        
        # If no specific thinking prompt was created, use a generic one
        if not thinking_prompt:
            thinking_prompt = """Thinking through this task step by step:

1. Understand the task requirements
2. Analyze the available information
3. Consider different approaches and their implications
4. Develop a logical solution path
5. Organize my thoughts into a structured response
"""
        
        return thinking_prompt
    
    async def _process_response(self, response: str, context: Context) -> str:
        """Process the response from the AI model.
        
        For the coordinator, we want to extract structured information from
        the response, such as analysis plans and synthesis results.
        
        Args:
            response: The response from the AI model
            context: The execution context
            
        Returns:
            The processed response
        """
        # Extract and execute any function calls
        response = await self._extract_and_execute_function_calls(response, context)
        
        # Determine the task type from context
        task = context.inputs.get("task", "unknown")
        
        # Process based on task type
        if task == "create_analysis_plan" or "project_name" in context.inputs and "analysis_plan" not in context.outputs:
            # Extract analysis plan from text if not explicitly returned by a function call
            try:
                # Simple heuristic: Try to extract a JSON-like structure
                import re
                import json
                
                json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
                if json_match:
                    try:
                        analysis_plan = json.loads(json_match.group(1))
                        context.outputs["analysis_plan"] = analysis_plan
                    except json.JSONDecodeError:
                        logger.warning("Found JSON block but could not parse it as valid JSON")
            except Exception as e:
                logger.warning(f"Error extracting analysis plan: {str(e)}")
        
        return response
