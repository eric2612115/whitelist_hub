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

The system is built with a microservices architecture:

- Client-facing applications (Web interface, Telegram bot, Discord bot, API)
- API Gateway (FastAPI)
- Core Services (Project, Contract, Analysis, User services)
- AI Agent Framework (Crawler, Analysis, Verification, Coordination agents)
- Infrastructure (MongoDB, Redis, Celery, Blockchain nodes)

## Getting Started

### Prerequisites

- Python 3.9+
- Poetry for dependency management
- MongoDB
- Redis
- Access to blockchain nodes (Ethereum, etc.)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/whitelist_hub.git
cd whitelist_hub

# Install dependencies
poetry install

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run the development server
poetry run uvicorn app.main:app --reload
```

## License

[MIT](LICENSE)
