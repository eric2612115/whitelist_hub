# Whitelist Hub

An automated blockchain project analysis platform focused on identifying, categorizing, and explaining smart contract functionality, with a particular emphasis on whitelist mechanisms.

## Features

- Automated smart contract discovery and analysis
- Whitelist mechanism detection and classification
- Contract function categorization
- Proxy contract detection
- User interaction flow generation
- Security assessment
- Advanced AI agent framework based on CrewAI for collaborative analysis
- **Multi-model AI support** (Anthropic Claude, Google Gemini, Google Vertex)
- **Advanced web crawling** with Firecrawl.dev integration
- **MongoDB integration** for persistent data storage
- **FastAPI-based backend** with WebSockets for real-time analysis updates

## Architecture

The system is built with a modular architecture based on CrewAI:

- AI Agent Framework with specialized crew members:
  - **Coordinator Agent**: Leads the analysis workflow and assigns tasks
  - **Crawler Agent**: Gathers project information from various sources using Firecrawl
  - **Analysis Agent**: Performs technical analysis of smart contracts
  - **Verification Agent**: Validates and enhances analysis results

- Core Services:
  - **MongoDB Service**: Manages database interactions for persistent storage
  - **Blockchain Client**: Handles blockchain interactions
  - **AI Client**: Manages communication with AI models (Claude, Gemini, Vertex)
  - **Prompt Manager**: Handles prompts with version control
  - **Firecrawl Client**: Advanced web crawling and data extraction

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Poetry for dependency management
- Access to AI model APIs (at least one of the following):
  - Anthropic Claude API
  - Google Gemini API
  - Google Vertex API
