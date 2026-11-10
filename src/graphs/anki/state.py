from typing import TypedDict, Annotated, Any
from langchain_core.messages import BaseMessage

class AnkiState(TypedDict):
    # Standard messages
    messages: Annotated[list[BaseMessage], "operator.add"]
    
    # MCP Client storage as requested
    anki_mcp_client: Any
    
    # Additional state for the graph
    run_id: str
    graph_id: str
