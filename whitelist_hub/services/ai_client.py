"""
AI client for interacting with language models.

This module provides a unified interface for interacting with different
language model providers like Gemini, Claude, and OpenAI.
"""

import os
import json
import logging
import asyncio
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Type, ClassVar, Union
from pydantic import BaseModel, Field

import google.generativeai as genai
from anthropic import Anthropic, AsyncAnthropic
from openai import AsyncOpenAI

from ..utils.retryable import async_retry
from ..utils.exceptions import AIModelError, AIModelTimeoutError

logger = logging.getLogger(__name__)


class AIModelProvider(str, Enum):
    """Supported AI model providers."""
    GEMINI = "gemini"
    CLAUDE = "claude"
    OPENAI = "openai"


class AIModelResponse(BaseModel):
    """Model for AI model responses."""
    content: str
    model: str
    usage: Dict[str, int] = Field(default_factory=dict)
    function_call: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AIClient(ABC):
    """Base class for AI model clients."""
    
    @abstractmethod
    async def get_completion(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        functions: Optional[List[Dict[str, Any]]] = None,
        function_call: Optional[str] = None,
        **kwargs: Any
    ) -> AIModelResponse:
        """Get a completion from the AI model.
        
        Args:
            messages: List of messages in the conversation
            model: The model to use
            temperature: Temperature for sampling
            max_tokens: Maximum number of tokens to generate
            functions: List of function specifications
            function_call: Function calling behavior
            **kwargs: Additional parameters for the model
            
        Returns:
            The model's response
        """
        pass


class GeminiClient(AIClient):
    """Client for Google's Gemini API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Gemini client.
        
        Args:
            api_key: Gemini API key (optional, can be read from environment)
        """
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("Gemini API key is required")
        
        genai.configure(api_key=self.api_key)
    
    async def get_completion(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        functions: Optional[List[Dict[str, Any]]] = None,
        function_call: Optional[str] = None,
        **kwargs: Any
    ) -> AIModelResponse:
        """Get a completion from Gemini.
        
        Args:
            messages: List of messages in the conversation
            model: The model to use (default: gemini-2.0-pro-001)
            temperature: Temperature for sampling
            max_tokens: Maximum number of tokens to generate
            functions: List of function specifications
            function_call: Function calling behavior
            **kwargs: Additional parameters for the model
            
        Returns:
            The model's response
        """
        model = model or "gemini-2.0-pro-001"
        
        try:
            # Convert messages to Gemini format
            gemini_messages = []
            
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                parts = msg.get("parts", [])
                
                if not parts and content:
                    parts = [{"text": content}]
                
                if role == "system":
                    # Convert to user message with system instruction
                    gemini_messages.append({
                        "role": "user",
                        "parts": parts or [{"text": content}]
                    })
                elif role == "user":
                    gemini_messages.append({
                        "role": "user",
                        "parts": parts or [{"text": content}]
                    })
                elif role == "assistant":
                    gemini_messages.append({
                        "role": "model",
                        "parts": parts or [{"text": content}]
                    })
            
            # Set up generation config
            generation_config = {
                "temperature": temperature,
                **kwargs
            }
            
            if max_tokens is not None:
                generation_config["max_output_tokens"] = max_tokens
            
            # Create model
            gemini_model = genai.GenerativeModel(model_name=model)
            
            # Add tool/function calling if provided
            if functions:
                # Convert functions to Gemini tools format
                tool_declarations = []
                
                for func in functions:
                    tool_declaration = {
                        "name": func["name"],
                        "description": func.get("description", ""),
                        "parameters": func.get("parameters", {})
                    }
                    tool_declarations.append(tool_declaration)
                
                if tool_declarations:
                    gemini_model = genai.GenerativeModel(
                        model_name=model,
                        tools=tool_declarations,
                        generation_config=generation_config
                    )
            
            # Run in an async context
            loop = asyncio.get_event_loop()
            
            def sync_run():
                # If there are multiple messages, handle as a conversation
                if len(gemini_messages) > 1:
                    chat = gemini_model.start_chat(history=gemini_messages[:-1])
                    response = chat.send_message(
                        gemini_messages[-1].get("parts", [{"text": ""}])[0].get("text", ""),
                        generation_config=generation_config
                    )
                else:
                    # Single message
                    response = gemini_model.generate_content(
                        gemini_messages[0] if gemini_messages else "",
                        generation_config=generation_config
                    )
                return response
            
            # Run the generation
            response = await loop.run_in_executor(None, sync_run)
            
            # Process the response
            content = response.text
            
            return AIModelResponse(
                content=content,
                model=model,
                usage={},
                metadata={"response_obj": str(response)}
            )
            
        except Exception as e:
            logger.error(f"Error in Gemini completion: {str(e)}")
            raise AIModelError(f"Gemini API error: {str(e)}")


