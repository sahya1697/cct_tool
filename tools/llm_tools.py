"""
LangChain-wrapped Ollama LLM helpers.
All LLM calls in the project must go through these wrappers.

Includes deterministic settings and response caching for reproducibility.
"""

from __future__ import annotations

import time
import logging
from typing import Optional

from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

import config
from tools.llm_cache import get_cache_key, get_cached_response, cache_response

logger = logging.getLogger(__name__)


def _build_llm(model: str, temperature: float = config.LLM_TEMPERATURE) -> OllamaLLM:
    """
    Build Ollama LLM with deterministic settings.
    
    Deterministic parameters:
    - temperature=0.0: No randomness in token selection
    - top_k=1: Only consider the single most likely token
    - top_p=1.0: Disable nucleus sampling
    - repeat_penalty=1.0: No penalty variance
    - seed: Fixed random seed (if supported)
    """
    params = {
        "base_url": config.OLLAMA_HOST,
        "model": model,
        "temperature": temperature,
        "num_predict": config.LLM_MAX_TOKENS,
        "top_k": config.LLM_TOP_K,
        "top_p": config.LLM_TOP_P,
        "repeat_penalty": config.LLM_REPEAT_PENALTY,
    }
    
    # Add seed if configured (requires Ollama 0.2.0+)
    if config.LLM_SEED is not None:
        params["seed"] = config.LLM_SEED
    
    return OllamaLLM(**params)


def get_primary_llm() -> OllamaLLM:
    """Return the primary reasoning LLM."""
    return _build_llm(config.PRIMARY_MODEL)


def get_light_llm() -> OllamaLLM:
    """Return the lighter model for simple/filtering tasks."""
    return _build_llm(config.LIGHT_MODEL)


def llm_invoke(
    prompt_template: str,
    variables: dict,
    model: str = config.PRIMARY_MODEL,
    retries: int = config.LLM_RETRY_ATTEMPTS,
    delay: float = config.LLM_RETRY_DELAY,
) -> str:
    """
    Invoke an LLM with retry handling and optional caching.

    Args:
        prompt_template: A string with {variable} placeholders.
        variables:        Values to fill into the template.
        model:            Ollama model name.
        retries:          Number of retry attempts on failure.
        delay:            Seconds to wait between retries.

    Returns:
        The LLM's text response.
    """
    # Check cache first
    cache_key = get_cache_key(prompt_template, variables, model)
    cached = get_cached_response(cache_key)
    if cached is not None:
        logger.debug("Using cached LLM response")
        return cached
    
    # Cache miss - call LLM
    llm = _build_llm(model)
    template = PromptTemplate.from_template(prompt_template)
    chain = template | llm | StrOutputParser()

    last_exc: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            result: str = chain.invoke(variables)
            result_stripped = result.strip()
            
            # Cache successful response
            cache_response(cache_key, result_stripped)
            
            return result_stripped
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            logger.warning(
                "LLM call failed (attempt %d/%d): %s", attempt, retries, exc
            )
            if attempt < retries:
                time.sleep(delay)

    raise RuntimeError(
        f"LLM call failed after {retries} attempts"
    ) from last_exc
