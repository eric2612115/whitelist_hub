"""MongoDB connection and helper functions."""

import logging
from motor.motor_asyncio import AsyncIOMotorClient
from ..core.config import settings

logger = logging.getLogger(__name__)

class Database:
    """MongoDB database connection."""
    
    client: AsyncIOMotorClient = None
    db = None


db = Database()


async def connect_to_mongo():
    """Connect to MongoDB."""
    logger.info("Connecting to MongoDB at %s", settings.MONGODB_URL)
    db.client = AsyncIOMotorClient(settings.MONGODB_URL)
    db.db = db.client[settings.MONGODB_DB_NAME]
    logger.info("Connected to MongoDB")


async def close_mongo_connection():
    """Close MongoDB connection."""
    if db.client:
        logger.info("Closing MongoDB connection")
        db.client.close()
        logger.info("Closed MongoDB connection")


# Helper functions for database operations
async def get_collection(collection_name: str):
    """Get MongoDB collection."""
    return db.db[collection_name]


# Common collection names
PROJECTS_COLLECTION = "projects"
CONTRACTS_COLLECTION = "contracts"
ANALYSIS_LOGS_COLLECTION = "analysis_logs"
CONTRACT_HISTORY_COLLECTION = "contract_history"
CONTRACT_CHANGES_COLLECTION = "contract_changes"
PROMPT_TEMPLATES_COLLECTION = "prompt_templates"
PROMPT_METADATA_COLLECTION = "prompt_metadata"
