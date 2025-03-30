# Whitelist Hub

An automated blockchain project analysis platform focused on identifying, categorizing, and explaining smart contract functionality, with a particular emphasis on whitelist mechanisms.

## Features

- Automated smart contract discovery and analysis
- Whitelist mechanism detection and classification
- Contract function categorization
- Proxy contract detection
- User interaction flow generation
- Security assessment
- Advanced AI agent framework for comprehensive analysis
- **Multi-model AI support** (OpenAI, Anthropic Claude, Google Gemini)
- **Advanced web crawling** with Firecrawl.dev integration
- **Custom AI provider support** for specialized models

## Architecture

The system is built with a modular architecture:

- AI Agent Framework with specialized agents:
  - Coordinator Agent: Orchestrates the analysis workflow
  - Crawler Agent: Gathers project information from various sources
  - Analysis Agent: Performs technical analysis of contracts
  - Verification Agent: Validates and enhances analysis results

- Core Services:
  - DeFiLlama Service: Interfaces with DeFiLlama API
  - Blockchain Client: Handles blockchain interactions
  - AI Client: Manages communication with AI models
  - Prompt Manager: Handles prompts with version control
  - Firecrawl Client: Advanced web crawling and data extraction

## Getting Started

### Prerequisites

- Python 3.9 or higher
- Poetry for dependency management
- Access to AI model APIs (at least one of the following):
  - OpenAI API
  - Anthropic Claude API
  - Google Gemini API
  - Custom AI provider API
- (Optional) Firecrawl.dev API key for enhanced crawling
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
   OPENAI_API_KEY=your_openai_api_key
   ANTHROPIC_API_KEY=your_anthropic_api_key
   GEMINI_API_KEY=your_gemini_api_key
   AI_MODEL_PROVIDER=openai  # or anthropic, gemini, custom
   
   # External services (optional but recommended)
   FIRECRAWL_API_KEY=your_firecrawl_api_key
   
   # Blockchain RPC URLs (optional)
   ETHEREUM_RPC_URL=https://mainnet.infura.io/v3/your_key
   BSC_RPC_URL=https://bsc-dataseed.binance.org/
   POLYGON_RPC_URL=https://polygon-rpc.com/
   ```

### Usage

#### Command Line Interface

Run the analysis from the command line:

```
poetry run python main.py "Project Name" --website "https://project-website.com" --github "https://github.com/project/repo" --framework "auto"
```

Framework options:
- `custom` - Uses the custom agent implementation (default)
- `langchain` - Uses LangChain for all tasks
- `auto` - Automatically selects the best framework for each task

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

The results will be saved in the `output/` directory with the following files:
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
│   │   ├── base_agent.py     # Base agent implementation
│   │   ├── coordinator_agent.py # Coordinator agent
│   │   ├── verification_agent.py # Verification agent
│   │   └── agent_factory.py  # Factory for creating agents
│   ├── core/                 # Core functionality
│   │   └── config/           # Configuration
│   ├── models/               # Data models
│   ├── prompts/              # Prompt templates
│   │   └── templates/        # Prompt template files
│   ├── services/             # External services
│   │   └── defillama_service.py # DeFiLlama integration
│   └── utils/                # Utility functions
│       ├── ai_client.py      # AI model client
│       ├── blockchain_client.py # Blockchain client
│       ├── firecrawl_client.py # Firecrawl client
│       └── langchain_client.py # LangChain client
├── tests/                    # Test suite
├── main.py                   # Entry point
├── pyproject.toml            # Poetry configuration
└── README.md                 # This file
```

## Extending the System

### Adding New Agent Types

1. Create a new agent class inheriting from BaseAgent
2. Implement agent-specific methods and action handlers
3. Add the agent to the agent factory

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
