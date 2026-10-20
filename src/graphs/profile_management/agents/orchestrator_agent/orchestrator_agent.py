from typing import Any, Dict, List, Optional, Tuple
import json
import re
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage
from pydantic import BaseModel, Field
from src.graphs.profile_management.state import ProfileManagementState
from src.settings.config_store import config_store
from src.shared.reasoning_chat_openai import ReasoningChatOpenAI
from langchain_openai import ChatOpenAI
from pathlib import Path



class OrchestratorExtraction(BaseModel):
    """
    Extracted parameters and decisions from user input.
    Matches the schema defined in orchestrator_agent_systemprompt.md.
    """
    intent: str = Field(description="The chosen flow name.")
    params: Dict[str, Any] = Field(description="Dictionary containing extracted parameters.")
    SystemMessage: str = Field(description="The orchestrator's response to the user.")
    summary_context: str = Field(description="A short summary of the context (should be empty per prompt).")

class OrchestratorAgent:
    """
    The core logic of the orchestrator agent.
    """

    PROMPT_PATH = Path(__file__).with_name("orchestrator_agent_systemprompt.md")

    def __init__(self):

        with self.PROMPT_PATH.open("r", encoding="utf-8") as file:
            self.system_prompt = file.read()
        

        self._init_llm()

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

    def _parse_json_content(self, content: str) -> Dict[str, Any]:
        """
        Extrahiert JSON aus dem Content, falls der LLM Markdown-Blocks nutzt.
        """
        json_match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
        if json_match:
            content = json_match.group(1)
        else:
            start = content.find('{')
            end = content.rfind('}')
            if start != -1 and end != -1:
                content = content[start:end+1]

        return json.loads(content)

    async def run(self, last_message: str) -> Tuple[OrchestratorExtraction, Dict[str, Any]]:
        """
        Executes the agent logic on a single message.
        Returns a tuple of (extracted_data, token_usage_dict).
        """
        try:
            message = await self.llm.ainvoke([
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=last_message)
            ])

            usage = message.response_metadata.get("token_usage", {})
            content_dict = self._parse_json_content(message.content)
            extraction = OrchestratorExtraction(**content_dict)

            return extraction, usage

        except Exception as e:
            raise e
