"""
Simple example application to demonstrate Whitelist Hub agent framework.

This script provides a simple CLI interface to interact with the agent framework
and run analyses on blockchain projects or contracts.
"""

import asyncio
import os
import sys
import json
import logging
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("whitelist_hub_example.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Import necessary components with absolute imports
from whitelist_hub.agent_framework.context import Context, Message, MessageRole
from whitelist_hub.agent_framework.agents import LLMAgent, CoordinatorAgent, CrawlerAgent, AnalyzerAgent, VerifierAgent
from whitelist_hub.agent_framework.registry import AgentRegistry
from whitelist_hub.workflows import create_project_analysis_workflow
from whitelist_hub.services.ai_client import AIModelProvider


async def run_interactive_session():
    """Run an interactive CLI session with the agent framework."""
    print("\n----- Whitelist Hub Agent Framework Example -----\n")
    print("This example demonstrates the agent framework's capabilities.")
    
    # Check for required environment variables
    required_vars = []
    if os.getenv("GEMINI_API_KEY") is None:
        required_vars.append("GEMINI_API_KEY")
    if os.getenv("ANTHROPIC_API_KEY") is None:
        required_vars.append("ANTHROPIC_API_KEY")
    
    if required_vars:
        print(f"\nWarning: The following environment variables are missing: {', '.join(required_vars)}")
        print("Some features may not work without these API keys.")
    
    # Create a context for the session
    context = Context()
    context.add_system_message("You are interacting with the Whitelist Hub agent framework.")
    
    # Main menu
    while True:
        print("\n----- Main Menu -----")
        print("1. Analyze a blockchain project")
        print("2. Analyze a smart contract")
        print("3. Chat with a coordinator agent")
        print("4. Chat with an analyzer agent")
        print("5. Exit")
        
        choice = input("\nEnter your choice (1-5): ").strip()
        
        if choice == "1":
            await analyze_project_interactive(context)
        elif choice == "2":
            await analyze_contract_interactive(context)
        elif choice == "3":
            await chat_with_agent_interactive("coordinator", context)
        elif choice == "4":
            await chat_with_agent_interactive("analyzer", context)
        elif choice == "5":
            print("\nExiting. Goodbye!")
            break
        else:
            print("\nInvalid choice. Please try again.")


async def analyze_project_interactive(context: Context):
    """Run an interactive project analysis session.
    
    Args:
        context: The session context
    """
    print("\n----- Analyze Blockchain Project -----")
    
    # Get project information
    project_name = input("\nEnter project name: ").strip()
    if not project_name:
        print("Project name is required. Returning to main menu.")
        return
    
    website = input("Enter project website URL (optional): ").strip()
    github_url = input("Enter project GitHub URL (optional): ").strip()
    
    # Choose AI model provider
    print("\nSelect AI model provider:")
    print("1. Google Gemini (best for code analysis)")
    print("2. Anthropic Claude (best for detailed reasoning)")
    choice = input("Enter your choice (1-2, default: 1): ").strip()
    
    if choice == "2":
        ai_model_provider = AIModelProvider.CLAUDE
        print("Using Claude for analysis.")
    else:
        ai_model_provider = AIModelProvider.GEMINI
        print("Using Gemini for analysis.")
    
    # Create and run the workflow
    print(f"\nStarting analysis of {project_name}...")
    print("This may take a few minutes. Progress will be displayed below.\n")
    
    try:
        # Create the workflow
        workflow = create_project_analysis_workflow(
            project_name=project_name,
            website=website,
            github_url=github_url,
            ai_model_provider=ai_model_provider
        )
        
        # Set up progress reporting
        def report_progress(event, data):
            if event == "task_started":
                print(f"Started task: {data.get('task_name', 'unknown')}")
            elif event == "task_completed":
                print(f"Completed task: {data.get('task_name', 'unknown')}")
            elif event == "task_failed":
                print(f"Task failed: {data.get('task_name', 'unknown')} - {data.get('error', '')}")
        
        workflow.add_global_listener(report_progress)
        
        # Update context
        context.inputs.update({
            "project_name": project_name,
            "website": website,
            "github_url": github_url
        })
        
        # Execute the workflow
        result_context = await workflow.execute(context)
        
        # Save the results
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)
        
        result_file = os.path.join(output_dir, f"{project_name}_analysis_result.json")
        with open(result_file, 'w') as f:
            json.dump(result_context.outputs, f, indent=2, default=str)
        
        print(f"\nAnalysis completed! Results saved to {result_file}")
        
        # Display summary
        if "synthesize_results" in result_context.outputs:
            print("\n----- Analysis Summary -----\n")
            summary = result_context.outputs["synthesize_results"]
            if isinstance(summary, dict) and "summary" in summary:
                print(summary["summary"])
            else:
                print(summary)
        
    except Exception as e:
        print(f"\nError during analysis: {str(e)}")