class ClaudeClient(AIClient):
    """Client for Anthropic's Claude API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Claude client.
        
        Args:
            api_key: Claude API key (optional, can be read from environment)
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Claude API key is required")
        
        self.client = AsyncAnthropic(api_key=self.api_key)
    
    async def get_completion(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        functions: Optional[List[Dict[str, Any]]] = None,
        function_call: Optional[str] = None,
        **kwargs: Any
    ) -> AIModelResponse:
        """Get a completion from Claude.
        
        Args:
            messages: List of messages in the conversation
            model: The model to use (default: claude-3-opus-20240229)
            temperature: Temperature for sampling
            max_tokens: Maximum number of tokens to generate
            functions: List of function specifications
            function_call: Function calling behavior
            **kwargs: Additional parameters for the model
            
        Returns:
            The model's response
        """
        model = model or "claude-3-opus-20240229"
        
        try:
            # Convert to Claude format
            system_message = None
            claude_messages = []
            
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                if role == "system":
                    system_message = content
                elif role == "user":
                    claude_messages.append({
                        "role": "user",
                        "content": content
                    })
                elif role == "assistant":
                    claude_messages.append({
                        "role": "assistant",
                        "content": content
                    })
                elif role == "function":
                    # Claude doesn't support function messages directly
                    # Convert to assistant message
                    claude_messages.append({
                        "role": "assistant",
                        "content": f"Function result from {msg.get('name', 'function')}:\n{content}"
                    })
            
            # Set up the request parameters
            request_params = {
                "model": model,
                "messages": claude_messages,
                "temperature": temperature,
                "max_tokens": max_tokens or 4096,
                **kwargs
            }
            
            # Add system prompt if provided
            if system_message:
                request_params["system"] = system_message
            
            # Add tool/function calling if provided
            if functions:
                # Claude's tool calling format
                tools = []
                for func in functions:
                    tool = {
                        "name": func["name"],
                        "description": func.get("description", ""),
                        "input_schema": func.get("parameters", {})
                    }
                    tools.append(tool)
                
                request_params["tools"] = tools
                
                if function_call and function_call != "auto":
                    request_params["tool_choice"] = function_call
            
            # Clean up None values
            request_params = {k: v for k, v in request_params.items() if v is not None}
            
            # Get completion
            response = await self.client.messages.create(**request_params)
            
            # Process the response
            content = response.content[0].text
            
            # Check for tool calls
            function_call_data = None
            if hasattr(response, "tool_calls") and response.tool_calls:
                tool_call = response.tool_calls[0]
                function_call_data = {
                    "name": tool_call.name,
                    "arguments": json.loads(tool_call.input) if isinstance(tool_call.input, str) else tool_call.input
                }
            
            return AIModelResponse(
                content=content,
                model=model,
                usage={
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                },
                function_call=function_call_data,
                metadata={"response_id": response.id}
            )
            
        except Exception as e:
            logger.error(f"Error in Claude completion: {str(e)}")
            raise AIModelError(f"Claude API error: {str(e)}")


class OpenAIClient(AIClient):
    """Client for OpenAI's API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the OpenAI client.
        
        Args:
            api_key: OpenAI API key (optional, can be read from environment)
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        self.client = AsyncOpenAI(api_key=self.api_key)
    
    async def get_completion(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        functions: Optional[List[Dict[str, Any]]] = None,
        function_call: Optional[str] = None,
        **kwargs: Any
    ) -> AIModelResponse:
        """Get a completion from OpenAI.
        
        Args:
            messages: List of messages in the conversation
            model: The model to use (default: gpt-4)
            temperature: Temperature for sampling
            max_tokens: Maximum number of tokens to generate
            functions: List of function specifications
            function_call: Function calling behavior
            **kwargs: Additional parameters for the model
            
        Returns:
            The model's response
        """
        model = model or "gpt-4"
        
        try:
            # OpenAI format is already compatible
            request_params = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                **kwargs
            }
            
            if max_tokens is not None:
                request_params["max_tokens"] = max_tokens
            
            # Add function calling if provided
            if functions:
                request_params["tools"] = [{"type": "function", "function": func} for func in functions]
                
                if function_call:
                    if function_call == "auto":
                        request_params["tool_choice"] = "auto"
                    else:
                        request_params["tool_choice"] = {
                            "type": "function",
                            "function": {"name": function_call}
                        }
            
            # Get completion
            response = await self.client.chat.completions.create(**request_params)
            
            # Process the response
            content = response.choices[0].message.content or ""
            
            # Check for function calls
            function_call_data = None
            if response.choices[0].message.tool_calls:
                tool_call = response.choices[0].message.tool_calls[0]
                if tool_call.type == "function":
                    function_call_data = {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments
                    }
            
            return AIModelResponse(
                content=content,
                model=model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                function_call=function_call_data,
                metadata={"response_id": response.id}
            )
            
        except Exception as e:
            logger.error(f"Error in OpenAI completion: {str(e)}")
            raise AIModelError(f"OpenAI API error: {str(e)}")


class AIClientFactory:
    """Factory for creating AI clients."""
    
    @staticmethod
    def create_client(provider: AIModelProvider, api_key: Optional[str] = None) -> AIClient:
        """Create an AI client for the specified provider.
        
        Args:
            provider: The AI model provider
            api_key: Optional API key for the provider
            
        Returns:
            An AI client instance
            
        Raises:
            ValueError: If the provider is not supported
        """
        if provider == AIModelProvider.GEMINI:
            return GeminiClient(api_key)
        elif provider == AIModelProvider.CLAUDE:
            return ClaudeClient(api_key)
        elif provider == AIModelProvider.OPENAI:
            return OpenAIClient(api_key)
        else:
            raise ValueError(f"Unsupported AI model provider: {provider}")
