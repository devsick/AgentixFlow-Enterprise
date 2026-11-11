
from langgraph.graph import StateGraph, END

from src.graphs.anki.state import AnkiState

from src.graphs.anki.nodes.nextcloud_mcp_initializer_node import (
    nextcloud_mcp_initializer_node,
)

from src.graphs.anki.nodes.firecrawl_mcp_initializer_node import (
    firecrawl_mcp_initializer_node,
)

from src.graphs.anki.nodes.anki_mcp_initializer_node import (
    anki_mcp_initializer_node,
)

from src.graphs.anki.nodes.anki_agent_node import (
    AnkiAgentNode,
)


def create_anki_graph():
    workflow = StateGraph(AnkiState)

    # --------------------------------------------------
    # 1. Nodes registrieren
    # --------------------------------------------------

    workflow.add_node(
    "initialize_nextcloud_mcp",
    nextcloud_mcp_initializer_node,
)

    workflow.add_node(
        "initialize_firecrawl_mcp",
        firecrawl_mcp_initializer_node,
    )

    workflow.add_node(
    "initialize_anki_mcp",
    anki_mcp_initializer_node,
)

    # Anki Agent uses LIVE streaming.
    # No status_only configuration is applied here.
    workflow.add_node(
        "anki_agent",
        AnkiAgentNode(),
        metadata={
            "streaming_mode": "live",
        },
    )

    # --------------------------------------------------
    # 2. Einstiegspunkt definieren
    # --------------------------------------------------

    workflow.set_entry_point("initialize_nextcloud_mcp")

    # --------------------------------------------------
    # 3. MCP Initialisierung
    # --------------------------------------------------

    workflow.add_edge(
        "initialize_nextcloud_mcp",
        "initialize_firecrawl_mcp",
    )

    workflow.add_edge(
        "initialize_firecrawl_mcp",
        "initialize_anki_mcp",
    )

    # --------------------------------------------------
    # 4. Anki Agent starten
    # --------------------------------------------------

    workflow.add_edge(
        "initialize_anki_mcp",
        "anki_agent",
    )

    workflow.add_edge(
        "anki_agent",
        END,
    )

    # --------------------------------------------------
    # 5. Graph kompilieren
    # --------------------------------------------------

    return workflow.compile()


# --------------------------------------------------
# Graph instance for registry
# --------------------------------------------------

graph_instance = create_anki_graph()


if __name__ == "__main__":
    graph = create_anki_graph()
    print("Anki graph compiled successfully.")
