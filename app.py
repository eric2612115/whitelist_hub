"""Main entry point for Whitelist Hub API."""

import uvicorn
import logging
from whitelist_hub.api.api import app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("whitelist_hub_api.log"),
        logging.StreamHandler()
    ]
)

if __name__ == "__main__":
    # Run the server
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
