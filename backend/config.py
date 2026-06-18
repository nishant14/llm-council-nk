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
