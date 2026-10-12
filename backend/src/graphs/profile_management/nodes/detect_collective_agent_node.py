from typing import Any, Dict

from langchain_core.messages import AIMessage, HumanMessage

from src.graphs.profile_management.state import ProfileManagementState
from src.graphs.profile_management.agents.detect_collective_agent.detect_collective_agent import (
    DetectCollectiveAgent,
)


class DetectCollectiveAgentNode:
    """
    Identifies the target collective and writes the result
    into the graph state.
    """

    def __init__():
        self.agent = DetectCollectiveAgent()

    async def __call__(
        self,
        state: ProfileManagementState,
    ) -> Dict[str, Any]:

        # Find the most recent user message.
        last_message = next(
            (
                message.content
                for message in reversed(state["messages"])
                if isinstance(message, HumanMessage)
            ),
            None,
        )

        if last_message is None:
            return {
                "metadata": {
                    **state.get("metadata", {}),
                    "error": "No user message found.",
                },
                "messages": [
                    AIMessage(
                        content="Error: No user message found."
                    )
                ],
            }

        # Retrieve the MCP client from the shared graph state.
        client = state.get("mcp_client")

        try:
            result = await self.agent.run(
                last_message=last_message,
                mcp_client=client,
            )

            collective_data = result["data"]
            usage = result["usage"]

        except Exception as exc:
            return {
                "metadata": {
                    **state.get("metadata", {}),
                    "error": f"DetectCollective failed: {exc}",
                },
                "messages": [
                    AIMessage(
                        content=(
                            "Error identifying the collective: "
                            f"{exc}"
                        )
                    )
                ],
            }

        new_collective = {
            "name": collective_data.get("name"),
            "id": collective_data.get("id"),
            "exists": collective_data.get("exists", False),
            "created": collective_data.get("created", False),
        }

        if new_collective["created"]:
            status_text = (
                f"A new collective '{new_collective['name']}' "
                "has been successfully created."
            )
        elif new_collective["exists"]:
            status_text = (
                f"Collective '{new_collective['name']}' was found."
            )
        elif not new_collective["id"]:
            status_text = (
                "Error: The collective could not be identified."
            )
        else:
            status_text = "Collective identified."

        return {
            "collective": new_collective,
            "messages": [
                AIMessage(content=status_text)
            ],
            "total_tokens": usage.get("total_tokens", 0),
            "metadata": {
                **state.get("metadata", {}),
                "agent": "detect_collective",
            },
        }
