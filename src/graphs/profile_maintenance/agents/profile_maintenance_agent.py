from typing import Any, Dict, List, Optional, Tuple
import json
import re
from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage, AIMessage, ToolMessage
from pydantic import BaseModel, Field
from src.settings.config_store import config_store
from src.shared.reasoning_chat_openai import ReasoningChatOpenAI
from src.tools.mcp_tool_factory import MCPToolFactory

class ProfileMaintenanceAgent:
    """
    The core logic of the profile maintenance agent.
    """

    PROMPT_PATH = Path(__file__).with_name("profile_maintenance_systemprompt.md")

    def __init__(self, tool_factory: MCPToolFactory):
        self.tool_factory = tool_factory
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

    async def run(self, messages: list, clients: Dict[str, Any]) -> Tuple[BaseMessage, Dict[str, Any]]:
        """
        Executes the agent logic on a list of messages with dynamic tools.
        Returns a tuple of (result_message, token_usage_dict).
        """
        try:
            # 1. Discover tools from clients
            tools = await self.tool_factory.create_tools(clients)
            
            # 2. Bind tools to the LLM
            model = self.llm.bind_tools(tools)

            full_messages = []
            if self.system_prompt:
                full_messages.append(SystemMessage(content=self.system_prompt))
            full_messages.extend(messages)

            # 3. Execute agent loop
            response = await model.ainvoke(full_messages)
            
            tools_by_name = {tool.name: tool for tool in tools}
            
            tool_iterations = 0
            while response.tool_calls and tool_iterations < 10:
                tool_iterations += 1
                tool_messages = []
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    tool_call_id = tool_call["id"]
                    
                    tool = tools_by_name.get(tool_name)
                    if tool:
                        try:
                            result = await tool.ainvoke(tool_args)
                            tool_messages.append(ToolMessage(content=str(result), tool_call_id=tool_call_id))
                        except Exception as e:
                            tool_messages.append(ToolMessage(content=f"Error: {str(e)}", tool_call_id=tool_call_id))
                    else:
                        tool_messages.append(ToolMessage(content=f"Tool {tool_name} not found.", tool_call_id=tool_call_id))
                
                full_messages.append(response)
                full_messages.extend(tool_messages)
                response = await model.ainvoke(full_messages)

            usage = response.response_metadata.get("token_usage", {})

            return response, usage

        except Exception as e:
            raise e
