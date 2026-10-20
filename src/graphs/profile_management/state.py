from typing import Annotated, TypedDict, Dict, Any, List, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

def sum_reducer(old: int, new: int) -> int:
    """Reducer function to sum up tokens."""
    return old + new

class ProfileManagementState(TypedDict):
    """
    Shared State for Profile Management Graph.
    Extends MultiAgentState logic via custom fields.
    """
    # --- Inherited/Shared Logic (Logic typically in MultiAgentState) ---
    messages: Annotated[list[BaseMessage], add_messages]
    total_tokens: Annotated[int, sum_reducer]
    metadata: Dict[str, Any]
    run_id: str
    graph_id: str

    # --- Profile Management Specific Fields ---
     # --- Orchestrator / Workflow Routing ---
    intent: str
    collective_name: Optional[str]
    file_paths: List[str]
    
    # Information about the target collective
    collective: Dict[str, Any] # {"name": str, "id": str, "exists": bool, "created": bool}
    
    # Content/Entities
    collectives: List[Dict[str, Any]]
    documents: List[Dict[str, Any]]
    person: Dict[str, Any]
    projects: List[Dict[str, Any]]
    employments: List[Dict[str, Any]]
    education: List[Dict[str, Any]]
    certificates: List[Dict[str, Any]]
    skills: List[Dict[str, Any]]
    sources: List[Dict[str, Any]]
    
    # Analysis Results
    profile_description: str
    positioning: str
    open_questions: List[str]
    
from typing import Annotated, TypedDict, Dict, Any, List, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

def sum_reducer(old: int, new: int) -> int:
    """Reducer function to sum up tokens."""
    return old + new

class ProfileManagementState(TypedDict):
    """
    Shared State for Profile Management Graph.
    Extends MultiAgentState logic via custom fields.
    """
    # --- Inherited/Shared Logic (Logic typically in MultiAgentState) ---
    messages: Annotated[list[BaseMessage], add_messages]
    total_tokens: Annotated[int, sum_reducer]
    metadata: Dict[str, Any]
    run_id: str
    graph_id: str

    # --- Profile Management Specific Fields ---
    # Information about the target collective
    collective: Dict[str, Any] # {"name": str, "id": str, "exists": bool, "created": bool}

    # --- Orchestrator / Workflow Routing ---
    intent: str
    collective_name: Optional[str]
    file_paths: List[Dict[str, Any]] 
    
    # Content/Entities
    collectives: List[Dict[str, Any]]
    documents: List[Dict[str, Any]]
    person: Dict[str, Any]
    projects: List[Dict[str, Any]]
    employments: List[Dict[str, Any]]
    education: List[Dict[str, Any]]
    certificates: List[Dict[str, Any]]
    skills: List[Dict[str, Any]]
    sources: List[Dict[str, Any]]
    
    # Analysis Results
    profile_description: str
    positioning: str
    open_questions: List[str]
    
    # Status & Error Tracking
    master_profile_status: str # e.g., 'pending', 'completed', 'error'
    master_profile_error: Optional[str]
    master_profile_success: Optional[str]
    profile: Dict[str, Any] # The final aggregated profile object

    # MCP Integration
    mcp_client: Any # Holds the NextcloudMCPClient instance

