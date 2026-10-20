from typing import Any, Dict

from langchain_core.messages import AIMessage, HumanMessage

from src.graphs.profile_management.state import ProfileManagementState
from src.graphs.profile_management.agents.detect_collective_agent.detect_collective_agent import (
    DetectCollectiveAgent,
)
from src.shared.node_wrapper import observe_node


class DetectCollectiveAgentNode:
    """
    Identifies the target collective and writes the result
    into the graph state.
    """
    
    def __init__(self):
        self.agent = DetectCollectiveAgent()

    @observe_node("detect_collective_agent_node")
    async def __call__(
        self,
        state: ProfileManagementState,
    ) -> Dict[str, Any]:

        # Retrieve the MCP client from the shared graph state.
        client = state.get("mcp_client")

        try:
            collective_name = state.get("collective_name")

            if not collective_name:
                return {
                    "metadata": {
                        **state.get("metadata", {}),
                        "error": "No collective_name found in state.",
                    },
                    "messages": [
                        AIMessage(
                            content="- Es wurde kein Collective-Name im State gefunden.\n"
                        )
                    ],
                }

            result = await self.agent.run(
                last_message=f"collective_name:{collective_name}",
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
                f"Collective '{new_collective['name']}' wurde erstellt "
                f"(ID: {new_collective['id']})."
            )
        elif new_collective["exists"]:
            status_text = (
                f"Collective '{new_collective['name']}' wurde gefunden "
                f"(ID: {new_collective['id']})."
            )
        elif not new_collective["id"]:
            status_text = "Die angeforderte Collective wurde nicht gefunden."
        else:
            status_text = (
                "Die Collective konnte nicht eindeutig identifiziert werden."
            )

        return {
            "collective": new_collective,
            "messages": [
                AIMessage(content=status_text + "\n")
            ],
            "total_tokens": usage.get("total_tokens", 0),
            "metadata": {**state.get("metadata", {})}
        }

                **state.get("metadata", {}),
                "agent": "detect_collective",
            },
        }