async def analyze_contract_interactive(context: Context):
    """Run an interactive contract analysis session.
    
    Args:
        context: The session context
    """
    print("\n----- Analyze Smart Contract -----")
    
    # Get contract information
    contract_address = input("\nEnter contract address: ").strip()
    if not contract_address:
        print("Contract address is required. Returning to main menu.")
        return
    
    # Choose blockchain
    print("\nSelect blockchain:")
    print("1. Ethereum")
    print("2. Polygon")
    print("3. Binance Smart Chain")
    print("4. Avalanche")
    print("5. Other")
    choice = input("Enter your choice (1-5, default: 1): ").strip()
    
    blockchain = "ethereum"  # Default
    if choice == "2":
        blockchain = "polygon"
    elif choice == "3":
        blockchain = "bsc"
    elif choice == "4":
        blockchain = "avalanche"
    elif choice == "5":
        blockchain = input("Enter blockchain name: ").strip().lower()
    
    # Choose AI model provider
    print("\nSelect AI model provider:")
    print("1. Google Gemini (best for code analysis)")
    print("2. Anthropic Claude (best for detailed reasoning)")
    choice = input("Enter your choice (1-2, default: 1): ").strip()
    
    if choice == "2":
        ai_model_provider = AIModelProvider.CLAUDE
        print("Using Claude for analysis.")
    else:
        ai_model_provider = AIModelProvider.GEMINI
        print("Using Gemini for analysis.")
    
    # Get the analyzer agent
    analyzer = AgentRegistry.get_agent("analyzer")
    if not analyzer:
        print("Analyzer agent not found. Please check your agent registry.")
        return
    
    # Create context
    context.inputs.update({
        "contract_address": contract_address,
        "blockchain": blockchain
    })
    
    print(f"\nStarting analysis of contract {contract_address} on {blockchain}...")
    print("This may take a minute or two. Please wait.\n")
    
    try:
        # Execute the agent
        result_context = await analyzer.execute(context)
        
        # Save the results
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)
        
        result_file = os.path.join(output_dir, f"{blockchain}_{contract_address}_analysis.json")
        with open(result_file, 'w') as f:
            json.dump(result_context.outputs, f, indent=2, default=str)
        
        print(f"\nAnalysis completed! Results saved to {result_file}")
        
        # Display the analysis
        if "contracts_analysis" in result_context.outputs:
            print("\n----- Contract Analysis -----\n")
            
            analysis = result_context.outputs["contracts_analysis"]
            if isinstance(analysis, dict) and "summary" in analysis:
                print(analysis["summary"])
            else:
                print(analysis)
        
    except Exception as e:
        print(f"\nError during analysis: {str(e)}")


async def chat_with_agent_interactive(agent_name: str, context: Context):
    """Run an interactive chat session with an agent.
    
    Args:
        agent_name: The name of the agent to chat with
        context: The session context
    """
    print(f"\n----- Chat with {agent_name.capitalize()} Agent -----")
    print("Type 'exit' to return to the main menu.")
    
    # Get the agent
    agent = AgentRegistry.get_agent(agent_name)
    if not agent:
        print(f"Agent '{agent_name}' not found. Please check your agent registry.")
        return
    
    # Create a new context for this chat
    chat_context = context.copy_with_empty_messages()
    chat_context.add_system_message(agent.config.system_prompt)
    
    while True:
        # Get user input
        user_input = input("\nYou: ").strip()
        
        if user_input.lower() == "exit":
            print("Returning to main menu.")
            break
        
        # Add user message to context
        chat_context.add_user_message(user_input)
        
        try:
            # Execute the agent
            print("\nThinking...")
            result_context = await agent.execute(chat_context)
            
            # Get the latest assistant message
            if result_context.messages:
                for msg in reversed(result_context.messages):
                    if msg.role == MessageRole.ASSISTANT:
                        print(f"\n{agent_name.capitalize()}: {msg.content}")
                        break
            
            # Update the chat context
            chat_context = result_context
            
        except Exception as e:
            print(f"\nError: {str(e)}")


def main():
    """Main entry point."""
    try:
        asyncio.run(run_interactive_session())
    except KeyboardInterrupt:
        print("\nInterrupted by user. Exiting.")
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        logger.exception("Unexpected error in main")


if __name__ == "__main__":
    main()
