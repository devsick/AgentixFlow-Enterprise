
from typing import Any, Dict, List
import json

from langchain_core.messages import AIMessage, HumanMessage

from src.graphs.anki.state import AnkiState
from src.graphs.anki.agents.anki_agent import AnkiAgent
from src.shared.node_wrapper import observe_node
from src.shared.collective_functions import error_result
from src.tools.mcp_tool_factory import MCPToolFactory


class AnkiAgentNode:
    OVERVIEW_TITLE = "Anki Cards"

    def __init__(self):
        self.agent = AnkiAgent(tool_factory=MCPToolFactory())
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
    def _extract_agent_output(content: str) -> Dict[str, Any]:
        """
        Extract and validate the unified JSON output from the agent.

        Expected format:

        {
            "response": "The actual result of the user's request.",
            "isCardCreation": false,
            "cards": []
        }

        The response must be a valid JSON object.
        """

        if not content:
            raise ValueError(
                "Agent returned empty content."
            )

        try:
            result = json.loads(content)

        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Agent returned invalid JSON: {exc}"
            ) from exc

        if not isinstance(result, dict):
            raise ValueError(
                "Expected a JSON object as agent output."
            )

        required_fields = {
            "response",
            "isCardCreation",
            "cards",
        }

        missing_fields = required_fields - result.keys()

        if missing_fields:
            raise ValueError(
                "Agent output is missing required properties: "
                f"{', '.join(sorted(missing_fields))}"
            )

        if not isinstance(result["response"], str):
            raise ValueError(
                "'response' must be a string."
            )

        if not isinstance(result["isCardCreation"], bool):
            raise ValueError(
                "'isCardCreation' must be a boolean."
            )

        if not isinstance(result["cards"], list):
            raise ValueError(
                "'cards' must be an array."
            )

        if not result["isCardCreation"] and result["cards"]:
            raise ValueError(
                "'cards' must be empty when "
                "'isCardCreation' is false."
            )

        return result

    @staticmethod
    def _validate_cards(
        cards: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Validate the structure of generated card objects.

        Card creation is controlled exclusively by the
        top-level isCardCreation property.

        Individual card objects do not require an
        isCreatingCard property.
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

            if (
                not isinstance(card["deck_name"], str)
                or not card["deck_name"].strip()
            ):
                raise ValueError(
                    f"Card at index {index}: invalid deck_name."
                )

            if (
                not isinstance(card["note_type"], str)
                or not card["note_type"].strip()
            ):
                raise ValueError(
                    f"Card at index {index}: invalid note_type."
                )

            if (
                not isinstance(card["fields"], dict)
                or not card["fields"]
            ):
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
        """

        clients = state.get("mcp_clients") or {}

        if not isinstance(clients, dict):
            raise TypeError(
                "state['mcp_clients'] must be a dictionary."
            )

        anki_client = clients.get("anki")

        if anki_client is None:
            raise ValueError(
                "Anki MCP client is missing from state['mcp_clients']."
            )

        return {
            key: client
            for key, client in clients.items()
            if client is not None
        }

    @observe_node("anki_agent_node")
    async def __call__(
        self,
        state: AnkiState,
    ) -> dict:
        """
        Execute the Anki agent node.

        Workflow:

        1. Read the latest human message from graph state.
        2. Retrieve initialized MCP clients.
        3. Dynamically discover and generate MCP tools.
        4. Execute the agent with its available tools.
        5. Extract and validate the unified JSON output.
        6. Return normal responses directly.
        7. Validate cards when card creation is requested.
        8. Execute card creation deterministically.
        9. Return execution results and metadata.
        """

        print("\n[ANKI_NODE] CALL START")

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


            if not isinstance(user_input, str):
                user_input = str(user_input)

            user_input = user_input.strip()

            if not user_input:
                raise ValueError(
                    "The latest human message is empty."
                )

            # --------------------------------------------------
            # 2. Retrieve MCP clients
            # --------------------------------------------------

            clients = self._build_mcp_client_mapping(
                state
            )

            anki_mcp_client = clients["anki"]

            # --------------------------------------------------
            # 3. Execute agent with dynamically discovered MCP tools
            # --------------------------------------------------

            result = await self.agent.run(
                user_input=user_input,
                clients=clients,
            )

            print("[ANKI_NODE] AGENT RETURNED")

            content = self._extract_content(
                result
            )

            # --------------------------------------------------
            # 4. Extract and validate unified agent output
            # --------------------------------------------------

            agent_output = self._extract_agent_output(
                content
            )

            response = agent_output["response"]

            is_card_creation = agent_output["isCardCreation"]

            cards = agent_output["cards"]

            # --------------------------------------------------
            # 5. Handle normal agent responses
            # --------------------------------------------------

            # No card creation is performed when
            # isCardCreation is False.
            #
            # The actual result of the user's request is
            # returned directly from the response property.

            if not is_card_creation:

                metadata = dict(
                    state.get("metadata") or {}
                )

                metadata["anki_agent_tool_iterations"] = (
                    result.get("tool_iterations", 0)
                )

                return {
                    "messages": [
                        AIMessage(
                            content=response
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

                    # The card object contains only the
                    # actual arguments required by create_card.
                    #
                    # No additional planning flag needs to
                    # be removed.

                    tool_arguments = dict(
                        card_data
                    )

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
                f"{response}\n\n"
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
