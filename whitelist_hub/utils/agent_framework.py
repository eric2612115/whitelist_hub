"""Agent framework utilities."""

import logging
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)


def select_best_framework(
    task_type: str,
    data_size: Optional[int] = None,
    complexity: Optional[str] = None,
    use_langchain: bool = False
) -> str:
    """Select the best framework for a specific task.
    
    Args:
        task_type: Type of task
        data_size: Size of input data (optional)
        complexity: Task complexity (low, medium, high)
        use_langchain: Whether to use LangChain as default
        
    Returns:
        Framework name ("custom", "langchain")
    """
    # Default to custom framework (our own implementation)
    if not use_langchain:
        return "custom"
    
    # For very large data or high complexity tasks, use LangChain
    if data_size and data_size > 100000:  # Over 100KB
        return "langchain"
    
    if complexity and complexity.lower() == "high":
        return "langchain"
    
    # Task-specific recommendations
    langchain_optimal_tasks = [
        "summarization",
        "agent_coordination",
        "multi_step_reasoning",
        "information_extraction",
        "document_qa"
    ]
    
    if any(task in task_type.lower() for task in langchain_optimal_tasks):
        return "langchain"
    
    # Default to custom framework
    return "custom"


def prepare_chain_context(
    task_type: str,
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """Prepare context for chain execution.
    
    Args:
        task_type: Type of task
        context: Original context dictionary
        
    Returns:
        Prepared context for chain
    """
    # Create a copy of the context
    prepared_context = context.copy()
    
    # Format complex objects for cleaner prompt
    for key, value in prepared_context.items():
        if isinstance(value, (dict, list)) and key != "system_prompt":
            # Special handling for 'abi' to keep it as JSON
            if key == "abi":
                continue
                
            if isinstance(value, dict):
                prepared_context[key] = "\n".join([f"{k}: {v}" for k, v in value.items()])
            elif isinstance(value, list):
                prepared_context[key] = "\n".join([str(item) for item in value])
    
    # Add task-specific context
    if task_type == "abi_analysis":
        prepared_context["task_description"] = "Analyze the provided contract ABI and categorize its functions by purpose."
    elif task_type == "proxy_detection":
        prepared_context["task_description"] = "Determine if this contract is a proxy or router pattern and identify its implementation address."
    elif task_type == "whitelist_analysis":
        prepared_context["task_description"] = "Analyze the whitelist mechanism implemented in this smart contract."
    
    return prepared_context


def parse_agent_output(output: str, task_type: str) -> Dict[str, Any]:
    """Parse output from agent into structured data.
    
    Args:
        output: Raw output from agent
        task_type: Type of task
        
    Returns:
        Parsed structured data
    """
    # Generic structure
    result = {
        "task_type": task_type,
        "success": True,
        "data": {}
    }
    
    # Check for clearly unsuccessful responses
    if "I cannot analyze" in output or "I don't have enough information" in output:
        result["success"] = False
        result["error"] = "Not enough information to complete analysis"
        return result
    
    # Task-specific parsing
    if task_type == "abi_analysis":
        # Extract function categories
        categories = {}
        
        # Simple heuristic parsing - in a real implementation this would be more sophisticated
        lines = output.split("\n")
        current_category = None
        
        for line in lines:
            if line.strip().endswith("functions:") or line.strip().endswith("Functions:"):
                current_category = line.split()[0].lower()
                categories[current_category] = []
            elif current_category and line.strip().startswith("- "):
                function_name = line.strip()[2:].split("(")[0].strip()
                categories[current_category].append({"name": function_name})
        
        result["data"]["function_categories"] = categories
        
    elif task_type == "proxy_detection":
        # Extract proxy information
        result["data"]["is_proxy"] = "proxy" in output.lower() and "not a proxy" not in output.lower()
        
        # Look for implementation address
        import re
        address_match = re.search(r"0x[a-fA-F0-9]{40}", output)
        if address_match:
            result["data"]["implementation_address"] = address_match.group(0)
    
    return result
