from typing import Any, Dict
from src.tools.nextcloud_mcp_client import NextcloudMCPClient
from src.shared.node_wrapper import observe_node

# Global allowlist: maximum permissions for all agents.
BASELINE_TOOLS = [
    "collectives_get_collectives",
    "collectives_get_pages",
    "collectives_get_page",
    "collectives_search_pages",
    "collectives_create_page",
    "nc_webdav_list_directory",
    "nc_webdav_read_file",
    "nc_webdav_write_file",
    "nc_webdav_create_directory",
    "nc_webdav_search_files",
    "nc_webdav_find_by_name",
]

@observe_node
async def nextcloud_mcp_initializer_node(state: Any) -> Dict[str, Any]:
    """
    Initializes the Nextcloud MCP client with the global allowlist.
    The client is stored in the LangGraph state.
    """
    client = NextcloudMCPClient(
        allowed_tools=BASELINE_TOOLS
    )

    try:
        print(
            f"--- MCP: Nextcloud Allowed_Tools: {client.allowed_tools} ---",
            flush=True,
        )
    except Exception as e:
        print(
            f"--- MCP Nextcloud Fehler: {type(e).__name__}: {e} ---",
            flush=True,
        )
        raise

    return {"mcp_clients": {"nextcloud": client}}
