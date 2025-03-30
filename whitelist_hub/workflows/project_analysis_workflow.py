"""
Project analysis workflow configuration.

This module provides a workflow configuration for analyzing a blockchain project,
including its contracts, whitelist mechanisms, and security aspects.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel

from ..agent_framework.workflow import Workflow, WorkflowConfig
from ..agent_framework.task import TaskConfig
from ..services.ai_client import AIModelProvider


def create_project_analysis_workflow(
    project_name: str,
    website: Optional[str] = None,
    github_url: Optional[str] = None,
    ai_model_provider: AIModelProvider = AIModelProvider.GEMINI,
    metadata: Optional[Dict[str, Any]] = None
) -> Workflow:
    """Create a workflow for analyzing a blockchain project.
    
    Args:
        project_name: The name of the project to analyze
        website: The project website URL
        github_url: The project GitHub URL
        ai_model_provider: The AI model provider to use
        metadata: Additional metadata for the workflow
        
    Returns:
        A configured workflow
    """
    metadata = metadata or {}
    
    # Define tasks
    plan_task = TaskConfig(
        name="create_analysis_plan",
        description="Create an analysis plan for the project",
        agent_name="coordinator",
        inputs={
            "project_name": project_name,
            "website": website,
            "github_url": github_url,
            "ai_model_provider": ai_model_provider.value
        }
    )
    
    crawl_website_task = TaskConfig(
        name="crawl_website",
        description="Crawl the project website to gather information",
        agent_name="crawler",
        inputs={
            "project_name": project_name,
            "website": website,
            "analysis_depth": 2  # Crawl up to 2 levels deep by default
        },
        dependencies=["create_analysis_plan"]
    )
    
    crawl_github_task = TaskConfig(
        name="crawl_github",
        description="Analyze the project's GitHub repositories",
        agent_name="crawler",
        inputs={
            "project_name": project_name,
            "github_url": github_url,
            "max_repos": 3  # Analyze up to 3 repositories by default
        },
        dependencies=["create_analysis_plan"]
    )
    
    discover_contracts_task = TaskConfig(
        name="discover_contracts",
        description="Discover and validate contract addresses associated with the project",
        agent_name="crawler",
        inputs={
            "project_name": project_name,
            "website_data": "${crawl_website.outputs.website_data}",
            "github_data": "${crawl_github.outputs.github_data}",
            "max_contracts": 10  # Discover up to 10 contracts by default
        },
        dependencies=["crawl_website", "crawl_github"]
    )
    
    analyze_contracts_task = TaskConfig(
        name="analyze_contracts",
        description="Analyze the discovered smart contracts",
        agent_name="analyzer",
        inputs={
            "project_name": project_name,
            "contracts": "${discover_contracts.outputs.contracts}",
            "analysis_plan": "${create_analysis_plan.outputs.analysis_plan}"
        },
        dependencies=["discover_contracts"]
    )
    
    identify_whitelist_task = TaskConfig(
        name="identify_whitelist",
        description="Identify and classify whitelist mechanisms in the project's contracts",
        agent_name="analyzer",
        inputs={
            "project_name": project_name,
            "contracts_analysis": "${analyze_contracts.outputs.contracts_analysis}"
        },
        dependencies=["analyze_contracts"]
    )
    
    security_assessment_task = TaskConfig(
        name="security_assessment",
        description="Assess the security of the whitelist mechanisms and overall contract architecture",
        agent_name="analyzer",
        inputs={
            "project_name": project_name,
            "contracts_analysis": "${analyze_contracts.outputs.contracts_analysis}",
            "whitelist_mechanisms": "${identify_whitelist.outputs.whitelist_mechanisms}"
        },
        dependencies=["identify_whitelist"]
    )
    
    verify_analysis_task = TaskConfig(
        name="verify_analysis",
        description="Verify the accuracy and consistency of the analysis results",
        agent_name="verifier",
        inputs={
            "project_name": project_name,
            "contracts_analysis": "${analyze_contracts.outputs.contracts_analysis}",
            "whitelist_mechanisms": "${identify_whitelist.outputs.whitelist_mechanisms}",
            "security_assessment": "${security_assessment.outputs.security_assessment}"
        },
        dependencies=["security_assessment"]
    )
    
    synthesize_task = TaskConfig(
        name="synthesize_results",
        description="Synthesize all analysis results into a comprehensive report",
        agent_name="coordinator",
        inputs={
            "project_name": project_name,
            "website_data": "${crawl_website.outputs.website_data}",
            "github_data": "${crawl_github.outputs.github_data}",
            "contracts_analysis": "${analyze_contracts.outputs.contracts_analysis}",
            "whitelist_mechanisms": "${identify_whitelist.outputs.whitelist_mechanisms}",
            "security_assessment": "${security_assessment.outputs.security_assessment}",
            "verification_results": "${verify_analysis.outputs.verification_results}"
        },
        dependencies=["verify_analysis"]
    )
    
    # Create workflow configuration
    workflow_config = WorkflowConfig(
        name=f"{project_name} Analysis",
        description=f"Comprehensive analysis of {project_name} project and its whitelist mechanisms",
        tasks=[
            plan_task,
            crawl_website_task,
            crawl_github_task,
            discover_contracts_task,
            analyze_contracts_task,
            identify_whitelist_task,
            security_assessment_task,
            verify_analysis_task,
            synthesize_task
        ],
        max_concurrent_tasks=3,  # Allow up to 3 tasks to run concurrently
        timeout_seconds=3600,  # 1 hour timeout for the entire workflow
        metadata={
            "project_name": project_name,
            "website": website,
            "github_url": github_url,
            "ai_model_provider": ai_model_provider.value,
            **metadata
        }
    )
    
    # Create and return the workflow
    return Workflow(config=workflow_config)
