# Whitelist Hub

An intelligent blockchain project analysis platform with a modular agent-based architecture, focused on identifying, categorizing, and explaining smart contract functionality, with a particular emphasis on whitelist mechanisms.

## Features

- **Modular Agent Framework** - Flexible and extensible agent architecture for blockchain analysis
- **Multi-model AI Support** - Integration with major AI providers (Gemini, Claude, OpenAI)
- **Real-time Analysis** - WebSocket support for real-time analysis updates
- **Workflow Engine** - Task-based workflows with dependency management
- **REST and WebSocket APIs** - Modern API design for integration with other systems
- **Self-healing Design** - Automatic recovery from failures and comprehensive error handling
- **Observability** - Event-based system for monitoring and telemetry

## Architecture

The system is built with a modular architecture based on specialized AI agents:

- **Agent Framework**:
  - **Agent Base** - Abstract interface for all agents with common functionality
  - **LLM Agent** - Base implementation for language model integration
  - **Coordinator Agent** - Plans and orchestrates the analysis workflow
  - **Crawler Agent** - Gathers project information from various sources
  - **Analyzer Agent** - Examines contract code and identifies whitelist mechanisms
  - **Verifier Agent** - Validates and cross-checks analysis results

- **Core Services**:
  - **Context Management** - Maintains state and messaging between agents
  - **Task Management** - Tracks task execution and dependencies
  - **Workflow Engine** - Orchestrates complex multi-agent workflows
  - **Event System** - Provides observability and tracking

- **API Layer**:
  - **REST API** - For command-driven interactions
  - **WebSocket API** - For real-time analysis updates
  - **Session Management** - For persistent analysis sessions

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Poetry for dependency management
- Access to AI model APIs (at least one of the following):
  - Google Gemini API key
  - Anthropic Claude API key
  - OpenAI API key

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

3. Create a `.env` file with your API keys:
   ```
   GEMINI_API_KEY=your_gemini_api_key
   ANTHROPIC_API_KEY=your_anthropic_api_key
   OPENAI_API_KEY=your_openai_api_key
   ```

### Basic Usage

#### Simple Command-line Interface

Try the simple CLI application to experiment with the agents:

```bash
poetry run python simple_app.py
```

This interactive application allows you to:
- Analyze blockchain projects
- Analyze individual smart contracts
- Chat directly with coordinator or analyzer agents

#### API Server

Run the API server for web-based access:

```bash
poetry run python app.py
```

This starts a FastAPI server on http://localhost:8000 with:
- API documentation at http://localhost:8000/docs
- REST endpoints for analysis sessions
- WebSocket endpoint for real-time updates

#### Command-line Analysis

Analyze a project directly from the command line:

```bash
poetry run python main.py --project "Aave" --website "https://aave.com" --github "https://github.com/aave"
```

Analyze a specific contract:

```bash
poetry run python main.py --contract "0x7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9" --blockchain "ethereum"
```

## Project Structure

```
whitelist_hub/
├── agent_framework/       # Core agent system
│   ├── agent.py           # Base Agent definition
│   ├── context.py         # Execution context model
│   ├── registry.py        # Agent registration system
│   ├── task.py            # Task definition and tracking
│   ├── tools.py           # Tool system for agents
│   ├── workflow.py        # Workflow orchestration
│   └── agents/            # Specific agent implementations
│       ├── llm_agent.py           # LLM integration
│       ├── coordinator_agent.py   # Analysis coordination
│       ├── crawler_agent.py       # Data gathering
│       ├── analyzer_agent.py      # Contract analysis
│       └── verifier_agent.py      # Results verification
├── api/                   # API layer
│   ├── api.py             # FastAPI implementation
│   ├── connection_manager.py  # WebSocket management
│   └── session_manager.py     # Analysis session management
├── services/              # External service integrations
│   └── ai_client.py       # AI model provider integration
├── utils/                 # Utility modules
│   ├── exceptions.py      # Custom exceptions
│   ├── observability.py   # Event tracking and telemetry
│   └── retryable.py       # Retry logic and fault tolerance
├── workflows/             # Predefined workflows
│   └── project_analysis_workflow.py  # Project analysis configuration
├── app.py                 # API server entry point
├── main.py                # CLI entry point
└── simple_app.py          # Interactive example application
```

## AI Model Comparison

The system supports multiple AI models, each with different strengths:

### Google Gemini
- **Strengths**: Fast code analysis, excellent technical understanding of blockchain concepts
- **Best for**: Rapid contract analysis, detecting complex whitelist patterns
- **Default model**: gemini-2.0-pro-001 (good balance of speed and accuracy)

### Anthropic Claude
- **Strengths**: Detailed explanations, nuanced understanding of contract interactions
- **Best for**: In-depth security analysis, complex pattern detection
- **Default model**: claude-3-opus-20240229 (high accuracy) and claude-3-haiku-20240307 (faster responses)

### Model Selection
You can switch between models by setting the `--model` parameter when using the CLI or by choosing the model in the interactive app.

## Extending the System

### Creating New Agent Types

1. Create a new class that extends `LLMAgent` or directly from `Agent`
2. Register it with the `@register_agent` decorator
3. Add any specialized methods needed for your agent's functionality

Example:
```python
from whitelist_hub.agent_framework.agents.llm_agent import LLMAgent, LLMAgentConfig
from whitelist_hub.agent_framework.registry import register_agent

@register_agent("my_agent")
class MySpecialAgent(LLMAgent):
    # Agent implementation
```

### Creating Custom Tools

1. Create a new class that extends `Tool`
2. Register it with the `@register_tool` decorator
3. Implement the `execute` method

Example:
```python
from whitelist_hub.agent_framework.tools import Tool, register_tool

@register_tool
class MyCustomTool(Tool):
    name = "my_custom_tool"
    description = "Performs a specialized function"
    
    async def execute(self, parameters):
        # Tool implementation
```

### Creating Custom Workflows

Use the `WorkflowConfig` and `TaskConfig` classes to define new workflows:

```python
from whitelist_hub.agent_framework.workflow import Workflow, WorkflowConfig
from whitelist_hub.agent_framework.task import TaskConfig

workflow_config = WorkflowConfig(
    name="My Custom Workflow",
    description="Performs a specialized analysis",
    tasks=[
        TaskConfig(name="task1", agent_name="coordinator", ...),
        TaskConfig(name="task2", agent_name="analyzer", ...)
    ]
)

workflow = Workflow(config=workflow_config)
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
