"""Main entry point for Whitelist Hub CLI."""

import asyncio
import logging
import argparse
from whitelist_hub.main import analyze_project, analyze_contract

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("whitelist_hub.log"),
        logging.StreamHandler()
    ]
)


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


if __name__ == "__main__":
    main()
