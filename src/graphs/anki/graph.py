from langgraph.graph import StateGraph, END
from src.graphs.anki.state import AnkiState
from src.graphs.anki.nodes.initializer import anki_initializer_node

def create_anki_graph():
    workflow = StateGraph(AnkiState)

    # Add nodes
    workflow.add_node("anki_initializer", anki_initializer_node)

    # Define edges
    workflow.set_entry_point("anki_initializer")
    workflow.add_edge("anki_initializer", END)

    return workflow.compile()

# For registry purposes
graph_instance = create_anki_graph()
