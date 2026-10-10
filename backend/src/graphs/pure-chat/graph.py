from langgraph.graph import StateGraph, START, END
from src.graphs.pure-chat.state import PureChatState
from src.graphs.pure-chat.nodes.chat_node import ChatNode

def create_pure_chat_graph():
    \"\"\"
    Erstellt und konfiguriert den Pure-Chat LangGraph.
    \"\"\"
    # Initialisiere den StateGraph mit unserem definierten State
    workflow = StateGraph(PureChatState)

    # Instanziierung des Nodes
    chat_node = ChatNode()

    # Registriere den Node im Workflow
    workflow.add_node(\"chat_node\", chat_node)

    # Definiere die Kanten (Edges)
    # In diesem simplen Graph: START -> chat_node -> END
    workflow.add_edge(START, \"chat_node\")
    workflow.add_edge(\"chat_node\", END)

    # Kompilieren des Graphen
    return workflow.compile()
