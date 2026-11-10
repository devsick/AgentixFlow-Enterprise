from langchain_core.messages import BaseMessage
from typing import Annotated, Any

# This file will contain the agent definition and its system prompt.
# It is intended to be generated or managed by the LLM.

SYSTEM_PROMPT = """You are an Anki specialist. Your goal is to help the user manage their Anki decks and cards effectively."""

# Placeholder for the agent logic
def get_agent_config():
    return {
        "system_prompt": SYSTEM_PROMPT,
        "model_settings": {}
    }
