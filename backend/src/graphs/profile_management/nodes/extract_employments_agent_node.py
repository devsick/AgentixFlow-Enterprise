from typing import Any, Dict
from langchain_core.messages import AIMessage
from src.graphs.profile_management.state import ProfileManagementState
from src.graphs.profile_management.agents.extract_employments.extract_employments_agent import (
    ExtractEmploymentsAgent,
)
from src.shared.node_wrapper import observe_node


class ExtractEmploymentsAgentNode:
    """
    Node, der den ExtractEmploymentsAgent aufruft und die Ergebnisse in den State schreibt.
    """

    def __init__(self):
        self.agent = ExtractEmploymentsAgent()

    @observe_node("extract_employments_agent_node")
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
                    "error": "No documents available in state to process employments.",
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
            # Der Agent erwartet collective (Dict), documents (list of Dicts) und projects (list of Dicts)
            result = await self.agent.run(
                collective=collective,
                documents=documents,
                mcp_client=client,
            )

            # Das Ergebnis des Agents wird im State 'employments' gespeichert.
            # Wir extrahieren success, pages und open_questions aus dem result.
            
            success = result.get("success", False)
            pages = result.get("pages", [])
            open_questions = result.get("open_questions", [])

            # 4. State-Update vorbereiten
            # Wir schreiben die extrahierten Informationen in den State 'employments'.
            return {
                "employments": {
                    "success": success,
                    "pages": pages,
                    "open_questions": open_questions
                },
                "messages": [
                    AIMessage(
                        content=f"Employment extraction completed. Success: {success}"
                    )
                ],
            }

        except Exception as exc:
            return {
                "metadata": {
                    **state.get("metadata", {}),
                    "error": f"ExtractEmployments failed: {exc}",
                },
                "messages": [
                    AIMessage(
                        content=(
                            "Error during employment extraction: "
                            f"{exc}"
                        )
                    )
                ],
            }
