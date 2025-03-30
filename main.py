"""Main entry point for Whitelist Hub."""

import asyncio
import logging
import argparse
import json
from typing import Dict, Any, Optional

from whitelist_hub.agents.agent_factory import create_agent
from whitelist_hub.utils.ai_client import AIClient
from whitelist_hub.prompts.prompt_manager import PromptManager
from whitelist_hub.utils.blockchain_client import BlockchainClient
from whitelist_hub.services.defillama_service import DefiLlamaService


async def analyze_project(project_name: str, website: Optional[str] = None, github_url: Optional[str] = None):
    """Analyze a blockchain project.
    
    Args:
        project_name: Name of the project
        website: Project website URL
        github_url: Project GitHub URL
    """
    print(f"Starting analysis of project: {project_name}")
    
    # Create shared services and clients
    ai_client = AIClient()
    prompt_manager = PromptManager(use_db=False, templates_dir="whitelist_hub/prompts/templates")
    blockchain_client = BlockchainClient()
    defillama_service = DefiLlamaService()
    
    # Create agents
    coordinator_agent = create_agent(
        "coordinator",
        ai_client=ai_client,
        prompt_manager=prompt_manager
    )
    
    crawler_agent = create_agent(
        "crawler",
        ai_client=ai_client,
        prompt_manager=prompt_manager,
        blockchain_client=blockchain_client,
        defillama_service=defillama_service
    )
    
    analysis_agent = create_agent(
        "analyzer",
        ai_client=ai_client,
        prompt_manager=prompt_manager,
        blockchain_client=blockchain_client
    )
    
    verifier_agent = create_agent(
        "verifier",
        ai_client=ai_client,
        prompt_manager=prompt_manager,
        blockchain_client=blockchain_client
    )
    
    # Step 1: Crawl initial data
    print("Step 1: Crawling project information...")
    project_data, crawl_log = await crawler_agent.crawl_project_information(
        project_name=project_name,
        website=website,
        github_url=github_url
    )
    
    # Save crawl log
    with open(f"output/{project_name}_crawl_log.json", "w") as f:
        json.dump(crawl_log.dict(), f, indent=2)
    
    # Step 2: Create analysis plan
    print("Step 2: Creating analysis plan...")
    analysis_plan, plan_log = await coordinator_agent.create_analysis_plan(
        project_name=project_name,
        project_data=project_data
    )
    
    # Save plan log
    with open(f"output/{project_name}_plan_log.json", "w") as f:
        json.dump(plan_log.dict(), f, indent=2)
    
    # Step 3: Analyze contracts found during crawling
    print("Step 3: Analyzing contracts...")
    contract_analyses = []
    
    for contract_info in project_data.get("contract_addresses", []):
        address = contract_info.get("address")
        blockchain = contract_info.get("blockchain", "ethereum")
        
        if not address:
            continue
        
        print(f"  Analyzing contract: {address} on {blockchain}")
        
        # Get contract ABI
        abi = await blockchain_client.fetch_contract_abi(address, blockchain)
        
        # Analyze ABI
        abi_analysis, abi_log = await analysis_agent.analyze_contract_abi(
            contract_address=address,
            blockchain=blockchain,
            abi_json=abi
        )
        
        # Detect if proxy
        proxy_detection, proxy_log = await analysis_agent.detect_proxy_pattern(
            contract_address=address,
            blockchain=blockchain
        )
        
        # Combine analyses
        contract_analysis = {
            "address": address,
            "blockchain": blockchain,
            "abi_analysis": abi_analysis,
            "proxy_detection": proxy_detection,
            "is_proxy": proxy_detection.get("is_proxy", False)
        }
        
        # If whitelist functionality detected, analyze it
        if any("whitelist" in category.lower() for category in abi_analysis.get("function_categories", {})):
            whitelist_analysis, whitelist_log = await analysis_agent.analyze_whitelist_mechanism(
                contract_address=address,
                contract_data=abi_analysis,
                blockchain=blockchain
            )
            
            contract_analysis["whitelist_analysis"] = whitelist_analysis
        
        contract_analyses.append(contract_analysis)
        
        # Save contract analysis logs
        with open(f"output/{blockchain}_{address}_analysis_log.json", "w") as f:
            json.dump({
                "abi_log": abi_log.dict(),
                "proxy_log": proxy_log.dict()
            }, f, indent=2)
    
    # Step 4: Verify and validate the analyses
    print("Step 4: Verifying analyses...")
    verified_analyses = []
    
    for contract_analysis in contract_analyses:
        # Define a simple schema for validation
        schema = {
            "type": "object",
            "required": ["address", "blockchain"],
            "properties": {
                "address": {"type": "string"},
                "blockchain": {"type": "string"}
            }
        }
        
        verified_result, verification_log = await verifier_agent.verify_analysis_result(
            analysis_result=contract_analysis,
            contract_schema=schema
        )
        
        verified_analyses.append(verified_result)
        
        # Save verification log
        address = contract_analysis.get("address")
        blockchain = contract_analysis.get("blockchain", "ethereum")
        
        with open(f"output/{blockchain}_{address}_verification_log.json", "w") as f:
            json.dump(verification_log.dict(), f, indent=2)
    
    # Step 5: Synthesize final results
    print("Step 5: Synthesizing results...")
    
    # Prepare data for synthesis
    synthesis_data = {
        "project_overview": project_data,
        "contract_analyses": verified_analyses,
        "whitelist_mechanisms": [
            analysis.get("whitelist_analysis") 
            for analysis in verified_analyses 
            if "whitelist_analysis" in analysis
        ],
        "user_flows": [],  # Would be populated in a full implementation
        "security_assessment": {
            "risk_level": "medium",  # Simplified for this example
            "findings": []
        }
    }
    
    final_synthesis, synthesis_log = await coordinator_agent.synthesize_analysis_results(
        project_name=project_name,
        project_overview=synthesis_data["project_overview"],
        contract_analyses=synthesis_data["contract_analyses"],
        whitelist_mechanisms=synthesis_data["whitelist_mechanisms"],
        user_flows=synthesis_data["user_flows"],
        security_assessment=synthesis_data["security_assessment"]
    )
    
    # Save final results
    with open(f"output/{project_name}_analysis_result.json", "w") as f:
        json.dump(final_synthesis, f, indent=2)
    
    with open(f"output/{project_name}_synthesis_log.json", "w") as f:
        json.dump(synthesis_log.dict(), f, indent=2)
    
    print(f"Analysis complete. Results saved in output/{project_name}_analysis_result.json")


async def main():
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
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Whitelist Hub - Blockchain Project Analysis")
    parser.add_argument("project", help="Project name to analyze")
    parser.add_argument("--website", help="Project website URL")
    parser.add_argument("--github", help="Project GitHub URL")
    
    args = parser.parse_args()
    
    # Create output directory
    import os
    os.makedirs("output", exist_ok=True)
    
    # Run analysis
    await analyze_project(args.project, args.website, args.github)


if __name__ == "__main__":
    asyncio.run(main())
