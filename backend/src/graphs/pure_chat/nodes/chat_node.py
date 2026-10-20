from typing import Any
from src.graphs.pure_chat.state import PureChatState
from src.graphs.pure_chat.agents.chat_agent import ChatAgent
from src.shared.node_wrapper import observe_node

class ChatNode:
    stream_mode = "live"
    def __init__(self):
        self.agent = ChatAgent()

    @observe_node("chat_node")
    async def __call__(self, state: PureChatState) -> dict[str, Any]:
        """
        Der Node verarbeitet den State, lädt den System-Prompt und 
        ruft den Agenten auf.
        """
        # 1. System Prompt aus der Markdown-Datei laden (idealerweise gecached)
        try:
            with open("repos/agents/backend/src/graphs/pure_chat/prompts/system.md", "r", encoding="utf-8") as f:
                system_prompt = f.read()
        except FileNotFoundError:
            system_prompt = """You are a helpful assistant."""

        await self.agent.set_system_prompt(system_prompt)

        # 2. Agenten aufrufen
        # Wir geben den State zurück, wobei die neue Nachricht und die Metadaten 
        # (aus der Antwort des Agenten) hinzugefügt werden.
        response = await self.agent.run(state["messages"])
        
        # 3. Metadaten extrahieren (Tokens, Reasoning etc.)
        # LangChain fügt diese in response.additional_kwargs oder response.response_metadata ein
        metadata = {
            "token_usage": getattr(response, "response_metadata", {}).get("token_usage"),
            "model_name": getattr(response, "response_metadata", {}).get("model_name"),
            # Falls das Modell Thinking/Reasoning via additional_kwargs sendet
            "reasoning_content": response.additional_kwargs.get("reasoning_content") if hasattr(response, "additional_kwargs") else None,
            "tool_calls": response.tool_calls if hasattr(response, 'tool_calls') else []
        }

        return {
            "messages": [response],
            "metadata": metadata
        }
