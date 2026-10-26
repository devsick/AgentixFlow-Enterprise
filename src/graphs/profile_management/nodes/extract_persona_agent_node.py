
from typing import Any, Dict

from langchain_core.messages import AIMessage

from src.graphs.profile_management.state import ProfileManagementState
from src.graphs.profile_management.agents.extract_persona.extract_persona_agent import (
    ExtractPersonaAgent,
)
from src.shared.node_wrapper import observe_node
from src.shared.collective_functions import (
    CollectiveConfig,
    import_single_page,
)


class ExtractPersonaAgentNode:
    """
    Node, der den ExtractPersonaAgent aufruft und das Ergebnis in den State schreibt.
    """

    

    PAGE_TITLE = "001-Person"

    

    def __init__(self):
        self.agent = ExtractPersonaAgent()

    @observe_node("extract_persona_agent_node")
    async def __call__(
        self,
        state: ProfileManagementState,
    ) -> Dict[str, Any]:
        # 1. Daten aus dem State holen.
        collective = state.get("collective")
        documents = state.get("documents", [])

        if not collective:
            return {
                "metadata": {
                    **state.get("metadata", {}),
                    "error": "Collective information missing from state.",
                },
                "messages": [
                    AIMessage(
                        content=(
                            "Error: Collective information is missing. "
                            "Persona extraction was not started."
                        )
                    )
                ],
            }

        # 2. Collective-ID und Name extrahieren.
        collective_id = collective.get("id")
        collective_name = collective.get("name")

        if not collective_id or not collective_name:
            return {
                "metadata": {
                    **state.get("metadata", {}),
                    "error": "Collective ID or collective name is missing.",
                },
                "messages": [
                    AIMessage(
                        content=(
                            "Error: The collective ID or collective name "
                            "is missing. Persona extraction was not started."
                        )
                    )
                ],
            }

        # 3. Dokumentinhalte prüfen.
        if not isinstance(documents, list):
            return {
                "metadata": {
                    **state.get("metadata", {}),
                    "error": "documents must be a list.",
                },
                "messages": [
                    AIMessage(
                        content=(
                            "Error: The loaded documents have an invalid format. "
                            "Persona extraction was not started."
                        )
                    )
                ],
            }

        document_contents = []

        for document in documents:
            if not isinstance(document, dict):
                continue

            content = document.get("content")

            if isinstance(content, str) and content.strip():
                document_contents.append(document)

        if not document_contents:
            return {
                "metadata": {
                    **state.get("metadata", {}),
                    "error": (
                        "No documents with usable content available in state."
                    ),
                },
                "messages": [
                    AIMessage(
                        content=(
                            "Error: No loaded documents with usable content "
                            "were found. Persona extraction was not started."
                        )
                    )
                ],
            }

        # 4. MCP Client aus dem State holen.
        client = state.get("mcp_client")

        if client is None:
            return {
                "metadata": {
                    **state.get("metadata", {}),
                    "error": "MCP client missing from state.",
                },
                "messages": [
                    AIMessage(
                        content=(
                            "Error: The MCP client is unavailable. "
                            "Persona extraction was not started."
                        )
                    )
                ],
            }

        try:
            # 5. Agent aufrufen: Inhalt generieren, keine Tools ausführen.
            result = await self.agent.run(
                documents=document_contents,
            )

            if not isinstance(result, dict):
                raise ValueError(
                    "ExtractPersonaAgent returned an invalid result; "
                    "expected a dictionary."
                )

            content = result.get("content")
            open_questions = result.get("open_questions", [])

            if not isinstance(content, str) or not content.strip():
                raise ValueError(
                    "ExtractPersonaAgent returned empty or invalid page content."
                )

            if not isinstance(open_questions, list):
                raise ValueError(
                    "ExtractPersonaAgent returned invalid open_questions; "
                    "expected a list."
                )

            # 6. Generische Konfiguration für eine einzelne Seite.
            config = CollectiveConfig(
                mode="single_page",
                page_title=self.PAGE_TITLE,
                graph_id=state.get("graph_id"),
                run_id=state.get("run_id"),
            )

            # 7. Seite über die gemeinsamen Funktionen erstellen/aktualisieren.
            imported = await import_single_page(
                client=state["mcp_client"],
                collective_id=collective_id,
                page_title=config.page_title,
                content=content,
                config=config,
                collective=collective,
            )

            # 8. Ergebnis prüfen.
            if not imported.get("success"):
                raise RuntimeError(
                    "Persona page import did not complete successfully."
                )

            # 9. State erst nach erfolgreichem Schreiben aktualisieren.
            return {
                "person": {
                    "success": True,
                    "pages": [
                        {
                            "page_id": imported.get("page_id"),
                            "page_name": imported.get(
                                "page_name",
                                self.PAGE_TITLE,
                            ),
                            "file_path": imported.get("path"),
                        }
                    ],
                    "open_questions": open_questions,
                },
                "metadata": {
                    **state.get("metadata", {}),
                    "error": None,
                },
                "messages": [
                    AIMessage(
                        content=(
                            "Persona extraction completed successfully "
                            f"for collective '{collective_name}'. "
                            f"Page '{self.PAGE_TITLE}' was written and verified."
                        )
                    )
                ],
            }

        except Exception as exc:
            return {
                "person": {
                    "success": False,
                    "pages": [],
                    "open_questions": [],
                },
                "metadata": {
                    **state.get("metadata", {}),
                    "error": f"ExtractPersona failed: {exc}",
                },
                "messages": [
                    AIMessage(
                        content=(
                            "Error during persona extraction: "
                            f"{exc}"
                        )
                    )
                ],
            }
