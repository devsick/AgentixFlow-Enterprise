from src.api.streaming_translator import node_wrapper, observe_node
from src.shared.monitoring_writer import monitoring_writer

@observe_node
async def anki_initializer_node(state: dict) -> dict:
    """
    Initializes the Anki MCP client and saves it to the state.
    """
    # Placeholder for actual initialization logic
    # In a real scenario, you would use the registered mcp_client
    print("Initializing Anki MCP client...")
    
    # Simulate client initialization
    client = {"type": "mcp_client", "name": "anki-mcp"} 
    
    # Update state with the client
    return {
        "anki_mcp_client": client
    }
