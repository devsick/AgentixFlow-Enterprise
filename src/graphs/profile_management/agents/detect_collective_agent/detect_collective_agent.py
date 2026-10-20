from typing import Any, Dict, Optional
import json
import re

from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
    ToolMessage,
    AIMessage,
)

from src.settings.config_store import config_store
from src.shared.reasoning_chat_openai import ReasoningChatOpenAI
from pathlib import Path






class DetectCollectiveAgent:
    """
    Identifies the target collective.

    Only tools included in ALLOWED_TOOLS can be made available
    to this agent. The MCP client also enforces global permissions.
    """

    ALLOWED_TOOLS = [
        "collectives_get_collectives",
        "collectives_get_pages",
        "collectives_get_page",
        "collectives_search_pages",
        "collectives_create_collective",
        "collectives_create_page",
    ]

    PROMPT_PATH = Path(__file__).with_name("detect_collective_systemprompt.md")

    MAX_TOOL_ROUNDS = 10

    def __init__(self):
        with self.PROMPT_PATH.open("r", encoding="utf-8") as f:
            self.system_prompt = f.read()
        self._init_llm()

    def _init_llm(self) -> None:
        profile = config_store.llm_profiles.get("oogabooga")

        if not profile:
            raise ValueError(
                "LLM Profile 'oogabooga' not found in configuration."
            )

        LLMClass = (
            ReasoningChatOpenAI
            if getattr(profile, "type", None) == "reasoning"
            else ChatOpenAI
        )

        self.llm = LLMClass(
            base_url=profile.url,
            api_key=profile.api_key,
            model=profile.model,
            temperature=0.7,
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
            raise ValueError(
                "LLM response content is not a string."
            )

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

        parsed = json.loads(content)

        if not isinstance(parsed, dict):
            raise ValueError(
                "Expected a JSON object in the LLM response."
            )

        return parsed

    @staticmethod
    def _extract_usage(response: Any) -> Dict[str, int]:
        """Normalizes token usage across model integrations."""

        usage = response.response_metadata.get("token_usage", {})

        if not usage:
            usage = getattr(response, "usage_metadata", None) or {}

        return {
            "total_tokens": int(usage.get("total_tokens", 0)),
            "prompt_tokens": int(
                usage.get("prompt_tokens", usage.get("input_tokens", 0))
            ),
            "completion_tokens": int(
                usage.get(
                    "completion_tokens",
                    usage.get("output_tokens", 0),
                )
            ),
        }

    async def run(
        self,
        last_message: str,
        mcp_client: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Runs the agent and executes MCP tools requested by the LLM.
        """
       
        if mcp_client is None:
            raise ValueError(
                "MCP client is missing from the graph state."
            )

        
        tools = await mcp_client.get_tools(
            allowed_names=self.ALLOWED_TOOLS
        )

        
        tools_by_name = {
            tool.name: tool for tool in tools
        }

        if not tools_by_name:
            raise RuntimeError(
                "No permitted MCP tools are available "
                "for DetectCollectiveAgent."
            )

        llm_with_tools = self.llm.bind_tools(tools,tool_choice="required")

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=last_message),
        ]

        total_usage = {
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
        }

        for _ in range(self.MAX_TOOL_ROUNDS):
            response = await llm_with_tools.ainvoke(messages)

                        
            usage = self._extract_usage(response)
             
            for key in total_usage:
                total_usage[key] += usage[key]

           
            # No tool calls means the model has returned its final answer.
            if not response.tool_calls:
                content_dict = self._parse_json_content(
                    response.content
                )

                return {
                    "data": content_dict,
                    "usage": total_usage,
                    "raw_content": response.content,
                }

            # Add the assistant message containing the tool calls.
            messages.append(response)

            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call.get("args", {})
                tool_call_id = tool_call["id"]

                # Do not execute tools outside this agent's allowlist.
                if tool_name not in tools_by_name:
                    raise PermissionError(
                        f"Tool '{tool_name}' is not allowed "
                        "for DetectCollectiveAgent."
                    )

                tool_result = await tools_by_name[tool_name].ainvoke(
                    tool_args
                )

                if isinstance(tool_result, str):
                    result_content = tool_result
                else:
                    result_content = json.dumps(
                        tool_result,
                        ensure_ascii=False,
                        default=str,
                    )

                messages.append(
                    ToolMessage(
                        content=result_content,
                        tool_call_id=tool_call_id,
                        name=tool_name,
                    )
                )

        raise RuntimeError(
            "Maximum number of tool-calling rounds exceeded "
            f"({self.MAX_TOOL_ROUNDS})."
        )
