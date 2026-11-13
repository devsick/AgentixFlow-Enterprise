from typing import Annotated, Optional, TypedDict, Dict, Any
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

def sum_reducer(old: int, new: int) -> int:
    """Reducer function to sum up tokens."""
    return old + new


def merge_dicts(old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    return {**old, **new}


class ProfileMaintenanceState(TypedDict):
    """
    State für den Pure-Chat Graph.
    """
    # --- Inherited/Shared Logic (Logic typically in MultiAgentState) ---
    messages: Annotated[list[BaseMessage], add_messages]
    total_tokens: Annotated[int, sum_reducer]
    metadata: Dict[str, Any]
    run_id: str
    graph_id: str

    collective: Dict[str, Any] # {"name": str, "id": str, "exists": bool, "created": bool}
    collective_name: Optional[str]

    # MCP Integration
    mcp_clients: Annotated[Dict[str, Any], merge_dicts]