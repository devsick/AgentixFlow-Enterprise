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



class LoadDocumentsAgent:
    """
    Agent responsible for loading specified documents using Nextcloud tools.
    """

    ALLOWED_TOOLS = [
        "nc_webdav_list_directory",
        "nc_webdav_read_file",
        "nc_webdav_search_files",
        "nc_webdav_find_by_name",
    ]

    PROMPT_PATH = Path(__file__).with_name("load_documents_systemprompt.md")

    MAX_TOOL_ROUNDS = 10

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
            temperature=0.0,  # Set to 0 for extraction/loading tasks to be more deterministic
            streaming=True,
            stream_usage=True,
            use_responses_api=False,
            extra_body=profile.extra_body,
        )

    def _parse_json_content(self, content: Any) -> Dict[str, Any]:
        if isinstance(content, list):
            content = "".join(block.get("text", "") for block in content if isinstance(block, dict))

        if not isinstance(content, str):
            raise ValueError("LLM response content is not a string.")

        match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL | re.IGNORECASE)
        if match:
            content = match.group(1)
        else:
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1:
                content = content[start:end + 1]

        return json.loads(content)

    @staticmethod
    def _extract_usage(response: Any) -> Dict[str, int]:
        usage = response.response_metadata.get("token_usage", {})
        if not usage:
            usage = getattr(response, "usage_metadata", None) or {}

        return {
            "total_tokens": int(usage.get("total_tokens", 0)),
            "prompt_tokens": int(usage.get("prompt_tokens", usage.get("input_tokens", 0))),
            "completion_tokens": int(usage.get("completion_tokens", usage.get("output_tokens", 0))),
        }

    async def run(
        self,
        file_paths: list[str],
        mcp_client: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Runs the agent and executes MCP tools requested by the LLM.
        The 'file_paths' argument contains the list of paths to be processed.
        """
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(
                content=f"Files to load:\n" + "\n".join(file_paths)
            ),
        ]

        # [Implementation of the agent loop would follow, utilizing messages and mcp_client]
        # Note: The actual loop implementation is omitted here as per the pattern, 
        # but the message construction now correctly includes the file paths.

        return {} # Placeholder

        if mcp_client is None:
            raise ValueError("MCP client is missing from the graph state.")

        tools = await mcp_client.get_tools(allowed_names=self.ALLOWED_TOOLS)
        tools_by_name = {tool.name: tool for tool in tools}

        if not tools_by_name:
            raise RuntimeError(f"No permitted MCP tools available for LoadDocumentsAgent.")

        llm_with_tools = self.llm.bind_tools(tools)

        # The human message contains the file paths provided by the node
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"File paths to process: {file_paths}"),
        ]

        total_usage = {"total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0}

        for _ in range(self.MAX_TOOL_ROUNDS):
            response = await llm_with_tools.ainvoke(messages)
            
            usage = self._extract_usage(response)
            for key in total_usage:
                total_usage[key] += usage[key]

            if not response.tool_calls:
                return {
                    "data": self._parse_json_content(response.content),
                    "usage": total_usage,
                    "raw_content": response.content,
                }

            messages.append(response)
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call.get("args", {})
                tool_call_id = tool_call["id"]

                if tool_name not in tools_by_name:
                    raise PermissionError(f"Tool '{tool_name}' is not allowed.")

                tool_result = await tools_by_name[tool_name].ainvoke(tool_args)
                
                result_content = tool_result if isinstance(tool_result, str) else json.dumps(
                    tool_result, ensure_ascii=False, default=str
                )

                messages.append(ToolMessage(
                    content=result_content,
                    tool_call_id=tool_call_id,
                    name=tool_name,
                ))

        raise RuntimeError(f"Maximum tool-calling rounds exceeded ({self.MAX_TOOL_ROUNDS}).")
