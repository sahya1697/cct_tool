"""
MongoDB tools for loading MISRA rules from database with JSON fallback.
"""

from __future__ import annotations

import logging
from typing import Optional

import config

logger = logging.getLogger(__name__)

_mongo_client: Optional[object] = None


def get_mongo_client():
    """Get or create MongoDB client singleton."""
    global _mongo_client
    
    if _mongo_client is not None:
        return _mongo_client
    
    try:
        from pymongo import MongoClient
        from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
        
        # Create client with short timeout for fast failure
        _mongo_client = MongoClient(
            config.MONGO_URI,
            serverSelectionTimeoutMS=3000,  # 3 second timeout
            connectTimeoutMS=3000,
            socketTimeoutMS=5000,
        )
        
        # Test connection
        _mongo_client.admin.command('ping')
        logger.info("MongoDB connected: %s", config.MONGO_URI)
        return _mongo_client
        
    except ImportError:
        logger.info("pymongo not installed, using JSON fallback. Install with: pip install pymongo")
        _mongo_client = None
        return None
        
    except (ConnectionFailure, ServerSelectionTimeoutError) as exc:
        logger.info("MongoDB unavailable, using JSON fallback: %s", exc)
        _mongo_client = None
        return None
        
    except Exception as exc:
        logger.warning("MongoDB connection error, using JSON fallback: %s", exc)
        _mongo_client = None
        return None


def load_rules_from_mongo() -> Optional[list[dict]]:
    """
    Load rules from MongoDB.
    
    Returns:
        List of rule dictionaries, or None if MongoDB is unavailable.
    """
    client = get_mongo_client()
    if client is None:
        return None
    
    try:
        db = client[config.MONGO_DB]
        collection = db[config.MONGO_RULES_COLLECTION]
        
        # Load all rules
        rules = list(collection.find({}, {"_id": 0}))  # Exclude MongoDB _id field
        
        if not rules:
            logger.warning("No rules found in MongoDB collection: %s.%s", 
                         config.MONGO_DB, config.MONGO_RULES_COLLECTION)
            return None
        
        logger.info("Loaded %d rules from MongoDB (%s.%s)", 
                   len(rules), config.MONGO_DB, config.MONGO_RULES_COLLECTION)
        return rules
        
    except Exception as exc:
        logger.warning("Failed to load rules from MongoDB: %s", exc)
        return None


def close_mongo_connection() -> None:
    """Close MongoDB connection."""
    global _mongo_client
    
    if _mongo_client is not None:
        try:
            _mongo_client.close()
            logger.info("MongoDB connection closed")
        except Exception as exc:
            logger.warning("Error closing MongoDB connection: %s", exc)
        finally:
            _mongo_client = None
