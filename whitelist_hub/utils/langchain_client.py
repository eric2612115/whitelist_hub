"""LangChain integration for Whitelist Hub."""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Union

from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain.schema import BaseMemory

from ..core.config import settings

logger = logging.getLogger(__name__)


class LangChainClient:
    """Client for LangChain-based agents and chains."""
    
    def __init__(
        self,
        provider: str = None,
        api_key: str = None,
        max_retries: int = 3,
        temperature: float = 0.1,
        memory: Optional[BaseMemory] = None
    ):
        """Initialize LangChain client.
        
        Args:
            provider: AI model provider (openai, anthropic)
            api_key: API key for the provider
            max_retries: Maximum number of retries for API calls
            temperature: Temperature for LLM generation
            memory: Optional memory component for LLM chains
        """
        self.provider = provider or settings.AI_MODEL_PROVIDER
        self.api_key = api_key or self._get_api_key()
        self.max_retries = max_retries
        self.temperature = temperature
        self.memory = memory
        self.system_prompt = "You are an expert blockchain analyst agent for the Whitelist Hub system."
        
        # Initialize LLM
        self.llm = self._initialize_llm()
    
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
    
    def _initialize_llm(self) -> Union[ChatOpenAI, ChatAnthropic]:
        """Initialize LLM based on provider.
        
        Returns:
            LLM instance
        """
        if self.provider == "openai":
            return ChatOpenAI(
                openai_api_key=self.api_key,
                temperature=self.temperature,
                max_retries=self.max_retries,
                model_name="gpt-4-turbo-preview"
            )
        elif self.provider == "anthropic":
            return ChatAnthropic(
                anthropic_api_key=self.api_key,
                temperature=self.temperature,
                max_retries=self.max_retries,
                model_name="claude-3-opus-20240229"
            )
        else:
            raise ValueError(f"Unsupported AI provider: {self.provider}")
    
    def create_chain_for_task(
        self,
        task_type: str,
        custom_prompt: Optional[str] = None,
        input_variables: Optional[List[str]] = None
    ) -> LLMChain:
        """Create a LangChain for a specific task.
        
        Args:
            task_type: Type of task (abi_analysis, proxy_detection, etc.)
            custom_prompt: Custom prompt text (optional)
            input_variables: Input variables for prompt template
            
        Returns:
            LLMChain for the specified task
        """
        # Default system context + task-specific template
        base_template = (
            "System: {system_prompt}\n\n"
            "Task: {task_description}\n\n"
            "Context: {context}\n\n"
            "Instructions: "
        )
        
        task_templates = {
            "abi_analysis": base_template + "Analyze the provided contract ABI and categorize its functions by purpose.",
            "proxy_detection": base_template + "Determine if this contract is a proxy or router pattern and identify its implementation address.",
            "whitelist_analysis": base_template + "Analyze the whitelist mechanism implemented in this smart contract."
        }
        
        # Use custom prompt if provided, otherwise use task-specific template
        template = custom_prompt or task_templates.get(task_type, base_template + "Complete the specified task.")
        
        # Set default input variables if not provided
        if input_variables is None:
            input_variables = ["system_prompt", "task_description", "context"]
        
        # Create prompt template
        prompt = PromptTemplate(
            template=template,
            input_variables=input_variables
        )
        
        # Create and return chain
        return LLMChain(
            prompt=prompt,
            llm=self.llm,
            memory=self.memory,
            verbose=True
        )
    
    async def run_task(
        self,
        task_type: str,
        context: Dict[str, Any],
        custom_prompt: Optional[str] = None
    ) -> str:
        """Run a task using LangChain.
        
        Args:
            task_type: Type of task
            context: Task context
            custom_prompt: Custom prompt (optional)
            
        Returns:
            Chain output
        """
        # Add system prompt to context
        context["system_prompt"] = self.system_prompt
        
        # Set task description if not provided
        if "task_description" not in context:
            context["task_description"] = f"Perform {task_type} analysis."
        
        # Create chain for task
        chain = self.create_chain_for_task(task_type, custom_prompt)
        
        # Run chain
        result = await chain.arun(**context)
        
        return result
