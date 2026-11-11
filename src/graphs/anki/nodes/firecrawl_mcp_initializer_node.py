from typing import Any, Dict
from src.tools.firecrawl_mcp_client import FirecrawlMCPClient
from src.shared.node_wrapper import observe_node

# Empty list as no specific tools were mentioned for firecrawl
BASELINE_TOOLS = ["firecrawl_scrape",
                  "firecrawl_search", 
                  "firecrawl_parse", 
                  "firecrawl_find_tools"]

@observe_node
async def firecrawl_mcp_initializer_node(state: Any) -> Dict[str, Any]:
    """
    Initializes the Firecrawl MCP client.
    The client is stored in the LangGraph state.
    """
    client = FirecrawlMCPClient(
        allowed_tools=BASELINE_TOOLS
    )

    try:
        print(
            f"--- MCP: Firecrawl Initialized ---",
            flush=True,
        )
    except Exception as e:
        print(
            f"--- MCP Firecrawl Fehler: {type(e).__name__}: {e} ---",
            flush=True,
        )
        raise

    return {"firecrawl_mcp_client": client}
