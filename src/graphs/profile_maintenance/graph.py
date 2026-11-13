from langgraph.graph import StateGraph, START, END
from src.graphs.profile_maintenance.state import ProfileMaintenanceState
from src.graphs.profile_maintenance.nodes.profile_maintenance_agent_node import ProfleMaintenanceNode
from src.graphs.profile_maintenance.nodes.nextcloud_mcp_initializer_node import (
    nextcloud_mcp_initializer_node,
)
from src.graphs.profile_maintenance.nodes.firecrawl_mcp_initializer_node import (
    firecrawl_mcp_initializer_node,
)


def create_profile_maintenance_graph():
    """
    Erstellt und konfiguriert den Pure-Chat LangGraph.
    """
    # Initialisiere den StateGraph mit unserem definierten State
    workflow = StateGraph(ProfileMaintenanceState)

    # Instanziierung des Nodes
    profile_maintenance_node = ProfleMaintenanceNode()

    # Registriere den Node im Workflow
    workflow.add_node("nextcloud_initialize_mcp", nextcloud_mcp_initializer_node)
    workflow.add_node("firecrawl_initialize_mcp", firecrawl_mcp_initializer_node)
    workflow.add_node("profile_maintenance_node", profile_maintenance_node, metadata={"streaming_mode": "live",})
    

    # Definiere die Kanten (Edges)
    # In diesem simplen Graph: START -> profile_maintenance_node -> END
    workflow.add_edge(START, "nextcloud_initialize_mcp")
    workflow.add_edge("nextcloud_initialize_mcp", "firecrawl_initialize_mcp")
    workflow.add_edge("firecrawl_initialize_mcp", "profile_maintenance_node")
    workflow.add_edge("profile_maintenance_node", END)

    # Kompilieren des Graphen
    return workflow.compile()