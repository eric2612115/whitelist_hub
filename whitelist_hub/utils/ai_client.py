"""AI model API client."""

import logging
import json
import asyncio
from typing import Dict, Any, Optional, List

from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from ..core.config import settings

logger = logging.getLogger(__name__)


class AIClient:
    """Client for AI model APIs using official client libraries."""
    
    def __init__(self, provider: str = None, api_key: str = None, max_retries: int = 3, timeout: int = 60):
        """Initialize AI client.
        
        Args:
            provider: AI model provider (openai, anthropic)
            api_key: API key for the provider
            max_retries: Maximum number of retries for API calls
            timeout: Timeout for API calls in seconds
        """
        self.provider = provider or settings.AI_MODEL_PROVIDER
        self.api_key = api_key or self._get_api_key()
        self.max_retries = max_retries
        self.timeout = timeout
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
        else:
            raise ValueError(f"Unsupported AI provider: {self.provider}")
    
    async def get_completion(
        self, 
        prompt: str, 
        temperature: float = 0.1, 
        max_tokens: int = 2000,
        model: Optional[str] = None
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
                    return await self._get_openai_completion(prompt, temperature, max_tokens, model)
                elif self.provider == "anthropic":
                    return await self._get_anthropic_completion(prompt, temperature, max_tokens, model)
                
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
        model: Optional[str]
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
        response = await self.client.chat.completions.create(
            model=model or "gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )
        
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
        model: Optional[str]
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
        response = await self.client.messages.create(
            model=model or "claude-3-opus-20240229",
            system=self.system_prompt,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Convert Anthropic response format to match OpenAI format for consistency
        return {
            "choices": [
                {
                    "message": {
                        "content": response.content[0].text,
                        "role": "assistant"
                    },
                    "finish_reason": response.stop_reason
                }
            ],
            "usage": {
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens
            }
        }
