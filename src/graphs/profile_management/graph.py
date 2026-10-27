from langgraph.graph import StateGraph, END

from src.graphs.profile_management.state import ProfileManagementState
from src.graphs.profile_management.nodes.mcp_initializer_node import (
    initialize_mcp_node,
)
from src.graphs.profile_management.nodes.orchestrator_agent_node import (
    OrchestratorAgentNode,
)
from src.graphs.profile_management.nodes.router_node import RouterNode
from src.graphs.profile_management.nodes.detect_collective_node import (
    DetectCollectiveAgentNode,
)
from src.graphs.profile_management.nodes.load_documents_node import (
    LoadDocumentsAgentNode,
)
from src.graphs.profile_management.nodes.extract_persona_agent_node import (
    ExtractPersonaAgentNode,
)
from src.graphs.profile_management.nodes.extract_project_agent_node import (
    ExtractProjectAgentNode,
)
from src.graphs.profile_management.nodes.extract_employments_agent_node import (
    ExtractEmploymentAgentNode,
)
from src.graphs.profile_management.nodes.extract_certificates_agent_node import (
    ExtractCertificatesAgentNode,
)
from src.graphs.profile_management.nodes.extract_skills_agent_node import (
    ExtractSkillsAgentNode,
)

def create_profile_management_graph():
    workflow = StateGraph(ProfileManagementState)

    # --------------------------------------------------
    # 1. Nodes registrieren
    # --------------------------------------------------

    workflow.add_node("initialize_mcp", initialize_mcp_node)
    workflow.add_node("orchestrator", OrchestratorAgentNode(), metadata={
        "streaming_mode": "status_only",
    })
    workflow.add_node("router", RouterNode())
    workflow.add_node("detect_collective", DetectCollectiveAgentNode(), metadata={
            "streaming_mode": "status_only",
        })
   
    workflow.add_node("load_documents", LoadDocumentsAgentNode(), metadata={
        "streaming_mode": "status_only",
    })
    workflow.add_node("extract_persona", ExtractPersonaAgentNode(), metadata={
            "streaming_mode": "status_only",
        })

    workflow.add_node("extract_projects", ExtractProjectAgentNode(), metadata={
                "streaming_mode": "status_only",
            })
    workflow.add_node("extract_employments", ExtractEmploymentAgentNode(), metadata={
                    "streaming_mode": "status_only",
               })
    workflow.add_node("extract_certificates", ExtractCertificatesAgentNode(), metadata={
                       "streaming_mode": "status_only",
                   })


  #  workflow.add_node("extract_skills", ExtractSkillsAgentNode(), metadata={
  #                          "streaming_mode": "status_only",
  #                      })
    # --------------------------------------------------
    # 2. Einstieg und Orchestrator
    # --------------------------------------------------

    workflow.set_entry_point("initialize_mcp")

    workflow.add_edge("initialize_mcp", "orchestrator")
    workflow.add_edge("orchestrator", "router")

    # --------------------------------------------------
    # 3. Router: passenden Workflow auswählen
    # --------------------------------------------------

    def router_logic(state: ProfileManagementState) -> str:

        intent = state.get("intent", "none")

        if intent == "create_master_profile":
            return "start_create_master_profile_workflow"

        # Nicht implementierte oder unbekannte Intents
        return "end"

    workflow.add_conditional_edges(
        "router",
        router_logic,
        {
            "start_create_master_profile_workflow": "detect_collective",
            "end": END,
        },
    )

    # --------------------------------------------------
    # 4. Ablauf des create_master_profile-Workflows
    # --------------------------------------------------

    workflow.add_edge("detect_collective", "load_documents")
   # workflow.add_edge("load_documents", "extract_certificates")
    workflow.add_edge("load_documents", "extract_employments")
   #
   # workflow.add_edge("load_documents", "extract_persona")
   # workflow.add_edge("extract_persona","extract_projects")
   # workflow.add_edge("extract_projects","extract_employments")
    workflow.add_edge("extract_employments", "extract_certificates")
   # workflow.add_edge("extract_certificates", "extract_skills")
    workflow.add_edge("extract_certificates", END)
   # workflow.add_edge("extract_skills", END)

    # --------------------------------------------------
    # 5. Graph kompilieren
    # --------------------------------------------------

    return workflow.compile()


if __name__ == "__main__":
    graph = create_profile_management_graph()
    print("Profile management graph compiled successfully.")
