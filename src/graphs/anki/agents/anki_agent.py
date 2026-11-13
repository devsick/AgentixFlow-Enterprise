
from typing import Any, Dict, List, Optional
from pathlib import Path
import json

from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from src.settings.config_store import config_store
from src.shared.reasoning_chat_openai import ReasoningChatOpenAI
from src.tools.mcp_tool_factory import MCPToolFactory
import uuid


class AnkiAgent:
    """
    Agent responsible for Anki administration, research,
    knowledge management, and Anki card planning.

    The agent can dynamically execute MCP tools for:
    - Anki administration
    - Nextcloud information retrieval
    - Firecrawl web research

    Card creation is deliberately excluded from LLM-driven
    tool execution.

    When card creation is requested, the agent completes all
    necessary research and tool calls first and returns a
    complete JSON object for deterministic execution by
    anki_agent_node.py.
    """

    PROMPT_PATH = Path(__file__).with_name(
        "anki_systemprompt.md"
    )

    MAX_TOOL_ITERATIONS = 20

    def __init__(self, tool_factory: MCPToolFactory):
        self.tool_factory = tool_factory
        with self.PROMPT_PATH.open(
            "r",
            encoding="utf-8",
        ) as file:
            self.system_prompt = file.read()

        self._init_llm()

    def _init_llm(self) -> None:
        """
        Initialize the configured language model.
        """

        profile = config_store.llm_profiles.get(
            "oogabooga"
        )

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
            temperature=0.0,
            streaming=True,
            stream_usage=True,
            use_responses_api=False,
            extra_body=profile.extra_body,
        )

    @staticmethod
    def _is_card_creation_tool(tool: Any) -> bool:
        """
        Identify Anki card creation tools.

        The factory normally prefixes tool names with the
        corresponding MCP client alias.

        Examples:
            anki_create_card
            create_card

        Card creation must never be exposed to the LLM.
        """

        tool_name = getattr(tool, "name", "")

        if not isinstance(tool_name, str):
            return False

        normalized_name = tool_name.lower().strip()

        return (
            normalized_name == "create_card"
            or normalized_name.endswith("_create_card")
        )

    def _filter_agent_tools(
        self,
        tools: Optional[List[Any]],
    ) -> List[Any]:
        """
        Remove deterministic card creation tools from
        the agent-facing tool collection.

        All other discovered tools remain available.
        """

        if not tools:
            return []

        filtered_tools = []

        for tool in tools:
            if self._is_card_creation_tool(tool):
                continue

            filtered_tools.append(tool)

        return filtered_tools

    @staticmethod
    def _normalize_tool_result(result: Any) -> str:
        """
        Convert tool results into content suitable for
        LangChain ToolMessage objects.
        """

        if isinstance(result, str):
            return result

        if result is None:
            return ""

        if isinstance(result, list):
            parts = []

            for item in result:
                if isinstance(item, dict):
                    text = item.get("text")

                    if text is not None:
                        parts.append(str(text))
                    else:
                        parts.append(str(item))
                else:
                    text = getattr(item, "text", None)

                    if text is not None:
                        parts.append(str(text))
                    else:
                        parts.append(str(item))

            return "\n".join(parts)

        if isinstance(result, dict):

            return json.dumps(
                result,
                ensure_ascii=False,
                default=str,
            )

        return str(result)

    @staticmethod
    def _has_final_output_contract(
        response: AIMessage,
    ) -> bool:
        """
        Check whether the LLM response already contains
        a complete final JSON object according to the
        mandatory output contract.

        Expected structure:

        {
            "response": "...",
            "isCardCreation": false,
            "cards": []
        }

        This check is deliberately performed before
        executing any tool calls.

        A valid final JSON object takes precedence over
        additional tool calls returned in the same
        AIMessage.

        This prevents the agent from continuing its
        tool loop after the requested result is already
        complete.
        """

        content = response.content

        if isinstance(content, str):
            text_content = content.strip()

        elif isinstance(content, list):
            text_parts = []

            for item in content:

                if isinstance(item, dict):
                    text = item.get("text")

                    if text is not None:
                        text_parts.append(str(text))

                else:
                    text = getattr(item, "text", None)

                    if text is not None:
                        text_parts.append(str(text))

            text_content = "\n".join(text_parts).strip()

        else:
            return False

        if not text_content:
            return False

        try:
            parsed = json.loads(text_content)

        except (json.JSONDecodeError, TypeError):
            return False

        if not isinstance(parsed, dict):
            return False

        if not isinstance(parsed.get("response"), str):
            return False

        if not isinstance(parsed.get("isCardCreation"), bool):
            return False

        if not isinstance(parsed.get("cards"), list):
            return False

        # When no card creation is requested,
        # the cards array must be empty.
        if (
            not parsed["isCardCreation"]
            and parsed["cards"]
        ):
            return False

        return True

    async def _execute_tool_calls(
        self,
        response: AIMessage,
        tools_by_name: Dict[str, Any],
    ) -> List[ToolMessage]:
        """
        Execute all tool calls returned by the LLM.

        Each tool call is executed through its dynamically
        generated StructuredTool instance.

        Errors are returned to the LLM as ToolMessages,
        allowing it to recover or select another tool.
        """

        tool_messages = []

        for tool_call in response.tool_calls:

            tool_name = tool_call.get("name")

            tool_call_id = tool_call.get("id")

            arguments = tool_call.get("args", {})

            if not tool_name:
                raise ValueError(
                    "LLM returned a tool call without a tool name."
                )

            if not tool_call_id:
                raise ValueError(
                    f"Tool call '{tool_name}' has no tool call ID."
                )

            if not isinstance(arguments, dict):
                raise ValueError(
                    f"Invalid arguments for tool '{tool_name}': "
                    f"expected dict, got {type(arguments).__name__}."
                )

            # Additional safety check.
            # Card creation must never be executed by the LLM.
            if (
                tool_name == "create_card"
                or tool_name.lower().endswith("_create_card")
            ):
                raise PermissionError(
                    "The Anki create_card operation is reserved "
                    "for deterministic execution in anki_agent_node.py."
                )

            tool = tools_by_name.get(tool_name)

            if tool is None:
                tool_messages.append(
                    ToolMessage(
                        content=(
                            f"Tool '{tool_name}' is not available. "
                            "Please select an available tool."
                        ),
                        tool_call_id=tool_call_id,
                    )
                )
                continue

            try:
                result = await tool.ainvoke(arguments)

                normalized_result = self._normalize_tool_result(
                    result
                )

                tool_messages.append(
                    ToolMessage(
                        content=normalized_result,
                        tool_call_id=tool_call_id,
                    )
                )

            except Exception as exc:

                error_message = (
                    f"Tool execution failed: "
                    f"{type(exc).__name__}: {exc}"
                )

                tool_messages.append(
                    ToolMessage(
                        content=error_message,
                        tool_call_id=tool_call_id,
                    )
                )

        return tool_messages

    async def run(
        self,
        user_input: str,
        clients: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute the agent loop.

        The agent can perform multiple sequential MCP tool
        interactions before generating its final response.

        The loop terminates immediately when the LLM returns
        a complete JSON object according to the mandatory
        final output contract.

        This termination check takes precedence over
        additional tool calls contained in the same response.

        If card creation is requested, the final response
        contains the JSON object with the planned cards.

        Actual card creation is handled separately by
        anki_agent_node.py.
        """

        run_id = str(uuid.uuid4())[:8]

        print(f"\n[ANKI_AGENT] RUN START | run_id={run_id}")
        print(f"[ANKI_AGENT] INPUT: {user_input!r}")

        if not isinstance(user_input, str) or not user_input.strip():
            raise ValueError(
                "user_input must be a non-empty string."
            )

        # Discover tools dynamically from clients.
        tools = await self.tool_factory.create_tools(clients)

        # Remove create_card from the agent-facing tools.
        agent_tools = self._filter_agent_tools(tools)

        # Map generated tool names to their StructuredTool instances.
        tools_by_name = {
            tool.name: tool
            for tool in agent_tools
        }

        # Build the conversation.
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=user_input),
        ]

        # Bind tools dynamically.
        if agent_tools:
            model = self.llm.bind_tools(agent_tools)
        else:
            model = self.llm

        tool_iterations = 0

        while True:

            print(
                f"[ANKI_AGENT] LLM INVOKE | "
                f"run_id={run_id} | "
                f"iteration={tool_iterations + 1} | "
                f"messages={len(messages)}"
            )

            response = await model.ainvoke(messages)

            print(
                f"[ANKI_AGENT] LLM RESPONSE | "
                f"run_id={run_id} | "
                f"finish_reason={response.response_metadata.get('finish_reason')} | "
                f"tool_calls={len(response.tool_calls or [])}"
            )

            if not isinstance(response, AIMessage):
                raise TypeError(
                    "The LLM returned an unexpected response type: "
                    f"{type(response).__name__}"
                )

            # --------------------------------------------------
            # 1. Check for a completed final JSON output.
            # --------------------------------------------------
            #
            # IMPORTANT:
            #
            # This check must happen BEFORE processing tool calls.
            #
            # Some models may return a complete final JSON response
            # together with additional tool calls in the same
            # AIMessage.
            #
            # If the final output contract is already fulfilled,
            # the task is complete and no further tool execution
            # is necessary.
            #
            # This prevents repeated research and tool calls
            # after the requested result has already been produced.
            # --------------------------------------------------

            if self._has_final_output_contract(response):

                print(
                    f"[ANKI_AGENT] RUN END | "
                    f"run_id={run_id} | "
                    f"reason=final_output_detected | "
                    f"ignored_tool_calls={len(response.tool_calls or [])}"
                )

                break

            # Add the complete assistant response to the conversation.
            messages.append(response)

            # No further tool calls: agent has completed its work.
            if not response.tool_calls:
                print(
                    f"[ANKI_AGENT] RUN END | "
                    f"run_id={run_id} | reason=no_tool_calls"
                )
                break

            tool_iterations += 1

            if tool_iterations > self.MAX_TOOL_ITERATIONS:
                raise RuntimeError(
                    "Maximum number of agent tool iterations exceeded "
                    f"({self.MAX_TOOL_ITERATIONS})."
                )

            # Execute all tool calls and return their results
            # to the model for further reasoning.
            tool_messages = await self._execute_tool_calls(
                response=response,
                tools_by_name=tools_by_name,
            )

            messages.extend(tool_messages)

        return {
            "content": response.content,
            "raw_response": response,
            "tool_iterations": tool_iterations,
            "tools_available": list(tools_by_name.keys()),
        }
