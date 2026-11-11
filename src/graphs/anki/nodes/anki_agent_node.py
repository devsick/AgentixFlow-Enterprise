
from typing import Any, Dict, List, Optional
import json
import re

from langchain_core.messages import AIMessage

from src.graphs.anki.state import AnkiState
from src.graphs.anki.agents.anki_agent import AnkiAgent
from src.shared.node_wrapper import observe_node
from src.shared.collective_functions import error_result
from src.tools.mcp_tool_factory import MCPToolFactory


class AnkiAgentNode:
    OVERVIEW_TITLE = "Anki Cards"

    def __init__(self):
        self.agent = AnkiAgent()
        self.tool_factory = MCPToolFactory()

    @staticmethod
    def _extract_content(result: Any) -> str:
        """
        Extract text content from the agent response.
        """

        content = result.get("content", "")

        if isinstance(content, str):
            return content.strip()

        if isinstance(content, list):
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

            return "\n".join(text_parts).strip()

        if content is None:
            return ""

        return str(content).strip()

    @staticmethod
    def _extract_json_array(content: str) -> Optional[List[Dict[str, Any]]]:
        """
        Extract a JSON array from the agent response.

        Supported formats:
        - Raw JSON array
        - JSON array inside a Markdown code block
        - JSON array embedded in surrounding text

        Returns None if the response does not contain a
        JSON array. This allows normal agent responses
        to pass through without card creation.
        """

        if not content:
            return None

        candidates = []

        # First attempt: parse the entire response directly.
        candidates.append(content.strip())

        # Second attempt: extract JSON from a fenced code block.
        fenced_matches = re.findall(
            r"```(?:json)?\s*(.*?)```",
            content,
            re.DOTALL | re.IGNORECASE,
        )

        candidates.extend(fenced_matches)

        for candidate in candidates:

            candidate = candidate.strip()

            if not candidate:
                continue

            try:
                parsed = json.loads(candidate)

                if isinstance(parsed, list):
                    return parsed

                if isinstance(parsed, dict) and isinstance(
                    parsed.get("cards"),
                    list,
                ):
                    return parsed["cards"]

            except json.JSONDecodeError:
                pass

        # Final fallback: find a JSON array in surrounding text.
        decoder = json.JSONDecoder()

        for match in re.finditer(r"\[", content):

            try:
                parsed, _ = decoder.raw_decode(
                    content[match.start():]
                )

                if isinstance(parsed, list):
                    return parsed

            except json.JSONDecodeError:
                continue

        return None

    @staticmethod
    def _validate_cards(
        cards: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Validate the structure of generated card objects.

        Only cards with isCreatingCard=True are executed.
        """

        if not isinstance(cards, list):
            raise ValueError(
                "Expected a JSON array containing card objects."
            )

        validated_cards = []

        for index, card in enumerate(cards):

            if not isinstance(card, dict):
                raise ValueError(
                    f"Card at index {index} must be a JSON object."
                )

            if "isCreatingCard" not in card:
                raise ValueError(
                    f"Card at index {index} is missing "
                    "'isCreatingCard'."
                )

            if not isinstance(card["isCreatingCard"], bool):
                raise ValueError(
                    f"Card at index {index}: "
                    "'isCreatingCard' must be a boolean."
                )

            if not card["isCreatingCard"]:
                continue

            required_fields = [
                "deck_name",
                "note_type",
                "fields",
                "tags",
            ]

            for required_field in required_fields:
                if required_field not in card:
                    raise ValueError(
                        f"Card at index {index} is missing "
                        f"required property '{required_field}'."
                    )

            if not isinstance(card["deck_name"], str) or not card["deck_name"].strip():
                raise ValueError(
                    f"Card at index {index}: invalid deck_name."
                )

            if not isinstance(card["note_type"], str) or not card["note_type"].strip():
                raise ValueError(
                    f"Card at index {index}: invalid note_type."
                )

            if not isinstance(card["fields"], dict) or not card["fields"]:
                raise ValueError(
                    f"Card at index {index}: fields must be "
                    "a non-empty object."
                )

            if not isinstance(card["tags"], list):
                raise ValueError(
                    f"Card at index {index}: tags must be a list."
                )

            for field_name, field_value in card["fields"].items():

                if not isinstance(field_name, str):
                    raise ValueError(
                        f"Card at index {index}: "
                        "field names must be strings."
                    )

                if not isinstance(field_value, str):
                    raise ValueError(
                        f"Card at index {index}: "
                        f"field '{field_name}' must contain a string."
                    )

            for tag in card["tags"]:
                if not isinstance(tag, str):
                    raise ValueError(
                        f"Card at index {index}: "
                        "all tags must be strings."
                    )

            validated_cards.append(card)

        return validated_cards

    @staticmethod
    def _build_mcp_client_mapping(
        state: AnkiState,
    ) -> Dict[str, Any]:
        """
        Collect initialized MCP clients from the graph state.

        Anki is mandatory because this agent is responsible
        for Anki operations.

        Other MCP clients are optional.
        """

        anki_client = state.get("anki_mcp_client")

        if anki_client is None:
            raise ValueError(
                "anki_mcp_client is missing from state."
            )

        clients = {
            "anki": anki_client,
        }

        firecrawl_client = state.get("firecrawl_mcp_client")

        if firecrawl_client is not None:
            clients["firecrawl"] = firecrawl_client

        nextcloud_client = state.get("nextcloud_mcp_client")

        if nextcloud_client is not None:
            clients["nextcloud"] = nextcloud_client

        return clients

    @observe_node("anki_agent_node")
    async def __call__(
        self,
        state: AnkiState,
    ) -> dict:
        """
        Execute the Anki agent node.

        Workflow:

        1. Read graph messages.
        2. Retrieve initialized MCP clients.
        3. Dynamically discover and generate MCP tools.
        4. Execute the agent with its available tools.
        5. Return normal responses directly.
        6. Parse and validate card JSON when present.
        7. Execute card creation deterministically.
        8. Return execution results and metadata.
        """

        try:

            # --------------------------------------------------
            # 1. Read messages from graph state
            # --------------------------------------------------

            messages = state.get("messages", [])

            if not messages:
                raise ValueError(
                    "No messages found in state to process."
                )

            input_parts = []

            for msg in messages:

                role = getattr(
                    msg,
                    "type",
                    "unknown",
                )

                content = getattr(
                    msg,
                    "content",
                    "",
                )

                if not isinstance(content, str):
                    content = str(content)

                input_parts.append(
                    f"{role.upper()}: {content}"
                )

            user_input = "\n".join(input_parts)

            # --------------------------------------------------
            # 2. Retrieve MCP clients
            # --------------------------------------------------

            clients = self._build_mcp_client_mapping(
                state
            )

            anki_mcp_client = clients["anki"]

            # --------------------------------------------------
            # 3. Dynamically discover MCP tools
            # --------------------------------------------------

            tools = await self.tool_factory.create_tools(
                clients
            )

            # --------------------------------------------------
            # 4. Execute agent with dynamic tools
            # --------------------------------------------------

            result = await self.agent.run(
                user_input=user_input,
                tools=tools,
            )

            content = self._extract_content(
                result
            )

            # --------------------------------------------------
            # 5. Determine whether this is a card creation task
            # --------------------------------------------------

            cards = self._extract_json_array(
                content
            )

            # Normal agent response:
            # No card creation is performed.
            if cards is None:

                metadata = dict(
                    state.get("metadata") or {}
                )

                metadata["anki_agent_tool_iterations"] = (
                    result.get("tool_iterations", 0)
                )

                return {
                    "messages": [
                        AIMessage(
                            content=content
                        )
                    ],
                    "metadata": metadata,
                }

            # --------------------------------------------------
            # 6. Validate generated cards
            # --------------------------------------------------

            validated_cards = self._validate_cards(
                cards
            )

            cards_selected = len(
                validated_cards
            )

            cards_skipped = (
                len(cards) - cards_selected
            )

            # --------------------------------------------------
            # 7. Deterministic card creation
            # --------------------------------------------------

            created_cards_count = 0
            failed_cards_count = 0

            card_errors = []

            for index, card_data in enumerate(
                validated_cards
            ):

                try:

                    # The special planning flag is not part
                    # of the actual Anki create_card arguments.
                    tool_arguments = {
                        key: value
                        for key, value in card_data.items()
                        if key != "isCreatingCard"
                    }

                    await anki_mcp_client.call_tool(
                        "create_card",
                        arguments=tool_arguments,
                    )

                    created_cards_count += 1

                except Exception as tool_exc:

                    failed_cards_count += 1

                    error_message = (
                        f"Card {index + 1} failed: "
                        f"{type(tool_exc).__name__}: {tool_exc}"
                    )

                    card_errors.append(
                        error_message
                    )

                    print(
                        error_message,
                        flush=True,
                    )

                    # Continue with the next card.
                    continue

            # --------------------------------------------------
            # 8. Build execution summary
            # --------------------------------------------------

            metadata = dict(
                state.get("metadata") or {}
            )

            metadata.update(
                {
                    "cards_generated": len(cards),
                    "cards_selected": cards_selected,
                    "cards_created": created_cards_count,
                    "cards_failed": failed_cards_count,
                    "cards_skipped": cards_skipped,
                    "anki_agent_tool_iterations": (
                        result.get("tool_iterations", 0)
                    ),
                }
            )

            summary = (
                "Anki card creation completed.\n\n"
                f"Generated cards: {len(cards)}\n"
                f"Cards selected for creation: {cards_selected}\n"
                f"Successfully created: {created_cards_count}\n"
                f"Failed: {failed_cards_count}\n"
                f"Skipped: {cards_skipped}"
            )

            if card_errors:

                summary += (
                    "\n\nErrors:\n"
                    + "\n".join(card_errors)
                )

            return {
                "messages": [
                    AIMessage(
                        content=summary
                    )
                ],
                "metadata": metadata,
            }

        except Exception as exc:

            error_result(exc)

            error_message = (
                f"AnkiAgent failed: "
                f"{type(exc).__name__}: {exc}"
            )

            return {
                "messages": [
                    AIMessage(
                        content=error_message
                    )
                ],
                "metadata": {
                    **dict(state.get("metadata") or {}),
                    "error": error_message,
                },
            }
