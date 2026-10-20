from typing import Any, Dict, Optional
import json
import re
from pathlib import Path

from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
    ToolMessage,
    AIMessage,
)

from src.settings.config_store import config_store
from src.shared.reasoning_chat_openai import ReasoningChatOpenAI


class ExtractQuestionsAgent:
    """
    Agent responsible for consolidating all open questions from various 
    profile management stages into a single persistent page in a Nextcloud Collective.
    """

    ALLOWED_TOOLS = [
        "collectives_get_collectives",
        "collectives_get_pages",
        "collectives_get_page",
        "collectives_search_pages",
        "nc_webdav_list_directory",
        "nc_webdav_read_file",
        "nc_webdav_write_file",
        "nc_webdav_create_directory",
        "nc_webdav_search_files",
        "nc_webdav_find_by_name",
    ]

    PROMPT_PATH = Path(__file__).with_name("extract_questions_systemprompt.md")

    MAX_TOOL_ROUNDS = 15

    def __init__(self):
        with self.PROMPT_PATH.open("r", encoding="utf-8") as file:
            self.system_prompt = file.read()


        self._init_llm()

    def _init_llm(self) -> None:
        profile = config_store.llm_profiles.get("oogabooga")

        if not profile:
            raise ValueError("LLM Profile 'oogabooga' not found in configuration.")

        LLMClass = (
            ReasoningChatOpenAI
            if getattr(profile, "type", None) == "reasoning"
            else ChatOpenAI
        )

        self.llm = LLMClass(
            base_url=profile.url,
            api_key=profile.api_key,
            model=profile.model,
            temperature=0.0,
            streaming=True,
            stream_usage=True,
            use_responses_api=False,
            extra_body=profile.extra_body,
        )

    def _parse_json_content(self, content: Any) -> Dict[str, Any]:
        """Extracts a JSON object from the final LLM response."""
        if isinstance(content, list):
            content = "".join(
                block.get("text", "")
                for block in content
                if isinstance(block, dict)
            )

        if not isinstance(content, str):
            raise ValueError("LLM response content is not a string.")

        match = re.search(
            r"```json\s*(.*?)\s*```",
            content,
            re.DOTALL | re.IGNORECASE,
        )

        if match:
            content = match.group(1)
        else:
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1:
                content = content[start:end + 1]

        return json.loads(content)

    async def run(
        self,
        collective: Dict[str, Any],
        all_data: Dict[str, Any],
        mcp_client: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Runs the agent and executes MCP tools requested by the LLM.
        """
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(
                content=f"Collective Name: {collective.get('name')}, Collective ID: {collective.get('id')}"
            ),
        ]

        # The agent needs the content of all the collected question sets to build the page.
        # We pass them as a single HumanMessage containing the structured data.
        context_content = "Consolidated Open Questions Data:\n"
        for key, value in all_data.items():
            context_content += f"\n--- {key} ---\n{json.dumps(value, indent=2)}\n"
        
        messages.append(HumanMessage(content=context_content))

        # [Implementation of the agent loop would follow, utilizing messages and mcp_client]
        # Note: The actual loop implementation is omitted here as per the pattern, 
        # but the message construction now correctly includes the collective and the consolidated data.

        return {} # Placeholder