- Firecrawl.dev API key for enhanced web crawling
- MongoDB instance (local or remote)
- (Optional) Redis for caching and task queue
- (Optional) Access to blockchain node RPC endpoints

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/whitelist_hub.git
   cd whitelist_hub
   ```

2. Install dependencies with Poetry:
   ```
   poetry install
   ```

3. Set up environment variables (create a `.env` file):
   ```
   # AI API Keys (at least one is required)
   ANTHROPIC_API_KEY=your_anthropic_api_key
   GEMINI_API_KEY=your_gemini_api_key
   AI_MODEL_PROVIDER=anthropic  # or gemini, vertex
   
   # External services
   FIRECRAWL_API_KEY=your_firecrawl_api_key
   
   # MongoDB connection
   MONGODB_URL=mongodb://localhost:27017
   MONGODB_DB_NAME=whitelist_hub
   
   # Optional: Redis configuration (for caching/queue)
   REDIS_HOST=localhost
   REDIS_PORT=6379
   
   # Blockchain RPC URLs (optional)
   ETHEREUM_RPC_URL=https://mainnet.infura.io/v3/your_key
   BSC_RPC_URL=https://bsc-dataseed.binance.org/
   POLYGON_RPC_URL=https://polygon-rpc.com/
   ```

### Using Google Gemini

To use Google Gemini as your AI model provider:

1. Set the following in your `.env` file:
   ```
   GEMINI_API_KEY=your_gemini_api_key
   AI_MODEL_PROVIDER=gemini
   ```

2. Run the example script to test Gemini integration:
   ```
   poetry run python gemini_example.py
   ```

3. Default models:
   - The system uses `gemini-2.0-flash-001` as the default model for standard analysis tasks
   - You can specify different models by configuring them in your prompts or API calls

Google Gemini offers excellent capabilities for code analysis and whitelist mechanism detection, with fast response times and strong technical understanding of blockchain concepts.

### Usage

#### API Server

Start the API server:

```
poetry run python app.py
```

The API will be available at http://localhost:8000

API Documentation is available at http://localhost:8000/docs

#### Interactive Analysis through API

The API provides interactive project analysis through both REST API and WebSockets:

1. Create a session:
   ```
   POST /api/sessions
   ```

2. Start a project analysis:
   ```
   POST /api/sessions/{session_id}/projects
   {
     "project_name": "AAVE",
     "website": "https://aave.com",
     "github_url": "https://github.com/aave"
   }
   ```

3. Send messages to interact with the analysis:
   ```
   POST /api/sessions/{session_id}/messages
   {
     "text": "Tell me about the whitelist mechanisms in this project"
   }
   ```

4. Connect via WebSocket for real-time updates:
   ```
   ws://localhost:8000/ws/{session_id}
   ```

The results will be saved in the MongoDB database and in the `output/` directory with the following files:
- `Project Name_analysis_result.json`: Final analysis results
- `Project Name_crawl_log.json`: Log of the crawling process
- `Project Name_plan_log.json`: Analysis plan created by the coordinator
- `Project Name_synthesis_log.json`: Log of the final synthesis process
- `{blockchain}_{address}_analysis_log.json`: Individual contract analysis logs
- `{blockchain}_{address}_verification_log.json`: Verification logs for contract analysis

## Project Structure

```
whitelist_hub/
├── whitelist_hub/            # Main package
│   ├── agents/               # AI agent framework
│   │   ├── crawler/          # Crawler agent components
│   │   ├── analyzer/         # Analysis agent components
│   │   ├── base_crew.py      # Base crew implementation
│   │   ├── coordinator.py    # Coordinator agent
│   │   ├── verification.py   # Verification agent
│   │   └── crew_factory.py   # Factory for creating agent crews
│   ├── api/                  # API endpoints
│   │   ├── api.py            # Main API implementation
│   │   ├── connection_manager.py # WebSocket connection manager
│   │   └── project_analysis_service.py # Analysis service
│   ├── core/                 # Core functionality
│   │   └── config/           # Configuration
│   ├── db/                   # Database integration
│   │   └── mongodb.py        # MongoDB client implementation
│   ├── models/               # Data models
│   ├── prompts/              # Prompt templates
│   │   └── templates/        # Prompt template files
│   ├── services/             # External services
│   │   └── defillama_service.py # DeFiLlama integration
│   └── utils/                # Utility functions
│       ├── ai_client.py      # AI model client
│       ├── blockchain_client.py # Blockchain client
│       ├── firecrawl_client.py # Firecrawl client
│       └── prompt_utils.py   # Prompt utilities
├── tests/                    # Test suite
├── main.py                   # Entry point
├── app.py                    # FastAPI server
├── gemini_example.py         # Google Gemini example script
├── pyproject.toml            # Poetry configuration
└── README.md                 # This file
```

## Key Differences from Previous Version

- Replaced LangChain with CrewAI for improved agent collaboration
- Focused on Anthropic Claude, Google Gemini, and Google Vertex as the primary LLM providers
- Direct integration with MongoDB instead of using langchain-mongodb
- Enhanced real-time analysis through WebSockets
- Simplified dependency management with fewer version conflicts
- Restructured agent architecture to follow CrewAI's crew-based approach

## AI Model Comparison

The system supports multiple AI models, each with different strengths:

### Google Gemini
- **Strengths**: Fast code analysis, excellent technical understanding of blockchain concepts, cost-effective for large-scale analysis
- **Best for**: Rapid contract analysis, detecting complex whitelist patterns
- **Default model**: gemini-2.0-flash-001 (fast analysis with good accuracy)
- **Alternative models**: gemini-2.0-pro-001 (deeper analysis with higher accuracy)

### Anthropic Claude
- **Strengths**: Detailed explanations, nuanced understanding of contract interactions, excellent reasoning
- **Best for**: In-depth security analysis, complex pattern detection
- **Default model**: claude-3-opus-20240229 (comprehensive analysis with high accuracy)
- **Alternative models**: claude-3-haiku-20240307 (faster analysis with reasonable accuracy)

### Model Selection
You can switch between models by changing the `AI_MODEL_PROVIDER` environment variable. The system will use the specified provider for all analyses. For specific tasks requiring a different provider, you can create a custom `AIClient` instance with the desired provider.

## Extending the System

### Creating New Agent Types

1. Define a new agent class in the appropriate directory
2. Update the crew factory to include your new agent type
3. Configure the agent's tasks and responsibilities in the main crew

### Adding New AI Models

1. Update the AIClient class to support the new model
2. Add the necessary configuration to settings.py
3. Implement the appropriate client methods

### Adding New External Services

1. Create a new client class for the service
2. Implement the necessary API methods
3. Update the relevant agent to use the new service

### Adding New Prompt Templates

1. Create new template files in `prompts/templates/`
2. Register templates in the PromptManager

### Supporting New Blockchains

1. Add new RPC URLs in the configuration
2. Update blockchain client to support the new chain

## License

This project is licensed under the MIT License - see the LICENSE file for details.
