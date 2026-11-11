
from typing import Annotated, Any, Dict, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


def sum_reducer(old: int, new: int) -> int:
    """Reducer function to sum up tokens."""
    return old + new


class AnkiState(TypedDict):
    """
    Shared State for the Anki Graph.
    Compatible with the common StreamingTranslator infrastructure.
    """

    # --- Inherited / Shared Logic ---
    messages: Annotated[list[BaseMessage], add_messages]
    total_tokens: Annotated[int, sum_reducer]
    metadata: Dict[str, Any]
    run_id: str
    graph_id: str

    # --- MCP Clients ---
    anki_mcp_client: Any
    firecrawl_mcp_client: Any
    nextcloud_mcp_client: Any
