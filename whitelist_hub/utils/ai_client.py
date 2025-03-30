"""AI model API client."""

import logging
import json
import asyncio
from typing import Dict, Any, Optional, List, Union

from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
import google.generativeai as genai
from google.generativeai.types import GenerationConfig
from ..core.config import settings

logger = logging.getLogger(__name__)


class AIClient:
    """Client for AI model APIs using official client libraries."""
    
    def __init__(self, provider: str = None, api_key: str = None, max_retries: int = 3, timeout: int = 60, custom_endpoint: str = None):
        """Initialize AI client.
        
        Args:
            provider: AI model provider (openai, anthropic, gemini, custom)
            api_key: API key for the provider
            max_retries: Maximum number of retries for API calls
            timeout: Timeout for API calls in seconds
            custom_endpoint: Custom API endpoint URL for custom providers
        """
        self.provider = provider or settings.AI_MODEL_PROVIDER
        self.api_key = api_key or self._get_api_key()
        self.max_retries = max_retries
        self.timeout = timeout
        self.custom_endpoint = custom_endpoint or settings.CUSTOM_AI_ENDPOINT
        self.system_prompt = "You are an expert blockchain analyst agent for the Whitelist Hub system."
        
        # Initialize clients
        if self.provider == "openai":
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                timeout=timeout,
                max_retries=max_retries
            )
        elif self.provider == "anthropic":
            self.client = AsyncAnthropic(
                api_key=self.api_key
            )
        elif self.provider == "gemini":
            genai.configure(api_key=self.api_key)
            self.client = genai
        elif self.provider == "custom":
            # For custom providers, we'll use a simple API wrapper
            # Actual implementation will depend on the custom API
            self.client = None
        else:
            raise ValueError(f"Unsupported AI provider: {self.provider}")
    
    def _get_api_key(self) -> str:
        """Get API key for the selected provider.
        
        Returns:
            API key
        """
        if self.provider == "openai":
            if not settings.OPENAI_API_KEY:
                raise ValueError("OpenAI API key not found in settings")
            return settings.OPENAI_API_KEY
        elif self.provider == "anthropic":
            if not settings.ANTHROPIC_API_KEY:
                raise ValueError("Anthropic API key not found in settings")
            return settings.ANTHROPIC_API_KEY
        elif self.provider == "gemini":
            if not settings.GEMINI_API_KEY:
                raise ValueError("Gemini API key not found in settings")
            return settings.GEMINI_API_KEY
        elif self.provider == "custom":
            if not settings.CUSTOM_AI_KEY:
                raise ValueError("Custom AI API key not found in settings")
            return settings.CUSTOM_AI_KEY
        else:
            raise ValueError(f"Unsupported AI provider: {self.provider}")
    
    async def get_completion(
        self, 
        prompt: str, 
        temperature: float = 0.1, 
        max_tokens: int = 2000,
        model: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        extra_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get completion from AI model.
        
        Args:
            prompt: Prompt text
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            model: Specific model to use (optional)
            
        Returns:
            Response from AI model in a standardized format
        """
        retries = 0
        last_error = None
        
        while retries < self.max_retries:
            try:
                if self.provider == "openai":
                    return await self._get_openai_completion(prompt, temperature, max_tokens, model, tools)
                elif self.provider == "anthropic":
                    return await self._get_anthropic_completion(prompt, temperature, max_tokens, model, tools)
                elif self.provider == "gemini":
                    return await self._get_gemini_completion(prompt, temperature, max_tokens, model)
                elif self.provider == "custom":
                    return await self._get_custom_completion(prompt, temperature, max_tokens, model, tools, extra_options)
                
            except Exception as e:
                last_error = e
                logger.warning(f"API request attempt {retries + 1} failed: {str(e)}")
                
                # Implement exponential backoff
                await asyncio.sleep(2 ** retries)
                retries += 1
        
        # If we get here, all retries failed
        logger.error(f"All {self.max_retries} API request attempts failed")
        raise last_error or RuntimeError("API request failed with unknown error")
    
    async def _get_openai_completion(
        self, 
        prompt: str, 
        temperature: float, 
        max_tokens: int,
        model: Optional[str],
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Get completion from OpenAI.
        
        Args:
            prompt: Prompt text
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            model: Specific model to use (optional)
            
        Returns:
            Response from OpenAI
        """
        kwargs = {
            "model": model or "gpt-4-turbo-preview",
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        # Add tools if provided
        if tools:
            kwargs["tools"] = tools
        
        response = await self.client.chat.completions.create(**kwargs)
        
        return {
            "choices": [
                {
                    "message": {
                        "content": response.choices[0].message.content,
                        "role": "assistant"
                    },
                    "finish_reason": response.choices[0].finish_reason
                }
            ],
            "usage": {
                "total_tokens": response.usage.total_tokens,
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens
            }
        }
    
    async def _get_anthropic_completion(
        self, 
        prompt: str, 
        temperature: float, 
        max_tokens: int,
        model: Optional[str],
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Get completion from Anthropic Claude.
        
        Args:
            prompt: Prompt text
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            model: Specific model to use (optional)
            
        Returns:
            Response formatted to match OpenAI structure
        """
        kwargs = {
            "model": model or "claude-3-opus-20240229",
            "system": self.system_prompt,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        # Add tools if supported and provided (check Anthropic API version)
        if tools and hasattr(self.client.messages, "create_with_tools"):
            response = await self.client.messages.create_with_tools(
                **kwargs,
                tools=tools
            )
        else:
            response = await self.client.messages.create(**kwargs)
        
        # Convert Anthropic response format to match OpenAI format for consistency
        content = response.content[0].text if isinstance(response.content, list) else response.content
        
        if hasattr(response, "content") and isinstance(response.content, list):
            message_content = response.content[0].text
        else:
            # Fallback for different response formats
            message_content = getattr(response, "text", str(response))
            
        # Handle tool calls if present
        tool_calls = []
        if hasattr(response, "tool_calls") and response.tool_calls:
            tool_calls = response.tool_calls
            
        result = {
            "choices": [
                {
                    "message": {
                        "content": message_content,
                        "role": "assistant",
                        "tool_calls": tool_calls
                    },
                    "finish_reason": getattr(response, "stop_reason", "stop")
                }
            ],
            "usage": {
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens
            }
        }
        
        return result
        
    async def _get_gemini_completion(
        self, 
        prompt: str, 
        temperature: float, 
        max_tokens: int,
        model: Optional[str]
    ) -> Dict[str, Any]:
        """Get completion from Google's Gemini model.
        
        Args:
            prompt: Prompt text
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            model: Specific model to use (optional)
            
        Returns:
            Response formatted to match OpenAI structure
        """
        try:
            # Configure the generation parameters
            generation_config = GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
            
            # Get the model
            model_name = model or "gemini-pro"
            model = self.client.GenerativeModel(model_name=model_name, 
                                              generation_config=generation_config)
            
            # Create the prompt
            gemini_prompt = [{
                "role": "user",
                "parts": [{"text": self.system_prompt + "\n\n" + prompt}]
            }]
            
            # Generate content
            response = await asyncio.to_thread(
                model.generate_content,
                gemini_prompt
            )
            
            # Extract content
            content = ""
            if hasattr(response, "text"):
                content = response.text
            elif hasattr(response, "parts"):
                content = "".join([part.text for part in response.parts if hasattr(part, "text")])
            else:
                content = str(response)
            
            # Convert to OpenAI format for consistency
            # Note: Gemini doesn't provide token usage, so we estimate
            estimated_prompt_tokens = len(prompt) / 4  # rough estimate
            estimated_completion_tokens = len(content) / 4  # rough estimate
            
            return {
                "choices": [
                    {
                        "message": {
                            "content": content,
                            "role": "assistant"
                        },
                        "finish_reason": "stop"
                    }
                ],
                "usage": {
                    "total_tokens": estimated_prompt_tokens + estimated_completion_tokens,
                    "prompt_tokens": estimated_prompt_tokens,
                    "completion_tokens": estimated_completion_tokens
                }
            }
            
        except Exception as e:
            logger.error(f"Error with Gemini API: {str(e)}")
            raise
            
    async def _get_custom_completion(
        self, 
        prompt: str, 
        temperature: float, 
        max_tokens: int,
        model: Optional[str],
        tools: Optional[List[Dict[str, Any]]] = None,
        extra_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get completion from a custom API endpoint (e.g., firecrawl.dev).
        
        Args:
            prompt: Prompt text
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            model: Specific model to use (optional)
            tools: List of tools to include with the request
            extra_options: Additional options for the custom API
            
        Returns:
            Response formatted to match OpenAI structure
        """
        import aiohttp
        
        try:
            # Prepare the request payload
            payload = {
                "prompt": prompt,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "system_message": self.system_prompt
            }
            
            # Add model if specified
            if model:
                payload["model"] = model
                
            # Add tools if provided
            if tools:
                payload["tools"] = tools
                
            # Add any extra options
            if extra_options:
                payload.update(extra_options)
                
            # Prepare headers
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Make the API request
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.custom_endpoint,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise ValueError(f"API request failed with status {response.status}: {error_text}")
                        
                    result = await response.json()
                    
            # Convert to standard format
            # This will need to be adjusted based on the actual API response format
            if "choices" in result and isinstance(result["choices"], list) and result["choices"]:
                # Response is already in OpenAI-like format
                return result
            elif "response" in result:
                # Simple API that just returns a response text
                content = result.get("response", "")
                estimated_prompt_tokens = len(prompt) / 4
                estimated_completion_tokens = len(content) / 4
                
                return {
                    "choices": [
                        {
                            "message": {
                                "content": content,
                                "role": "assistant"
                            },
                            "finish_reason": result.get("finish_reason", "stop")
                        }
                    ],
                    "usage": result.get("usage", {
                        "total_tokens": estimated_prompt_tokens + estimated_completion_tokens,
                        "prompt_tokens": estimated_prompt_tokens,
                        "completion_tokens": estimated_completion_tokens
                    })
                }
            else:
                # Unknown format, do best effort conversion
                logger.warning(f"Unknown custom API response format: {result}")
                content = str(result)
                
                return {
                    "choices": [
                        {
                            "message": {
                                "content": content,
                                "role": "assistant"
                            },
                            "finish_reason": "stop"
                        }
                    ],
                    "usage": {
                        "total_tokens": 0,
                        "prompt_tokens": 0,
                        "completion_tokens": 0
                    }
                }
                
        except Exception as e:
            logger.error(f"Error with custom API: {str(e)}")
            raise
