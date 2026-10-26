
from typing import Any, Dict

from langchain_core.messages import AIMessage

from src.graphs.profile_management.state import ProfileManagementState
from src.shared.node_wrapper import observe_node
import json


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
                    # Try with parse_document="markdown" first
                    result = await read_tool.ainvoke({"path": path, "parse_document": "markdown"})

                    # Extract the actual application payload from the MCP result.
                    # The document content is in structuredContent["content"],
                    # not in the outer MCP result's "content" field.
                    if isinstance(result, str):
                        result = json.loads(result)

                    if isinstance(result, dict):
                        if result.get("isError"):
                            raise RuntimeError(f"MCP tool returned an error: {result}")

                        result = result.get("structuredContent")

                        if isinstance(result, str):
                            result = json.loads(result)

                    if not isinstance(result, dict):
                        raise RuntimeError(
                            "Unexpected MCP tool result: expected structuredContent "
                            f"as a dict, got {type(result).__name__}"
                        )

                    # Handle the structured ReadFileResponse
                    if "content" in result:
                        content = result["content"]

                        # If the tool reported a failed parse, reflect that
                        if result.get("parse_status") in ["failed", "skipped"]:
                            status = "error"
                            error_msg = (
                                f"Parse status: {result.get('parse_status')} "
                                f"({result.get('parse_notes', 'No notes provided')})"
                            )
                        elif "error" in result or "error_message" in result:
                            # Explicit error keys in the dict
                            status = "error"
                            error_msg = result.get("error") or result.get("error_message")
                        elif not content:
                            # Content is empty, could be an error or just empty
                            status = "error"
                            error_msg = "Empty content received"
                        else:
                            status = "success"
                            error_msg = None
                    else:
                        # If the structured result has no "content", treat it as an error
                        status = "error"
                        content = None
                        error_msg = str(result)

                    if status == "success":
                        success_count += 1
                    else:
                        error_count += 1

                    documents.append({
                        "path": path,
                        "status": status,
                        "content": content,
                        "error": error_msg
                    })

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
