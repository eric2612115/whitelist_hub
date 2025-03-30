"""Main entry point for Whitelist Hub."""

import asyncio
import logging
import argparse
import json
from typing import Dict, Any, Optional

from whitelist_hub.agents.agent_factory import create_agent
from whitelist_hub.utils.ai_client import AIClient
from whitelist_hub.utils.langchain_client import LangChainClient
from whitelist_hub.utils.agent_framework import select_best_framework
from whitelist_hub.prompts.prompt_manager import PromptManager
from whitelist_hub.utils.blockchain_client import BlockchainClient
from whitelist_hub.services.defillama_service import DefiLlamaService


async def analyze_project(project_name: str, website: Optional[str] = None, github_url: Optional[str] = None, framework: str = "custom"):
    """Analyze a blockchain project.
    
    Args:
        project_name: Name of the project
        website: Project website URL
        github_url: Project GitHub URL
    """
    print(f"Starting analysis of project: {project_name}")
    
    # Create shared services and clients
    ai_client = AIClient()
    langchain_client = LangChainClient()
    prompt_manager = PromptManager(use_db=False, templates_dir="whitelist_hub/prompts/templates")
    blockchain_client = BlockchainClient()
    defillama_service = DefiLlamaService()
    
    # Determine if we should use LangChain for everything
    use_langchain = framework == "langchain"
    
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
        
        # Choose framework for this task
        if framework == "auto":
            task_framework = select_best_framework("abi_analysis", data_size=len(str(abi)), complexity="medium")
        else:
            task_framework = framework
        
        # Analyze ABI using appropriate framework
        if task_framework == "langchain":
            print(f"  Using LangChain for ABI analysis of {address}")
            # Prepare context for LangChain
            context = {
                "contract_address": address,
                "blockchain": blockchain,
                "abi": json.dumps(abi)[:1000] + "..." if len(json.dumps(abi)) > 1000 else json.dumps(abi)
            }
            
            # Run analysis using LangChain
            abi_analysis_result = await langchain_client.run_task("abi_analysis", context)
            
            # Parse the result
            from whitelist_hub.utils.agent_framework import parse_agent_output
            abi_analysis = parse_agent_output(abi_analysis_result, "abi_analysis")
            
            # Create a simple log
            from whitelist_hub.models.analysis_log import AnalysisLog
            abi_log = AnalysisLog(
                project_id="",
                contract_id="",
                analysis_id=f"langchain_abi_{address}",
                agent_type="langchain",
                execution_time_ms=0
            )
            
        else:
            print(f"  Using custom framework for ABI analysis of {address}")
            # Use the existing custom agent implementation
            abi_analysis, abi_log = await analysis_agent.analyze_contract_abi(
                contract_address=address,
                blockchain=blockchain,
                abi_json=abi
            )
        
        # Choose framework for proxy detection
        if framework == "auto":
            task_framework = select_best_framework("proxy_detection", complexity="high")
        else:
            task_framework = framework
        
        # Detect if proxy using appropriate framework
        if task_framework == "langchain":
            print(f"  Using LangChain for proxy detection of {address}")
            # Prepare context for LangChain
            context = {
                "contract_address": address,
                "blockchain": blockchain,
                "abi_analysis": json.dumps(abi_analysis) if isinstance(abi_analysis, dict) else str(abi_analysis)
            }
            
            # Run analysis using LangChain
            proxy_result = await langchain_client.run_task("proxy_detection", context)
            
            # Parse the result
            proxy_detection = parse_agent_output(proxy_result, "proxy_detection")
            
            # Create a simple log
            proxy_log = AnalysisLog(
                project_id="",
                contract_id="",
                analysis_id=f"langchain_proxy_{address}",
                agent_type="langchain",
                execution_time_ms=0
            )
            
        else:
            print(f"  Using custom framework for proxy detection of {address}")
            # Use the existing custom agent implementation
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
        whitelist_detected = False
        if isinstance(abi_analysis, dict):
            whitelist_detected = any("whitelist" in category.lower() for category in abi_analysis.get("function_categories", {}))
        elif hasattr(abi_analysis, "data") and hasattr(abi_analysis.data, "function_categories"):
            whitelist_detected = any("whitelist" in category.lower() for category in abi_analysis.data.function_categories)
        
        if whitelist_detected:
            # Choose framework for whitelist analysis
            if framework == "auto":
                task_framework = select_best_framework("whitelist_analysis", complexity="high")
            else:
                task_framework = framework
            
            # Analyze whitelist using appropriate framework
            if task_framework == "langchain":
                print(f"  Using LangChain for whitelist analysis of {address}")
                # Prepare context for LangChain
                context = {
                    "contract_address": address,
                    "blockchain": blockchain,
                    "contract_data": json.dumps(abi_analysis)[:2000] if isinstance(abi_analysis, dict) else str(abi_analysis)[:2000]
                }
                
                # Run analysis using LangChain
                whitelist_result = await langchain_client.run_task("whitelist_analysis", context)
                
                # Parse the result
                whitelist_analysis = parse_agent_output(whitelist_result, "whitelist_analysis")
                contract_analysis["whitelist_analysis"] = whitelist_analysis
                
            else:
                print(f"  Using custom framework for whitelist analysis of {address}")
                # Use the existing custom agent implementation
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
    parser.add_argument("--framework", choices=["custom", "langchain", "auto"], default="custom",
                        help="Agent framework to use: custom, langchain, or auto (will select best for each task)")
    
    args = parser.parse_args()
    
    # Create output directory
    import os
    os.makedirs("output", exist_ok=True)
    
    # Run analysis
    await analyze_project(args.project, args.website, args.github, args.framework)


if __name__ == "__main__":
    asyncio.run(main())
