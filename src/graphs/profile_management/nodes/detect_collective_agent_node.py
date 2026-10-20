from typing import Any, Dict

from langchain_core.messages import AIMessage

from src.graphs.profile_management.state import ProfileManagementState
from src.shared.node_wrapper import observe_node


class DetectCollectiveAgentNode:
    """
    Deterministic node that identifies or creates a target collective using MCP tools.
    """
    
    def __init__(self):
        pass

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

            # 1. Get all collectives
            # We allow both tools in the request to ensure we get the right ones if they exist
            tools = await client.get_tools(allowed_names=["nextcloud-mcp_collectives_get_collectives", "nextcloud-mcp_collectives_create_collective"])
            
            get_collectives_tool = next((t for t in tools if t.name == "nextcloud-mcp_collectives_get_collectives"), None)
            create_collective_tool = next((t for t in tools if t.name == "nextcloud-mcp_collectives_create_collective"), None)

            if not get_collectives_tool:
                raise RuntimeError("Required tool 'nextcloud-mcp_collectives_get_collectives' not available.")

            # List all collectives
            existing_collectives = await get_collectives_tool.ainvoke({})
            
            # 2. Check for exact match
            matched_collective = None
            for coll in existing_collectives:
                if coll.get("name") == collective_name:
                    matched_collective = coll
                    break

            if matched_collective:
                new_collective = {
                    "name": matched_collective["name"],
                    "id": matched_collective["id"],
                    "exists": True,
                    "created": False,
                }
                status_text = f"Collective '{new_collective['name']}' wurde gefunden (ID: {new_collective['id']}).\n"
            else:
                # 3. Try to create it
                if not create_collective_tool:
                    raise RuntimeError("Required tool 'nextcloud-mcp_collectives_create_collective' not available to create the collective.")
                
                try:
                    creation_result = await create_collective_tool.ainvoke({"name": collective_name})
                    
                    new_collective = {
                        "name": creation_result["name"],
                        "id": creation_result["id"],
                        "exists": False,
                        "created": True,
                    }
                    status_text = f"Collective '{new_collective['name']}' wurde erstellt (ID: {new_collective['id']}).\n"
                except Exception as creation_err:
                    # If creation fails, return error state
                    new_collective = {
                        "name": None,
                        "id": None,
                        "exists": False,
                        "created": False,
                    }
                    status_text = f"Fehler beim Erstellen der Collective '{collective_name}': {str(creation_err)}\n"
                    return {
                        "collective": new_collective,
                        "messages": [AIMessage(content=status_text)],
                        "total_tokens": 0,
                        "metadata": {
                            **state.get("metadata", {}),
                            "error": f"Creation failed: {str(creation_err)}"
                        }
                    }

            return {
                "collective": new_collective,
                "messages": [
                    AIMessage(content=status_text)
                ],
                "total_tokens": 0,
                "metadata": {**state.get("metadata", {})}
            }

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
                            f"{exc}\n"
                        )
                    )
                ],
            }
