"""OpenRouter API client for making LLM requests."""

import asyncio
import logging
import time
import httpx
from typing import List, Dict, Any, Optional
from .config import OPENROUTER_API_KEY, OPENROUTER_API_URL

logger = logging.getLogger(__name__)

# Global semaphore to limit concurrent requests to OpenRouter (prevents 429 rate limits)
OPENROUTER_SEMAPHORE = asyncio.Semaphore(3)


async def query_model(
    model: str,
    messages: List[Dict[str, Any]],
    timeout: float = 30.0
) -> Optional[Dict[str, Any]]:
    """
    Query a single model via OpenRouter API.

    Args:
        model: OpenRouter model identifier (e.g., "openai/gpt-4o")
        messages: List of message dicts with 'role' and 'content'
        timeout: Request timeout in seconds

    Returns:
        Response dict with 'content' and optional 'reasoning_details', or None if failed
    """
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": messages,
    }

    start = time.perf_counter()
    try:
        async with OPENROUTER_SEMAPHORE:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    OPENROUTER_API_URL,
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()

                data = response.json()
                message = data['choices'][0]['message']

                logger.info("query_model model=%s ok in %.2fs", model, time.perf_counter() - start)
                return {
                    'content': message.get('content'),
                    'reasoning_details': message.get('reasoning_details')
                }

    except httpx.HTTPStatusError as e:
        logger.error(
            "query_model model=%s failed after %.2fs: HTTP %s",
            model, time.perf_counter() - start, e.response.status_code
        )
        return None
    except httpx.TimeoutException:
        logger.error("query_model model=%s timed out after %.2fs", model, time.perf_counter() - start)
        return None
    except Exception as e:
        logger.error("query_model model=%s failed after %.2fs: %s", model, time.perf_counter() - start, e)
        return None


async def query_models_parallel(
    models: List[str],
    messages: List[Dict[str, str]]
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Query multiple models in parallel.

    Args:
        models: List of OpenRouter model identifiers
        messages: List of message dicts to send to each model

    Returns:
        Dict mapping model identifier to response dict (or None if failed)
    """
    import asyncio

    # Create tasks for all models
    tasks = [query_model(model, messages) for model in models]

    # Wait for all to complete
    responses = await asyncio.gather(*tasks)

    # Map models to their responses
    return {model: response for model, response in zip(models, responses)}
