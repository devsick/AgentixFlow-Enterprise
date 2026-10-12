from typing import Any, Dict, List, Optional
from langchain_core.messages import HumanMessage, AIMessage
from src.graphs.profile_management.state import ProfileManagementState
from src.graphs.profile_management.agents.orchestrator_agent.orchestrator_agent import OrchestratorAgent

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
        decision = {
            "intent": intent,
            "params": extraction.params,
            "summary_context": extraction.summary_context
        }

        new_messages = []

        # 1. Falls eine SystemMessage (Antwort an den User) generiert wurde
        if extraction.SystemMessage:
            new_messages.append(AIMessage(content=extraction.SystemMessage))

        # 2. Logik für nicht implementierte Intents
        # Wenn der Intent weder 'ask_user' noch implementiert ist:
        if intent != "ask_user" and intent not in self.IMPLEMENTED_INTENTS:
            new_messages.append(AIMessage(content="This feature is currently not implemented."))
            # Wir setzen das Intent im Decision-Objekt auf 'unimplemented', 
            # damit der Router dies als Signal erkennt.
            decision["intent"] = "unimplemented"

        return {
            "metadata": {
                **state.get("metadata", {}),
                "orchestrator_decision": decision
            },
            "messages": new_messages,
            "total_tokens": usage.get("total_tokens", 0)
        }
