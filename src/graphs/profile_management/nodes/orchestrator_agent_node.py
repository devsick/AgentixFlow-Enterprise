from typing import Any, Dict, List, Optional
from langchain_core.messages import HumanMessage, AIMessage
from src.graphs.profile_management.state import ProfileManagementState
from src.graphs.profile_management.agents.orchestrator_agent.orchestrator_agent import OrchestratorAgent
from src.shared.node_wrapper import observe_node

class OrchestratorAgentNode:
    """
    Node, der den User-Input mithilfe eines LLM-Agents analysiert, 
    Parameter extrahiert und die Entscheidung für den nächsten Schritt trifft.
    """
    
    # Liste der aktuell unterstützten Workflows
    IMPLEMENTED_INTENTS = ["create_master_profile"]

    def __init__(self):
        # Die Agent-Instanz wird initialisiert. 
        self.agent = OrchestratorAgent()

    @observe_node("orchestrator_agent_node")
    async def __call__(self, state: ProfileManagementState) -> Dict[str, Any]:
        last_message = state["messages"][-1].content

        # Der Agent führt die Logik aus
        try:
            extraction, usage = await self.agent.run(last_message)
        except Exception as e:
            # Fallback bei Fehlern
            return {
                "metadata": {**state.get("metadata", {}), "error": str(e)},
                "messages": [AIMessage(content=f"Fehler bei der Analyse: {str(e)}")]
            }

        intent = extraction.intent
        params = extraction.params
        decision = {
            "intent": intent,
            "params": params,
            "summary_context": extraction.summary_context
        }

        new_messages = []

        # 1. Falls eine SystemMessage (Antwort an den User) generiert wurde
      #  if extraction.SystemMessage:
      #      new_messages.append(AIMessage(content=extraction.SystemMessage))

        # 2. Logik für nicht implementierte Intents
        # Wenn der Intent weder 'ask_user' noch implementiert ist:
        if intent != "ask_user" and intent not in self.IMPLEMENTED_INTENTS:
            new_messages.append(AIMessage(content="This feature is currently not implemented."))
            # Wir setzen das Intent im Decision-Objekt auf 'unimplemented', 
            # damit der Router dies als Signal erkennt.
            decision["intent"] = "unimplemented"
        else:
            # Feedback an den User über die Entscheidung
            collective_name = params.get("collective_name", "unknown")
            file_paths = params.get("file_paths", [])
            
            msg_parts = [f"I extracted the collective {collective_name} and the next task is {intent}."]
            if file_paths:
                msg_parts.append(f"Files detected: {', '.join(file_paths)}")
            
            new_messages.append(AIMessage(content="\n".join(msg_parts) + "\n"))

        return {
            "intent": decision["intent"],
            "collective_name": params.get("collective_name"),
            "file_paths": params.get("file_paths", []),
            "messages": new_messages,
            "total_tokens": usage.get("total_tokens", 0),
            "metadata": {
                **state.get("metadata", {})
            }
        }
