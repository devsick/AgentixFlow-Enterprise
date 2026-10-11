from typing import Annotated, TypedDict, Dict, Any
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class PureChatState(TypedDict):
    """
    State für den Pure-Chat Graph.
    """
    # add_messages sorgt dafür, dass Nachrichten an den Verlauf angehängt werden, statt ihn zu überschreiben
    messages: Annotated[list[BaseMessage], add_messages]
    
    # metadata speichert Streaming-Informationen wie Token-Usage, Thinking-Content und Modell-Name
    metadata: Dict[str, Any]

    # Monitoring-Informationen für das Filesystem-Logging
    run_id: str
    graph_id: str
