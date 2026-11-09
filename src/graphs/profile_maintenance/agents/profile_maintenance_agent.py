from typing import Any, Dict, List, Optional, Tuple
import json
import re
from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage
from pydantic import BaseModel, Field
from src.settings.config_store import config_store
from src.shared.reasoning_chat_openai import ReasoningChatOpenAI

ALLOWED_TOOLS = [
    "collectives_get_collectives",
    "collectives_get_pages",
    "collectives_get_page",
    "collectives_search_pages",
    "collectives_create_page",
    "nc_webdav_list_directory",
    "nc_webdav_read_file",
    "nc_webdav_write_file",
    "nc_webdav_create_directory",
    "nc_webdav_search_files",
    "nc_webdav_find_by_name",
]


class ProfileMaintenanceAgent:
    """
    The core logic of the profile maintenance agent.
    """

    PROMPT_PATH = Path(__file__).with_name("profile_maintenance_systemprompt.md")

    def __init__(self):
        with self.PROMPT_PATH.open("r", encoding="utf-8") as file:
            self.system_prompt = file.read()
        
        self._init_llm()
        self.tools = []

    def _init_llm(self):
        profile = config_store.llm_profiles.get("oogabooga")
        if not profile:
            raise ValueError("LLM Profile 'oogabooga' not found in configuration.")

        LLMClass = ReasoningChatOpenAI if getattr(profile, "type", None) == "reasoning" else ChatOpenAI

        self.llm = LLMClass(
            base_url=profile.url,
            api_key=profile.api_key,
            model=profile.model,
            temperature=0.7,
            streaming=True,
            stream_usage=True,
            use_responses_api=False,
            extra_body=profile.extra_body
        )

    async def set_tools(self, tools: list):
        """Setzt die Tools für den Agenten."""
        self.tools = tools
        self.llm = self.llm.bind_tools(tools)

    async def run(self, messages: list) -> Tuple[BaseMessage, Dict[str, Any]]:
        """
        Executes the agent logic on a list of messages.
        Returns a tuple of (result_message, token_usage_dict).
        """
        try:
            full_messages = []
            if self.system_prompt:
                full_messages.append(SystemMessage(content=self.system_prompt))
            full_messages.extend(messages)

            message = await self.llm.ainvoke(full_messages)
            usage = message.response_metadata.get("token_usage", {})

            return message, usage

        except Exception as e:
            raise e
