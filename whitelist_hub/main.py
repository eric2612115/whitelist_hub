"""Main entry point for Whitelist Hub."""

import asyncio
import logging
import os
import json
import argparse
from datetime import datetime

from .utils.ai_client import AIClient
from .utils.blockchain_client import BlockchainClient
from .utils.firecrawl_client import FirecrawlClient
from .prompts.prompt_manager import PromptManager
from .services.defillama_service import DefiLlamaService
from .agents.crew_factory import create_crew

logger = logging.getLogger(__name__)


async def analyze_project(
    project_name: str,
    website: str = None,
    github_url: str = None,
    output_dir: str = "output",
    verbose: bool = True
):
    """Analyze a blockchain project.
    
    Args:
        project_name: Name of the project
        website: Project website URL
        github_url: Project GitHub URL
        output_dir: Output directory for results
        verbose: Whether to enable verbose logging
    """
    # Create dependencies
    ai_client = AIClient()
    prompt_manager = PromptManager(use_db=False, templates_dir="whitelist_hub/prompts/templates")
    blockchain_client = BlockchainClient()
    firecrawl_client = FirecrawlClient()
    defillama_service = DefiLlamaService()
    
    # Create analysis crew
    crew = create_crew(
        crew_type="whitelist_analysis",
        ai_client=ai_client,
        prompt_manager=prompt_manager,
        blockchain_client=blockchain_client,
        firecrawl_client=firecrawl_client,
        defillama_service=defillama_service,
        verbose=verbose
    )
    
    # Configure for full analysis
    if isinstance(crew, object) and hasattr(crew, "create_full_analysis_crew"):
        crew.create_full_analysis_crew(project_name)
    
    # Prepare context
    context = {
        "project_name": project_name,
        "website": website,
        "github_url": github_url,
        "analysis_timestamp": datetime.now().isoformat()
    }
    
    # Run the crew
    logger.info(f"Starting analysis of {project_name}...")
    result = await crew.run(context)
    
    # Ensure the result is a dictionary
    if not isinstance(result, dict):
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except:
                result = {"result": result}
        else:
            result = {"result": str(result)}
    
    # Add metadata
    result["project_name"] = project_name
    result["analysis_timestamp"] = datetime.now().isoformat()
    if website:
        result["website"] = website
    if github_url:
        result["github_url"] = github_url
    
    # Get summary
    crew_summary = crew.get_summary()
    result["analysis_summary"] = crew_summary
    
    # Save result to output directory
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{project_name}_analysis_result.json")
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)
    
    logger.info(f"Analysis of {project_name} completed and saved to {output_path}")
    return result


async def analyze_contract(
    contract_address: str,
    blockchain: str = "ethereum",
    output_dir: str = "output",
    verbose: bool = True
):
    """Analyze a specific contract.
    
    Args:
        contract_address: Contract address
        blockchain: Blockchain name
        output_dir: Output directory for results
        verbose: Whether to enable verbose logging
    """
    # Create dependencies
    ai_client = AIClient()
    prompt_manager = PromptManager(use_db=False, templates_dir="whitelist_hub/prompts/templates")
    blockchain_client = BlockchainClient()
    
    # Create analysis crew
    crew = create_crew(
        crew_type="whitelist_analysis",
        ai_client=ai_client,
        prompt_manager=prompt_manager,
        blockchain_client=blockchain_client,
        verbose=verbose
    )
    
    # Configure for contract analysis
    if isinstance(crew, object) and hasattr(crew, "create_contract_analysis_crew"):
        crew.create_contract_analysis_crew([
            {"address": contract_address, "blockchain": blockchain}
        ])
    
    # Prepare context
    context = {
        "contract_address": contract_address,
        "blockchain": blockchain,
        "analysis_timestamp": datetime.now().isoformat()
    }
    
    # Run the crew
    logger.info(f"Starting analysis of contract {contract_address} on {blockchain}...")
    result = await crew.run(context)
    
    # Ensure the result is a dictionary
    if not isinstance(result, dict):
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except:
                result = {"result": result}
        else:
            result = {"result": str(result)}
    
    # Add metadata
    result["contract_address"] = contract_address
    result["blockchain"] = blockchain
    result["analysis_timestamp"] = datetime.now().isoformat()
    
    # Save result to output directory
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{blockchain}_{contract_address}_analysis_result.json")
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)
    
    logger.info(f"Analysis of contract {contract_address} completed and saved to {output_path}")
    return result


def main():
    """Main entry point."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("whitelist_hub.log"),
            logging.StreamHandler()
        ]
    )
    
    # Parse arguments
    parser = argparse.ArgumentParser(description="Whitelist Hub - Blockchain Project Analysis")
    parser.add_argument("--project", help="Project name to analyze")
    parser.add_argument("--website", help="Project website URL")
    parser.add_argument("--github", help="Project GitHub URL")
    parser.add_argument("--contract", help="Contract address to analyze")
    parser.add_argument("--blockchain", default="ethereum", help="Blockchain name for contract analysis")
    parser.add_argument("--output", default="output", help="Output directory for results")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Run analysis
    if args.project:
        result = asyncio.run(analyze_project(
            project_name=args.project,
            website=args.website,
            github_url=args.github,
            output_dir=args.output,
            verbose=args.verbose
        ))
    elif args.contract:
        result = asyncio.run(analyze_contract(
            contract_address=args.contract,
            blockchain=args.blockchain,
            output_dir=args.output,
            verbose=args.verbose
        ))
    else:
        parser.print_help()
        return
    
    logger.info("Analysis completed successfully")


if __name__ == "__main__":
    main()
