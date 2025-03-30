"""
LLM-based agent implementation.

This module provides a base implementation of an agent that uses LLMs
to make decisions and take actions.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Set, Type, ClassVar, Union
from pydantic import BaseModel, Field, root_validator

from ..agent import Agent, AgentConfig
from ..context import Context, MessageRole
from ..registry import register_agent
from ...utils.retryable import retryable
from ...utils.exceptions import AIModelError, AIModelTimeoutError
from ...services.ai_client import AIClient, AIClientFactory, AIModelProvider

logger = logging.getLogger(__name__)


class LLMAgentConfig(AgentConfig):
    """Configuration for an LLM-based agent."""
    model_provider: AIModelProvider = AIModelProvider.GEMINI
    function_calling_format: str = "auto"
    include_thinking_in_response: bool = False
    thinking_format: str = "thinking"  # "thinking", "json", "markdown"


@register_agent("llm_agent")
class LLMAgent(Agent):
    """Base class for agents that use LLMs to make decisions.
    
    This class provides a foundation for agents that use language models to
    process inputs, make decisions, and generate outputs.
    """
    
    def __init__(self, config: LLMAgentConfig):
        """Initialize the LLM agent with its configuration.
        
        Args:
            config: The agent configuration
        """
        super().__init__(config)
        self.config = config
        self.ai_client = AIClientFactory.create_client(config.model_provider)
    
    @retryable(max_retries=3, retry_delay=1, exceptions=[AIModelError, AIModelTimeoutError])
    async def _execute(self, context: Context) -> Context:
        """Execute the agent logic using the LLM.
        
        Args:
            context: The execution context
            
        Returns:
            The updated context with agent outputs
        """
        # Prepare the system message if not already present
        self._ensure_system_message(context)
        
        # Add thinking before generating the response
        thinking = await self._generate_thinking(context)
        if thinking:
            self.add_thought(context, thinking)
        
        # Generate the response
        response = await self._generate_response(context)
        
        # Process the response to extract function calls and content
        processed_response = await self._process_response(response, context)
        
        # Add the processed response to the context
        if self.config.include_thinking_in_response and thinking:
            if self.config.thinking_format == "thinking":
                processed_response = f"Thinking:\n{thinking}\n\nResponse:\n{processed_response}"
            elif self.config.thinking_format == "json":
                processed_response = f"```json\n{{\n  \"thinking\": {json.dumps(thinking)},\n  \"response\": {json.dumps(processed_response)}\n}}\n```\n"
            elif self.config.thinking_format == "markdown":
                processed_response = f"## Thinking\n\n{thinking}\n\n## Response\n\n{processed_response}"
        
        context.add_assistant_message(processed_response)
        
        # Add any extracted outputs to the context
        outputs = self._extract_outputs(processed_response)
        context.outputs.update(outputs)
        
        return context
    
    def _ensure_system_message(self, context: Context) -> None:
        """Ensure that there is a system message in the context.
        
        If no system message is present, add one using the agent's system prompt.
        
        Args:
            context: The execution context
        """
        has_system_message = any(msg.role == MessageRole.SYSTEM for msg in context.messages)
        
        if not has_system_message and self.config.system_prompt:
            context.add_message(MessageRole.SYSTEM, self.config.system_prompt)
    
    async def _generate_thinking(self, context: Context) -> str:
        """Generate thinking steps before producing the final response.
        
        This method can be overridden by subclasses to implement specific
        thinking processes.
        
        Args:
            context: The execution context
            
        Returns:
            The thinking steps as a string
        """
        # Default implementation does not add thinking
        return ""
    
    async def _generate_response(self, context: Context) -> str:
        """Generate a response using the AI model.
        
        Args:
            context: The execution context
            
        Returns:
            The model's response
        """
        messages = context.get_messages_for_llm()
        
        # Call the AI model with the messages
        response = await self.ai_client.get_completion(
            messages=messages,
            model=self.config.model_name,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            functions=[tool.to_function_spec() for tool in self.tools] if self.tools else None,
            function_call=self.config.function_calling_format if self.tools else None
        )
        
        return response.content
    
    async def _process_response(self, response: str, context: Context) -> str:
        """Process the response from the AI model.
        
        This method can extract and execute function calls from the response.
        
        Args:
            response: The response from the AI model
            context: The execution context
            
        Returns:
            The processed response
        """
        # Default implementation just returns the response
        return response
    
    def _extract_outputs(self, response: str) -> Dict[str, Any]:
        """Extract structured outputs from the response.
        
        This method can be overridden by subclasses to implement specific
        output extraction logic.
        
        Args:
            response: The processed response
            
        Returns:
            Extracted outputs as a dictionary
        """
        # Default implementation doesn't extract any outputs
        return {}
    
    async def _extract_and_execute_function_calls(self, text: str, context: Context) -> str:
        """Extract and execute function calls from the response text.
        
        Args:
            text: The response text
            context: The execution context
            
        Returns:
            The updated text with function call results
        """
        # Check for function call syntax
        function_call_pattern = r"```\s*(.+?)\s*\(\s*(.+?)\s*\)\s*```"
        function_calls = re.finditer(function_call_pattern, text)
        
        # Execute each function call
        for match in function_calls:
            full_match = match.group(0)
            function_name = match.group(1)
            args_str = match.group(2)
            
            try:
                # Parse the arguments
                args = json.loads(f"{{{args_str}}}")
                
                # Execute the function
                result = await self.use_tool(context, function_name, args)
                
                # Replace the function call with the result
                result_str = f"```{function_name} result:\n{json.dumps(result, indent=2)}\n```"
                text = text.replace(full_match, result_str)
            except Exception as e:
                # Replace the function call with the error
                error_str = f"```{function_name} error: {str(e)}```"
                text = text.replace(full_match, error_str)
        
        return text
