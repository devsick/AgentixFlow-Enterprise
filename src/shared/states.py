from typing import Annotated, TypedDict, Dict, Any
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

def sum_reducer(old: int, new: int) -> int:
    """Reducer function to sum up tokens."""
    return old + new

class MultiAgentState(TypedDict):
    """
    Shared State for Multi-Agent Graphs.
    Designed to be used by all future graphs to support:
    - Message history via add_messages reducer.
    - Automatic token aggregation via sum_reducer.
    - Metadata for streaming and monitoring.
    - Unique run and graph identifiers.
    """
    # Conversation history
    messages: Annotated[list[BaseMessage], add_messages]
    
    # Cumulative token usage across all agents
    total_tokens: Annotated[int, sum_reducer]
    
    # Metadata for tracking individual agent contributions/status/thinking
    metadata: Dict[str, Any]

    # Unique identifiers
    run_id: str
    graph_id: str
