from langgraph.graph import StateGraph, END
from src.graphs.profile_management.state import ProfileManagementState
from src.graphs.profile_management.nodes.mcp_initializer_node import initialize_mcp_node
from src.graphs.profile_management.nodes.orchestrator_agent_node import OrchestratorAgentNode
from src.graphs.profile_management.nodes.router_node import RouterNode
from src.graphs.profile_management.nodes.detect_collective_agent_node import DetectCollectiveAgentNode
from src.graphs.profile_management.nodes.load_documents_agent_node import LoadDocumentsAgentNode

def create_profile_management_graph():
    workflow = StateGraph(ProfileManagementState)

    # 1. Initialize Nodes
    # initialize_mcp_node is a function
    workflow.add_node("initialize_mcp", initialize_mcp_node)
    
    # Agent Nodes
    orchestrator = OrchestratorAgentNode()
    workflow.add_node("orchestrator", orchestrator)
    
    router = RouterNode()
    workflow.add_node("router", router)
    
    detect_collective = DetectCollectiveAgentNode()
    workflow.add_node("detect_collective", detect_collective)

    load_documents = LoadDocumentsAgentNode()
    workflow.add_node("load_documents", load_documents)

    # 2. Define Edges
    # Start -> Initialize MCP
    workflow.set_entry_point("initialize_mcp")
    
    # Initialize MCP -> Orchestrator
    workflow.add_edge("initialize_mcp", "orchestrator")
    
    # Orchestrator -> Router
    workflow.add_edge("orchestrator", "router")
    
    # Conditional Edges from Router
    def router_logic(state: ProfileManagementState):
        # RouterNode setzt das Signal in 'routing_signal' im metadata Feld
        signal = state.get("metadata", {}).get("routing_signal", "none")
        if signal == "detect_collective":
            return "detect_collective"
        elif signal == "load_documents":
            return "load_documents"
        elif signal == "end" or signal == "unimplemented":
            return "end"
        else:
            return "end"

    workflow.add_conditional_edges(
        "router",
        router_logic,
        {
            "detect_collective": "detect_collective",
            "end": END
        }
    )

    # Agent Node -> Router (to decide next step)
    workflow.add_edge("detect_collective", "router")
    
    # detect_collective -> load_documents
    workflow.add_edge("detect_collective", "load_documents")

    return workflow.compile()

if __name__ == "__main__":
    graph = create_profile_management_graph()
    print("Graph compiled successfully.")
