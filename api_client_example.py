"""Example client for Whitelist Hub API."""

import asyncio
import json
import websockets
import aiohttp
import sys

API_BASE_URL = "http://localhost:8000/api"
WS_BASE_URL = "ws://localhost:8000/ws"

async def interact_with_api():
    """Interact with the Whitelist Hub API."""
    async with aiohttp.ClientSession() as session:
        # Step 1: Create a session
        print("Creating session...")
        async with session.post(f"{API_BASE_URL}/sessions") as response:
            if response.status != 200:
                print(f"Error creating session: {response.status}")
                return
            
            session_data = await response.json()
            session_id = session_data["session_id"]
            print(f"Session created with ID: {session_id}")
        
        # Step 2: Connect to WebSocket
        print(f"Connecting to WebSocket...")
        async with websockets.connect(f"{WS_BASE_URL}/{session_id}") as websocket:
            # Receive welcome message
            welcome = await websocket.recv()
            print(f"Server: {json.loads(welcome)['text']}")
            
            # Send message to analyze AAVE
            message = {
                "type": "message",
                "text": "Analyze AAVE project for me"
            }
            await websocket.send(json.dumps(message))
            print(f"You: {message['text']}")
            
            # Receive response
            response = await websocket.recv()
            response_data = json.loads(response)
            print(f"Server: {response_data['text']}")
            
            # Process progress messages
            print("\nAnalysis Progress:")
            try:
                while True:
                    # Set timeout for user input
                    message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    message_data = json.loads(message)
                    
                    # Print progress messages
                    if message_data.get("message_type") == "system":
                        print(f"  [Progress] {message_data['text']}")
                    elif message_data.get("type") == "analysis_completed":
                        print(f"  [Complete] Analysis of AAVE completed!")
                        break
                    elif message_data.get("message_type") == "normal" and message_data.get("role") == "assistant":
                        print(f"Server: {message_data['text']}")
            except asyncio.TimeoutError:
                # Check if user wants to send a message
                print("\nAnalysis is running in the background. You can:")
                print("1. Wait for it to complete")
                print("2. Ask a question about the progress")
                print("3. Exit")
                choice = input("Enter your choice (1/2/3): ")
                
                if choice == "2":
                    question = input("Enter your question: ")
                    message = {
                        "type": "message",
                        "text": question
                    }
                    await websocket.send(json.dumps(message))
                    print(f"You: {message['text']}")
                    
                    # Receive response
                    response = await websocket.recv()
                    response_data = json.loads(response)
                    print(f"Server: {response_data['text']}")
                
                elif choice == "3":
                    print("Exiting...")
                    return
            
            # Get analysis result
            print("\nOnce analysis is complete, you can ask questions about the project")
            while True:
                question = input("\nEnter your question (or 'exit' to quit): ")
                
                if question.lower() == "exit":
                    break
                
                message = {
                    "type": "message",
                    "text": question
                }
                await websocket.send(json.dumps(message))
                print(f"You: {message['text']}")
                
                # Wait for thinking status
                thinking = await websocket.recv()
                thinking_data = json.loads(thinking)
                if thinking_data.get("message_type") == "thinking":
                    print("Server: Thinking...")
                
                # Receive response
                response = await websocket.recv()
                response_data = json.loads(response)
                print(f"Server: {response_data['text']}")

if __name__ == "__main__":
    asyncio.run(interact_with_api())
