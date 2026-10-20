from typing import Any, Dict
from langchain_core.messages import AIMessage
from src.graphs.profile_management.state import ProfileManagementState
from src.graphs.profile_management.agents.extract_questions.extract_questions_agent import (
    ExtractQuestionsAgent,
)
from src.shared.node_wrapper import observe_node

class ExtractQuestionsAgentNode:
    """
    Node, der den ExtractQuestionsAgent aufruft und die Ergebnisse in den State schreibt.
    """

    def __init__(self):
        self.agent = ExtractQuestionsAgent()




class ExtractQuestionsAgentNode:
    """
    Node, der den ExtractQuestionsAgent aufruft und die Ergebnisse in den State schreibt.
    """

    def __init__(self):
        self.agent = ExtractQuestionsAgent()

    @observe_node("extract_questions_agent_node")
    async def __call__(
        self,
        state: ProfileManagementState,
    ) -> Dict[str, Any]:
        # 1. Die benötigten Daten aus dem State holen.
        collective = state.get("collective")
        
        # Wir sammeln alle Entities, die potenzielle open_questions enthalten können.
        # Basierend auf dem SystemPrompt des Agents sind dies:
        # person, projects, employments, education, certificates, skills, sources.
        all_data = {
            "person": state.get("person", {}),
            "projects": state.get("projects", []),
            "employments": state.get("employments", []),
            "education": state.get("education", []),
            "certificates": state.get("certificates", []),
            "skills": state.get("skills", []),
            "sources": state.get("sources", []),
        }
        
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

        # 2. MCP Client aus dem State holen
        client = state.get("mcp_client")

        try:
            # 3. Agent ausführen
            # Der Agent erwartet collective (Dict) und all_data (Dict mit den Zuständen).
            result = await self.agent.run(
                collective=collective,
                all_data=all_data,
                mcp_client=client,
            )

            # Das Ergebnis des Agents (success, pages, open_questions) wird in den State geschrieben.
            # Da der Agent keine eigene Flow-Variable erzeugt, schreiben wir das Ergebnis 
            # in ein neues Feld 'open_questions_page_metadata'.
            
            success = result.get("success", False)
            pages = result.get("pages", [])
            open_questions = result.get("open_questions", [])

            # 4. State-Update vorbereiten
            prefix = (
                "The create_master_profile is completed. "
                "There are some open questions during the extraction process. "
                "You can find these also in the page 004_Open_Questions in Nextcloud. "
                "If you want to answer these questions you are starting the profile_maintenance chat."
            )

            if open_questions:
                questions_list = "\n".join([f"- {q}" for q in open_questions])
                summary_text = f"{prefix}\n\n{questions_list}"
            else:
                summary_text = f"{prefix}\n\nNo open questions were identified."

            return {
                "open_questions_page_metadata": {
                    "success": success,
                    "pages": pages,
                    "open_questions": open_questions
                },
                "messages": [
                    AIMessage(
                        content=summary_text
                    )
                ],
            }

        except Exception as exc:
            return {
                "metadata": {
                    **state.get("metadata", {}),
                    "error": f"ExtractQuestions failed: {exc}",
                },
                "messages": [
                    AIMessage(
                        content=(
                            "Error during open questions extraction: "
                            f"{exc}"
                        )
                    )
                ],
            }
