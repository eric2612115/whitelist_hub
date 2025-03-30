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

## Getting Started

### Prerequisites

- Python 3.9 or higher
- Poetry for dependency management
- Access to OpenAI API or Anthropic Claude API
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
   # AI API Keys
   OPENAI_API_KEY=your_openai_api_key
   ANTHROPIC_API_KEY=your_anthropic_api_key
   
   # Blockchain RPC URLs (optional)
   ETHEREUM_RPC_URL=https://mainnet.infura.io/v3/your_key
   BSC_RPC_URL=https://bsc-dataseed.binance.org/
   POLYGON_RPC_URL=https://polygon-rpc.com/
   ```

### Usage

Run the analysis from the command line:

```
poetry run python main.py "Project Name" --website "https://project-website.com" --github "https://github.com/project/repo"
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
│   │   ├── base_agent.py     # Base agent implementation
│   │   ├── coordinator_agent.py # Coordinator agent
│   │   ├── analysis_agent.py # Analysis agent
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
│       └── blockchain_client.py # Blockchain client
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

### Adding New Prompt Templates

1. Create new template files in `prompts/templates/`
2. Register templates in the PromptManager

### Supporting New Blockchains

1. Add new RPC URLs in the configuration
2. Update blockchain client to support the new chain

## License

This project is licensed under the MIT License - see the LICENSE file for details.
