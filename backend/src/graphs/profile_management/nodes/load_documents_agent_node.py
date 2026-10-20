from typing import Any, Dict

from langchain_core.messages import AIMessage

from src.graphs.profile_management.state import ProfileManagementState
from src.shared.node_wrapper import observe_node


class LoadDocumentsAgentNode:
    """
    Deterministic node that loads files directly using MCP tools.
    """

    def __init__(self):
        pass

    @observe_node("load_documents_agent_node")
    async def __call__(
        self,
        state: ProfileManagementState,
    ) -> Dict[str, Any]:
        """
        Deterministic node that loads files directly using MCP tools.
        """
        file_paths = state.get("file_paths", [])
        client = state.get("mcp_client")

        if not file_paths:
            return {
                "metadata": {
                    **state.get("metadata", {}),
                    "error": "No file paths provided.",
                },
                "messages": [AIMessage(content="Error: No file paths found to load.")],
            }

        if not client:
            return {
                "metadata": {
                    **state.get("metadata", {}),
                    "error": "MCP client not found in state.",
                },
                "messages": [AIMessage(content="Error: MCP client is missing.")],
            }

        documents = []
        success_count = 0
        error_count = 0

        try:
            # Get the specific tool for reading files
            tools = await client.get_tools(allowed_names=["nc_webdav_read_file"])
            read_tool = next((t for t in tools if t.name == "nc_webdav_read_file"), None)

            if not read_tool:
                raise RuntimeError("Required tool 'nc_webdav_read_file' not available.")

            for path in file_paths:
                try:
                    try:
                        # Try with parse_document="markdown" first
                        result = await read_tool.ainvoke({"path": path, "parse_document": "markdown"})
                    except Exception:
                        # Fallback if the parameter is not supported by the tool
                        result = await read_tool.ainvoke({"path": path})
                    
                    # Handle different possible result formats from MCP tools
                    if isinstance(result, dict):
                        # Check if it's the structured ReadFileResponse
                        if "content" in result:
                            content = result["content"]
                            # If the tool reported a failed parse, we should reflect that
                            if result.get("parse_status") in ["failed", "skipped"]:
                                status = "error"
                                error_msg = f"Parse status: {result.get('parse_status')} ({result.get('parse_notes', 'No notes provided')})"
                            else:
                                status = "success"
                                error_msg = None
                        else:
                            # Fallback for other dict structures
                            content = str(result)
                            status = "success"
                            error_msg = None
                    else:
                        content = str(result)
                        status = "success"
                        error_msg = None

                    documents.append({
                        "path": path,
                        "status": status,
                        "content": content,
                        "error": error_msg
                    })
                    
                    if status == "success":
                        success_count += 1
                    else:
                        error_count += 1
                except Exception as e:
                    documents.append({
                        "path": path,
                        "status": "error",
                        "content": None,
                        "error": str(e)
                    })
                    error_count += 1

            # Construct summary message listing all processed files
            summary_lines = []
            for doc in documents:
                if doc["status"] == "success":
                    summary_lines.append(f"✅ {doc['path']}")
                else:
                    summary_lines.append(f"❌ {doc['path']} (Error: {doc['error']})")

            summary_text = (
                f"File loading process completed ({success_count} success, {error_count} failure):\n"
                + "\n".join(summary_lines)
            )

            return {
                "documents": documents,
                "messages": [AIMessage(content=summary_text + "\n")],
                "total_tokens": 0,
                "metadata": {**state.get("metadata", {})}
            }

        except Exception as exc:
            return {
                "metadata": {
                    **state.get("metadata", {}),
                    "error": f"Deterministic load failed: {exc}",
                },
                "messages": [AIMessage(content=f"Error in loading process: {exc}\n")],
            }
