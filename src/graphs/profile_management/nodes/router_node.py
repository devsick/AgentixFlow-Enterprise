from typing import Dict, Any
from src.graphs.profile_management.state import ProfileManagementState
from src.shared.node_wrapper import observe_node

class RouterNode:
    """
    Deterministischer Node, der basierend auf dem Orchestrator-Intent 
    den nächsten Schritt im Graphen steuert.
    """
    @observe_node("router_node")
    async def __call__(self, state: ProfileManagementState) -> Dict[str, Any]:
        intent = state.get("intent", "none")
        print(f"DEBUG: RouterNode received intent: {intent}")

        # Wir geben keine neuen Nachrichten oder State-Updates zurück, 
        # sondern steuern nur das Routing via die Rückgabe des Intents für die Edge.
        # In LangGraph gibt man bei einem Router oft direkt den String für die Edge zurück,
        # aber hier geben wir das Signal im State zurück, um es in der Edge abzugreifen.
        
        return {
            "metadata": {
                **state.get("metadata", {}),
                "routing_signal": intent
            }
        }
