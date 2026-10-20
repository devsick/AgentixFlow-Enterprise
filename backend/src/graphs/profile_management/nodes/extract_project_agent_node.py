from typing import Any, Dict
from langchain_core.messages import AIMessage
from src.graphs.profile_management.state import ProfileManagementState
from src.graphs.profile_management.agents.extract_project.extract_project_agent import (
    ExtractProjectAgent,
)
from src.shared.node_wrapper import observe_node


class ExtractProjectAgentNode:
    """
    Node, der den ExtractProjectAgent aufruft und die Ergebnisse in den State schreibt.
    """

    def __init__(self):
        self.agent = ExtractProjectAgent()

    @observe_node("extract_project_agent_node")
    async def __call__(
        self,
        state: ProfileManagementState,
    ) -> Dict[str, Any]:
        # 1. Die benötigten Daten aus dem State holen.
        collective = state.get("collective")
        documents = state.get("loaded_documents")
        
        if not collective:
            return {
                "metadata": {
                    **state.get("metadata", {}),
                    "error": "Collective information missing from state.",
                },
                "messages": [
                    AIMessage(
                        content="Error: Collective information is missing."
                    )
                ],
            }
        
        if not documents:
            return {
                "metadata": {
                    **state.get("metadata", {}),
                    "error": "No documents available in state to process projects.",
                },
                "messages": [
                    AIMessage(
                        content="Error: No loaded documents found in state."
                    )
                ],
            }

        # 2. MCP Client aus dem State holen
        client = state.get("mcp_client")

        try:
            # 3. Agent ausführen
            # Der Agent erwartet collective (Dict) und documents (list of Dicts)
            result = await self.agent.run(
                collective=collective,
                documents=documents,
                mcp_client=client,
            )

            # Das Ergebnis des Agents wird im State 'projects' gespeichert.
            # Wir extrahieren success, pages und open_questions aus dem result.
            
            success = result.get("success", False)
            pages = result.get("pages", [])
            open_questions = result.get("open_questions", [])

            # 4. State-Update vorbereiten
            # Wir schreiben die extrahierten Informationen in den State 'projects'.
            return {
                "projects": {
                    "success": success,
                    "pages": pages,
                    "open_questions": open_questions
                },
                "messages": [
                    AIMessage(
                        content=f"Project extraction completed. Success: {success}"
                    )
                ],
            }

        except Exception as exc:
            return {
                "metadata": {
                    **state.get("metadata", {}),
                    "error": f"ExtractProject failed: {exc}",
                },
                "messages": [
                    AIMessage(
                        content=(
                            "Error during project extraction: "
                            f"{exc}"
                        )
                    )
                ],
            }
