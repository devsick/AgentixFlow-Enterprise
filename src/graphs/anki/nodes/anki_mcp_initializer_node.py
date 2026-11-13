
from typing import Any, Dict

from src.tools.anki_mcp_client import AnkiMCPClient
from src.shared.node_wrapper import observe_node
from src.shared.monitoring_writer import monitoring_writer



BASELINE_TOOLS = [
    "anki_notes",
    "anki_metadata",
    "anki_sync",
]


@observe_node
async def anki_mcp_initializer_node(state: Any) -> Dict[str, Any]:
    """
    Initializes the Anki MCP client, verifies the connection,
    retrieves the actual MCP tools and stores the client
    in the LangGraph state.
    """

    graph_id = state.get("graph_id", "unknown_graph")
    run_id = state.get("run_id", "unknown_run")

    print("--- MCP: Anki Initializing ---", flush=True)

    client = None

    try:
        await monitoring_writer.log_event(
            graph_id,
            run_id,
            "anki_mcp_initialization_attempt",
            {
                "allowed_tools": BASELINE_TOOLS,
            },
        )

        client = AnkiMCPClient(
            allowed_tools=BASELINE_TOOLS,
        )

        print(
            f"[ANKI MCP] Allowed tools: {client.allowed_tools}",
            flush=True,
        )

        # Establish connection and retrieve actual server tools.
        mcp_tools = await client.list_tools()

        actual_tool_names = [
            tool.get("name")
            for tool in mcp_tools
            if isinstance(tool, dict)
        ]

        print(
            f"[ANKI MCP] Actual tools returned by tools/list: "
            f"{actual_tool_names}",
            flush=True,
        )

        await monitoring_writer.log_event(
            graph_id,
            run_id,
            "anki_mcp_tools_loaded",
            {
                "allowed_tools": BASELINE_TOOLS,
                "actual_tools": actual_tool_names,
                "tool_count": len(mcp_tools),
            },
        )

        await monitoring_writer.log_event(
            graph_id,
            run_id,
            "anki_mcp_initialization_success",
            {
                "actual_tools": actual_tool_names,
                "tool_count": len(mcp_tools),
            },
        )

        print(
            f"--- MCP: Anki Initialized ({len(mcp_tools)} tools loaded) ---",
            flush=True,
        )

        return {
            "mcp_clients": {
                "anki": client,
            }
        }

    except Exception as e:
        error_msg = (
            f"--- MCP Anki Fehler: {type(e).__name__}: {e} ---"
        )
        print(error_msg, flush=True)

        await monitoring_writer.log_event(
            graph_id,
            run_id,
            "anki_mcp_initialization_failure",
            {
                "error": str(e),
                "error_type": type(e).__name__,
                "allowed_tools": BASELINE_TOOLS,
            },
        )

        if client is not None:
            await client.close()

        raise
