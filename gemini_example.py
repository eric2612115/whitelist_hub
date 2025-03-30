"""Example of using Google Gemini for whitelist analysis."""

import asyncio
import logging
import os
from dotenv import load_dotenv
import google.generativeai as genai

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# Ensure environment variables are loaded
load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Example Ethereum contract ABI (simplified)
EXAMPLE_ABI = [
    {
        "inputs": [],
        "name": "isWhitelisted",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "address", "name": "user", "type": "address"}],
        "name": "addToWhitelist",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "address", "name": "user", "type": "address"}],
        "name": "removeFromWhitelist",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]


async def main():
    """Run a simple example using Google Gemini."""
    
    # Create messages for Gemini
    messages = [
        {
            "role": "user", 
            "parts": [
                {
                    "text": f"""
                    Here is an Ethereum contract ABI. Analyze it and explain what whitelist mechanisms it implements:
                    
                    ABI: {str(EXAMPLE_ABI)}
                    """
                }
            ]
        }
    ]
    
    try:
        # Get model
        model = genai.GenerativeModel(model_name="gemini-1.5-flash-001")
        
        # Generate content
        logger.info("Sending request to Gemini...")
        response = model.generate_content(messages)
        
        # Print the response
        logger.info("\n=== Gemini Response ===\n")
        print(response.text)
        logger.info("\n=====================\n")
        
    except Exception as e:
        logger.error(f"Error getting completion from Gemini: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
