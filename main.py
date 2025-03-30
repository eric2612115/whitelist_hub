"""Main entry point for Whitelist Hub CLI."""

import asyncio
import logging
import argparse
import json
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("whitelist_hub.log"),
        logging.StreamHandler()
    ]
)

# Import from whitelist_hub package using absolute imports
from whitelist_hub.agent_framework.context import Context
from whitelist_hub.agent_framework.registry import get_agent
from whitelist_hub.workflows import create_project_analysis_workflow
from whitelist_hub.services.ai_client import AIModelProvider


async def analyze_project(
    project_name: str,
    website: str = None,
    github_url: str = None,
    output_dir: str = "output",
    verbose: bool = False,
    ai_model_provider: AIModelProvider = AIModelProvider.GEMINI
):
    """Analyze a blockchain project.
    
    Args:
        project_name: The name of the project to analyze
        website: The project website URL
        github_url: The project GitHub URL
        output_dir: Directory to save output files
        verbose: Whether to enable verbose logging
        ai_model_provider: The AI model provider to use
        
    Returns:
        Analysis results
    """
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    
    logger.info(f"Starting analysis of project: {project_name}")
    
    # Create the workflow
    workflow = create_project_analysis_workflow(
        project_name=project_name,
        website=website,
        github_url=github_url,
        ai_model_provider=ai_model_provider
    )
    
    # Set up logging for workflow events
    def log_workflow_event(event_name, data):
        logger.info(f"Workflow event: {event_name} - {data.get('task_name', '')}")
        
    workflow.add_global_listener(log_workflow_event)
    
    # Create initial context
    context = Context(
        inputs={
            "project_name": project_name,
            "website": website,
            "github_url": github_url
        }
    )
    
    try:
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Execute the workflow
        logger.info("Executing workflow...")
        result_context = await workflow.execute(context)
        
        # Save the results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save full results
        result_file = os.path.join(output_dir, f"{project_name}_analysis_result.json")
        with open(result_file, 'w') as f:
            json.dump(result_context.outputs, f, indent=2, default=str)
        
        logger.info(f"Analysis completed. Results saved to {result_file}")
        
        # Generate and save summary
        if "synthesize_results" in result_context.outputs:
            summary_file = os.path.join(output_dir, f"{project_name}_summary.md")
            with open(summary_file, 'w') as f:
                f.write(f"# {project_name} Analysis Summary\n\n")
                f.write(f"Analysis completed on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                if isinstance(result_context.outputs["synthesize_results"], dict):
                    summary = result_context.outputs["synthesize_results"].get("summary", "")
                    if summary:
                        f.write(summary)
                else:
                    f.write(str(result_context.outputs["synthesize_results"]))
            
            logger.info(f"Summary saved to {summary_file}")
        
        return result_context.outputs
        
    except Exception as e:
        logger.error(f"Error during project analysis: {str(e)}")
        # Save error log
        error_file = os.path.join(output_dir, f"{project_name}_analysis_error.log")
        with open(error_file, 'w') as f:
            f.write(f"Error during analysis: {str(e)}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            if hasattr(e, "__traceback__"):
                import traceback
                f.write(traceback.format_exc())
        
        logger.info(f"Error log saved to {error_file}")
        raise


async def analyze_contract(
    contract_address: str,
    blockchain: str = "ethereum",
    output_dir: str = "output",
    verbose: bool = False,
    ai_model_provider: AIModelProvider = AIModelProvider.GEMINI
):
    """Analyze a specific smart contract.
    
    Args:
        contract_address: The contract address to analyze
        blockchain: The blockchain name (ethereum, polygon, etc.)
        output_dir: Directory to save output files
        verbose: Whether to enable verbose logging
        ai_model_provider: The AI model provider to use
        
    Returns:
        Analysis results
    """
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    
    logger.info(f"Starting analysis of contract: {contract_address} on {blockchain}")
    
    # Get the analyzer agent
    analyzer = get_agent("analyzer")
    if not analyzer:
        logger.error("Analyzer agent not found")
        return None
    
    # Create initial context
    context = Context(
        inputs={
            "contract_address": contract_address,
            "blockchain": blockchain
        }
    )
    
    try:
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Execute the agent
        logger.info("Executing analyzer agent...")
        result_context = await analyzer.execute(context)
        
        # Save the results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = os.path.join(output_dir, f"{blockchain}_{contract_address}_analysis.json")
        with open(result_file, 'w') as f:
            json.dump(result_context.outputs, f, indent=2, default=str)
        
        logger.info(f"Analysis completed. Results saved to {result_file}")
        
        return result_context.outputs
        
    except Exception as e:
        logger.error(f"Error during contract analysis: {str(e)}")
        # Save error log
        error_file = os.path.join(output_dir, f"{blockchain}_{contract_address}_error.log")
        with open(error_file, 'w') as f:
            f.write(f"Error during analysis: {str(e)}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            if hasattr(e, "__traceback__"):
                import traceback
                f.write(traceback.format_exc())
        
        logger.info(f"Error log saved to {error_file}")
        raise


def main():
    """Main entry point."""
    # Parse arguments
    parser = argparse.ArgumentParser(description="Whitelist Hub - Blockchain Project Analysis")
    parser.add_argument("--project", help="Project name to analyze")
    parser.add_argument("--website", help="Project website URL")
    parser.add_argument("--github", help="Project GitHub URL")
    parser.add_argument("--contract", help="Contract address to analyze")
    parser.add_argument("--blockchain", default="ethereum", help="Blockchain name for contract analysis")
    parser.add_argument("--output", default="output", help="Output directory for results")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--model", default="gemini", choices=["gemini", "claude", "openai"],
                       help="AI model provider to use")
    
    args = parser.parse_args()
    
    # Convert model choice to enum
    ai_model_provider = AIModelProvider.GEMINI
    if args.model == "claude":
        ai_model_provider = AIModelProvider.CLAUDE
    elif args.model == "openai":
        ai_model_provider = AIModelProvider.OPENAI
    
    # Check if any operation was specified
    if not (args.project or args.contract):
        parser.print_help()
        sys.exit(1)
    
    try:
        # Run analysis
        if args.project:
            result = asyncio.run(analyze_project(
                project_name=args.project,
                website=args.website,
                github_url=args.github,
                output_dir=args.output,
                verbose=args.verbose,
                ai_model_provider=ai_model_provider
            ))
            print(f"Project analysis completed successfully. Results in {args.output}")
            
        elif args.contract:
            result = asyncio.run(analyze_contract(
                contract_address=args.contract,
                blockchain=args.blockchain,
                output_dir=args.output,
                verbose=args.verbose,
                ai_model_provider=ai_model_provider
            ))
            print(f"Contract analysis completed successfully. Results in {args.output}")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
