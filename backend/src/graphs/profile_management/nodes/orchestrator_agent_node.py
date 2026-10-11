from typing import Any, Dict
from langchain_core.messages import HumanMessage
from src.graphs.profile_management.state import ProfileManagementState

class OrchestratorAgentNode:
    """
    Node, der den User-Input klassifiziert, den Flow wählt 
    und Parameter wie `collective_name` extrahiert.
    """
    
    def __init__(self, prompt_path: str):
        with open(prompt_path, 'r', encoding='utf-8') as f:
            self.system_prompt = f.read()

    async def __call__(self, state: ProfileManagementState) -> Dict[str, Any]:
        # Simulation der LLM-Logik für den Testlauf
        last_message = state["messages"][-1].content.lower()
        
        decision = {
            "intent": "none",
            "params": {},
            "summary_context": ""
        }
        
        # Simulation: Fall 1 - Alles okay, Flow starten
        if "profil" in last_message or "collective" in last_message:
            decision["intent"] = "create_master_profile"
            if "collective" in last_message:
                # Simuliere Extraktion
                parts = last_message.split("collective")
                if len(parts) > 1:
                    name = parts[1].strip().replace("'", "").replace('"', "").split()[0]
                    decision["params"]["collective_name"] = name
            else:
                # Simulation: Fall 2 - Name fehlt -> Rückfrage
                decision["intent"] = "ask_user"
                decision["summary_context"] = "Missing collective name"
        
        # Wenn der Intent 'ask_user' ist, müssen wir eine Nachricht generieren
        new_messages = []
        if decision["intent"] == "ask_user":
            new_messages.append(HumanMessage(content="Welches Collective meinst du genau? Bitte nenne den Namen."))

        return {
            "metadata": {
                **state.get("metadata", {}),
                "orchestrator_decision": decision
            },
            "messages": new_messages
        }
