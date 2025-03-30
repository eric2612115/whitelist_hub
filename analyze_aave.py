"""Script to analyze AAVE directly."""

import asyncio
import json
import os
from datetime import datetime

from whitelist_hub.api.project_analysis_service import ProjectAnalysisService
from whitelist_hub.utils.ai_client import AIClient
from whitelist_hub.utils.firecrawl_client import FirecrawlClient
from whitelist_hub.prompts.prompt_manager import PromptManager
from whitelist_hub.services.defillama_service import DefiLlamaService
from whitelist_hub.utils.blockchain_client import BlockchainClient

# Ensure output directory exists
os.makedirs("output", exist_ok=True)

async def analyze_aave():
    """Analyze AAVE project directly."""
    # Print start message
    print(f"Starting AAVE analysis at {datetime.now().isoformat()}")
    
    # Initialize services
    ai_client = AIClient()
    prompt_manager = PromptManager(use_db=False, templates_dir="whitelist_hub/prompts/templates")
    blockchain_client = BlockchainClient()
    firecrawl_client = FirecrawlClient()
    defillama_service = DefiLlamaService()
    
    # Create project analysis service
    service = ProjectAnalysisService(
        ai_client=ai_client,
        prompt_manager=prompt_manager,
        blockchain_client=blockchain_client,
        firecrawl_client=firecrawl_client,
        defillama_service=defillama_service
    )
    
    # Define message callback
    async def message_callback(message):
        # Print progress to console
        if message.get("message_type") == "system":
            print(f"[SYSTEM] {message.get('text', '')}")
        elif message.get("type") == "analysis_completed":
            print(f"[COMPLETE] Analysis of AAVE completed!")
    
    # Analyze AAVE
    result = await service.analyze_project(
        project_name="AAVE",
        website="https://aave.com",
        github_url="https://github.com/aave",
        message_callback=message_callback
    )
    
    # Save result
    output_file = "output/AAVE_analysis_result.json"
    with open(output_file, "w") as f:
        json.dump(result, f, indent=2)
    
    print(f"Analysis complete! Results saved to {output_file}")
    print(f"AAVE received a {result.get('rating', {}).get('rating', 'N/A')} rating with score {result.get('rating', {}).get('overall_score', 0)}/100")
    
    top_factor = max(result.get('rating', {}).get('factors', {}), key=lambda k: result.get('rating', {}).get('factors', {}).get(k, 0))
    print(f"Top factor: {top_factor} with score {result.get('rating', {}).get('factors', {}).get(top_factor, 0)}/10")

if __name__ == "__main__":
    asyncio.run(analyze_aave())
