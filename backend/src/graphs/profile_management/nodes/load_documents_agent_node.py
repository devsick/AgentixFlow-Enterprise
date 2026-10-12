from typing import Any, Dict
from langchain_core.messages import AIMessage, HumanMessage
from src.graphs.profile_management.state import ProfileManagementState
from src.graphs.profile_management.agents.load_documents.agents.load_documents.load_documents_agent import (
    LoadDocumentsAgent,
)


class LoadDocumentsAgentNode:
    """
    Node, der den LoadDocumentsAgent aufruft und die geladenen Dokumente in den State schreibt.
    """

    def __init__(self):
        self.agent = LoadDocumentsAgent()

    async def __call__(
        self,
        state: ProfileManagementState,
    ) -> Dict[str, Any]:

        # 1. Liste der extrahierten Pfade aus dem State holen.
        # Wir gehen davon aus, dass der vorherige Node diese in state["extracted_file_paths"] geschrieben hat.
        file_paths = state.get("extracted_file_paths", [])
        
        if not file_paths:
            return {
                "metadata": {
                    **state.get("metadata", {}),
                    "error": "No file paths provided to LoadDocumentsAgent.",
                },
                "messages": [
                    AIMessage(
                        content="Error: No file paths found to load."
                    )
                ],
            }

        # 2. MCP Client aus dem State holen
        client = state.get("mcp_client")

        try:
            # 3. Agent ausführen
            # Der Agent erwartet nun eine Liste von Strings (list[str])
            result = await self.agent.run(
                file_paths=file_paths,
                mcp_client=client,
            )

            # Die Agent-Daten enthalten das Array 'documents'
            documents = result["data"].get("documents", [])

            # 4. Eine inhaltsfreie Zusammenfassung für die AIMessage erstellen
            # Wir listen nur den Pfad und den Status auf, niemals den 'content'.
            summary_lines = []
            for doc in documents:
                path = doc.get("path") or doc.get("name", "unknown")
                status = doc.get("status", "error")
                error = doc.get("error")
                
                line = f"- {path}: {status}"
                if status == "error" and error:
                    line += f" ({error})"
                summary_lines.append(line)

            summary_text = "Document loading process completed:\n" + "\n".join(summary_lines)

            # 5. State-Update vorbereiten
            # 'loaded_documents' enthält die vollständigen Daten (inkl. content) für den weiteren Workflow.
            # Die 'messages' enthalten nur die inhaltsfreie Status-Zusammenfassung.
            return {
                "loaded_documents": documents,
                "messages": [
                    AIMessage(content=summary_text)
                ],
            }

        except Exception as exc:
            return {
                "metadata": {
                    **state.get("metadata", {}),
                    "error": f"LoadDocuments failed: {exc}",
                },
                "messages": [
                    AIMessage(
                        content=(
                            "Error loading documents: "
                            f"{exc}"
                        )
                    )
                ],
            }
