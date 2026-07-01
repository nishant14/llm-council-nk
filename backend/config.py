"""Configuration for the LLM Council."""

import os
from dotenv import load_dotenv

load_dotenv()

# OpenRouter API key
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Council members - list of OpenRouter model identifiers
# These models participate in:
# - Stage 1 (Initial Responses): Generating individual answers (optionally using STAGE1_PERSONA_SYSTEM_PROMPT in backend/prompts.py)
# - Stage 2 (Peer Rankings): Reviewing and ranking each other's answers (using STAGE2_STANDARD_RANKING_PROMPT or STAGE2_PERSONA_RANKING_PROMPT in backend/prompts.py)
COUNCIL_MODELS = [
    "google/gemini-2.5-flash",
    "meta-llama/llama-3.3-70b-instruct:free",
    "deepseek/deepseek-chat",
    "openai/gpt-4o-mini",
]

# Models a user can pick from for each persona on the Persona Council screen
# (GET /api/available-models). Distinct from COUNCIL_MODELS above, which is
# the smaller set actually queried by default in Standard mode - changing
# this list does not affect Standard mode's cost/behavior.
# Each entry's "tier" is a coarse OpenRouter pricing bucket (blended prompt+
# completion $/M tokens): low < $1, medium $1-$10, max > $10. Used to group
# the model dropdown into sections so users can see cost before picking.
PERSONA_MODEL_CHOICES = [
    # Claude
    {"id": "anthropic/claude-3-haiku", "tier": "low"},
    {"id": "anthropic/claude-haiku-4.5", "tier": "medium"},
    {"id": "anthropic/claude-sonnet-4.6", "tier": "medium"},
    {"id": "anthropic/claude-opus-4.8", "tier": "max"},
    # Gemini
    {"id": "google/gemini-2.5-flash-lite", "tier": "low"},
    {"id": "google/gemini-2.5-flash", "tier": "low"},
    {"id": "google/gemini-2.5-pro", "tier": "medium"},
    # OpenAI
    {"id": "openai/gpt-5-nano", "tier": "low"},
    {"id": "openai/gpt-5-mini", "tier": "low"},
    {"id": "openai/gpt-5.4", "tier": "medium"},
    {"id": "openai/o3-pro", "tier": "max"},
    # Qwen
    {"id": "qwen/qwen3-235b-a22b-2507", "tier": "low"},
    {"id": "qwen/qwen3-8b", "tier": "low"},
    {"id": "qwen/qwen3-max", "tier": "medium"},
    # Llama
    {"id": "meta-llama/llama-3.1-8b-instruct", "tier": "low"},
    {"id": "meta-llama/llama-3.3-70b-instruct", "tier": "low"},
    {"id": "nousresearch/hermes-3-llama-3.1-405b", "tier": "medium"},
]

# Chairman model - synthesizes final response
# This model participates in:
# - Stage 0 (Persona Suggestion): Analyzing queries to suggest expert perspectives (using PERSONA_SUGGESTION_PROMPT in backend/prompts.py)
# - Stage 3 (Final Synthesis): Synthesizing Stage 1 responses and Stage 2 rankings (using STAGE3_STANDARD_CHAIRMAN_PROMPT or STAGE3_PERSONA_CHAIRMAN_PROMPT in backend/prompts.py)
# - Title Generation: Creating a short title for the conversation (using CONVERSATION_TITLE_PROMPT in backend/prompts.py)
CHAIRMAN_MODEL = "google/gemini-2.5-flash"

# OpenRouter API endpoint
OPENROUTER_API_URL = os.getenv("OPENROUTER_API_URL", "https://openrouter.ai/api/v1/chat/completions")

# Data directory for conversation storage
DATA_DIR = "data/conversations"
