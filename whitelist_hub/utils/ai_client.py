"""AI model API client."""

import logging
import json
import aiohttp
import asyncio
from typing import Dict, Any, Optional

from ..core.config import settings

logger = logging.getLogger(__name__)


class AIClient:
    """Client for AI model APIs."""
    
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
    
    def _get_api_key(self) -> str:
        """Get API key for the selected provider.
        
        Returns:
            API key
        """
        if self.provider == "openai":
            return settings.OPENAI_API_KEY
        elif self.provider == "anthropic":
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
            Response from AI model
        """
        if self.provider == "openai":
            return await self._get_openai_completion(prompt, temperature, max_tokens, model)
        elif self.provider == "anthropic":
            return await self._get_anthropic_completion(prompt, temperature, max_tokens, model)
        else:
            raise ValueError(f"Unsupported AI provider: {self.provider}")
    
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
        url = "https://api.openai.com/v1/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "model": model or "gpt-4-turbo-preview",
            "messages": [
                {"role": "system", "content": "You are an expert blockchain analyst agent for the Whitelist Hub system."},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        return await self._make_api_request(url, headers, data)
    
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
        url = "https://api.anthropic.com/v1/messages"
        
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key,
            "anthropic-version": "2023-06-01"
        }
        
        system_prompt = "You are an expert blockchain analyst agent for the Whitelist Hub system."
        
        data = {
            "model": model or "claude-3-opus-20240229",
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        response = await self._make_api_request(url, headers, data)
        
        # Convert Anthropic response format to match OpenAI format for consistency
        if "content" in response:
            return {
                "choices": [
                    {
                        "message": {
                            "content": response["content"][0]["text"],
                            "role": "assistant"
                        },
                        "finish_reason": response.get("stop_reason", "stop")
                    }
                ],
                "usage": {
                    "total_tokens": response.get("usage", {}).get("input_tokens", 0) + 
                                   response.get("usage", {}).get("output_tokens", 0),
                    "prompt_tokens": response.get("usage", {}).get("input_tokens", 0),
                    "completion_tokens": response.get("usage", {}).get("output_tokens", 0)
                }
            }
        
        # If response format is unexpected, return as is
        return response
    
    async def _make_api_request(self, url: str, headers: Dict[str, str], data: Dict[str, Any]) -> Dict[str, Any]:
        """Make API request with retries.
        
        Args:
            url: API URL
            headers: Request headers
            data: Request data
            
        Returns:
            API response
        """
        retries = 0
        last_error = None
        
        while retries < self.max_retries:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        url, 
                        headers=headers, 
                        json=data, 
                        timeout=aiohttp.ClientTimeout(total=self.timeout)
                    ) as response:
                        response_json = await response.json()
                        
                        if response.status != 200:
                            error_msg = response_json.get("error", {}).get("message", str(response_json))
                            logger.error(f"API request failed: {error_msg}")
                            last_error = ValueError(f"API request failed: {error_msg}")
                            
                            # Implement exponential backoff
                            await asyncio.sleep(2 ** retries)
                            retries += 1
                            continue
                        
                        return response_json
            
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_error = e
                logger.warning(f"API request attempt {retries + 1} failed: {str(e)}")
                
                # Implement exponential backoff
                await asyncio.sleep(2 ** retries)
                retries += 1
        
        # If we get here, all retries failed
        logger.error(f"All {self.max_retries} API request attempts failed")
        raise last_error or RuntimeError("API request failed with unknown error")
