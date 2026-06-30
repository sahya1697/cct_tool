"""
LLM Response Caching for Deterministic Outputs.

Caches LLM responses based on prompt content to ensure:
1. Identical inputs always return identical outputs
2. Faster execution (no redundant LLM calls)
3. Cost savings (reduced API usage)
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import Optional

import config

logger = logging.getLogger(__name__)

# Create cache directory
CACHE_DIR = Path(config.LLM_CACHE_DIR)
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def normalize_text(text: str) -> str:
    """
    Normalize text for consistent caching.
    
    Removes extra whitespace and normalizes line endings
    to prevent cache misses from formatting differences.
    """
    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    
    # Remove leading/trailing whitespace per line
    lines = [line.rstrip() for line in text.split("\n")]
    
    # Remove empty leading/trailing lines
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    
    return "\n".join(lines)


def get_cache_key(prompt: str, variables: dict, model: str) -> str:
    """
    Generate deterministic cache key from inputs.
    
    Args:
        prompt: Prompt template string
        variables: Dictionary of variables to fill into template
        model: Model name
    
    Returns:
        SHA256 hash of normalized inputs
    """
    # Normalize all text variables
    normalized_vars = {}
    for key, value in variables.items():
        if isinstance(value, str):
            normalized_vars[key] = normalize_text(value)
        else:
            normalized_vars[key] = value
    
    # Create deterministic representation
    content = json.dumps(
        {
            "prompt": normalize_text(prompt),
            "variables": normalized_vars,
            "model": model,
        },
        sort_keys=True,
        ensure_ascii=True,
    )
    
    # Generate hash
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def get_cached_response(cache_key: str) -> Optional[str]:
    """
    Retrieve cached LLM response if available.
    
    Args:
        cache_key: Cache key from get_cache_key()
    
    Returns:
        Cached response text or None if not found
    """
    if not config.USE_LLM_CACHE:
        return None
    
    cache_file = CACHE_DIR / f"{cache_key}.txt"
    
    if cache_file.exists():
        try:
            response = cache_file.read_text(encoding="utf-8")
            logger.debug("Cache HIT: %s", cache_key[:16])
            return response
        except Exception as exc:
            logger.warning("Failed to read cache file %s: %s", cache_key[:16], exc)
            return None
    
    logger.debug("Cache MISS: %s", cache_key[:16])
    return None


def cache_response(cache_key: str, response: str) -> None:
    """
    Store LLM response in cache.
    
    Args:
        cache_key: Cache key from get_cache_key()
        response: LLM response text to cache
    """
    if not config.USE_LLM_CACHE:
        return
    
    cache_file = CACHE_DIR / f"{cache_key}.txt"
    
    try:
        cache_file.write_text(response, encoding="utf-8")
        logger.debug("Cached response: %s", cache_key[:16])
    except Exception as exc:
        logger.warning("Failed to write cache file %s: %s", cache_key[:16], exc)


def clear_cache() -> int:
    """
    Clear all cached LLM responses.
    
    Returns:
        Number of cache files deleted
    """
    if not CACHE_DIR.exists():
        return 0
    
    count = 0
    for cache_file in CACHE_DIR.glob("*.txt"):
        try:
            cache_file.unlink()
            count += 1
        except Exception as exc:
            logger.warning("Failed to delete cache file %s: %s", cache_file.name, exc)
    
    logger.info("Cleared %d cached responses", count)
    return count


def get_cache_stats() -> dict:
    """
    Get cache statistics.
    
    Returns:
        Dictionary with cache stats:
        - enabled: Whether caching is enabled
        - cache_dir: Cache directory path
        - cached_files: Number of cached responses
        - total_size_bytes: Total cache size in bytes
    """
    if not CACHE_DIR.exists():
        return {
            "enabled": config.USE_LLM_CACHE,
            "cache_dir": str(CACHE_DIR),
            "cached_files": 0,
            "total_size_bytes": 0,
        }
    
    cache_files = list(CACHE_DIR.glob("*.txt"))
    total_size = sum(f.stat().st_size for f in cache_files)
    
    return {
        "enabled": config.USE_LLM_CACHE,
        "cache_dir": str(CACHE_DIR),
        "cached_files": len(cache_files),
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / (1024 * 1024), 2),
    }
