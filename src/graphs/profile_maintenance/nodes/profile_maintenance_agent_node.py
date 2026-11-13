
from typing import Any

from src.graphs.profile_maintenance.state import ProfileMaintenanceState
from src.graphs.profile_maintenance.agents.profile_maintenance_agent import (
    ProfileMaintenanceAgent,
)
from src.shared.node_wrapper import observe_node
from src.tools.mcp_tool_factory import MCPToolFactory


class ProfileMaintenanceNode:
    stream_mode = "live"

    def __init__(self):
        self.agent = ProfileMaintenanceAgent(
            tool_factory=MCPToolFactory()
        )

    @observe_node("profile_maintenance_agent_node")
    async def __call__(
        self,
        state: ProfileMaintenanceState,
    ) -> dict[str, Any]:
        """
        Execute the profile maintenance agent.

        Workflow:
        1. Read messages from the graph state.
        2. Retrieve initialized MCP clients.
        3. Pass messages and clients to the agent.
        4. The agent dynamically creates and executes MCP tools.
        5. Extract response metadata.
        6. Return the assistant message and updated metadata.
        """

        # --------------------------------------------------
        # 1. Read messages from graph state
        # --------------------------------------------------

        messages = state.get("messages", [])

        if not messages:
            raise ValueError(
                "No messages found in state to process."
            )

        # --------------------------------------------------
        # 2. Retrieve MCP clients
        # --------------------------------------------------

        clients = state.get("mcp_clients") or {}

        if not isinstance(clients, dict):
            raise TypeError(
                "state['mcp_clients'] must be a dictionary."
            )

        if not clients:
            raise ValueError(
                "No MCP clients found in state['mcp_clients']."
            )

        # --------------------------------------------------
        # 3. Execute profile maintenance agent
        # --------------------------------------------------

        # The agent itself creates the dynamic tools using
        # MCPToolFactory and executes the tool-calling loop.
        response = await self.agent.run(
            messages,
            clients,
        )

        # --------------------------------------------------
        # 4. Extract response and token usage
        # --------------------------------------------------

        message, usage = response

        # --------------------------------------------------
        # 5. Collect metadata
        # --------------------------------------------------

        metadata = dict(
            state.get("metadata") or {}
        )

        response_metadata = (
            getattr(message, "response_metadata", {}) or {}
        )

        additional_kwargs = (
            getattr(message, "additional_kwargs", {}) or {}
        )

        metadata.update(
            {
                "token_usage": usage,
                "model_name": response_metadata.get(
                    "model_name"
                ),
                "reasoning_content": additional_kwargs.get(
                    "reasoning_content"
                ),
                "tool_calls": getattr(
                    message,
                    "tool_calls",
                    [],
                ),
            }
        )

        # --------------------------------------------------
        # 6. Return graph state update
        # --------------------------------------------------

        return {
            "messages": [message],
            "metadata": metadata,
        }


# Backward compatibility for existing imports that still
# use the previous misspelled class name.
ProfleMaintenanceNode = ProfileMaintenanceNode
