from typing import Any, Dict
from src.tools.anki_mcp_client import AnkiMCPClient
from src.shared.node_wrapper import observe_node

# Empty list as no specific tools were mentioned for anki
BASELINE_TOOLS = ["anki-mcp-anki_notes", 
                  "anki-mcp-anki_metadata", 
                  "anki-mcp-anki_sync"]

@observe_node
async def anki_mcp_initializer_node(state: Any) -> Dict[str, Any]:
    """
    Initializes the Anki MCP client.
    The client is stored in the LangGraph state.
    """
    client = AnkiMCPClient(
        allowed_tools=BASELINE_TOOLS
    )

    try:
        print(
            f"--- MCP: Anki Initialized ---",
            flush=True,
        )
    except Exception as e:
        print(
            f"--- MCP Anki Fehler: {type(e).__name__}: {e} ---",
            flush=True,
        )
        raise

    return {"anki_mcp_client": client}
