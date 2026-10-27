from typing import Any, Dict

from langchain_core.messages import AIMessage

from src.graphs.profile_management.state import ProfileManagementState
from src.graphs.profile_management.agents.extract_skills.extract_skills_agent import (
    ExtractSkillsAgent,
)
from src.shared.node_wrapper import observe_node
from src.shared.collective_functions import (
    CollectiveConfig,
    import_single_page,
)


class ExtractSkillsAgentNode:
    """
    Node responsible for extracting skills and competencies
    and importing the 032-Skills page.
    """

    PAGE_TITLE = "032-Skills"

    SKILL_CATEGORIES = {
        "## Professional Skills",
        "## Technical Skills",
        "## Methods",
        "## Tools / Technologies",
        "## Languages",
        "## Soft Skills",
        "## Other substantiated competencies",
    }

    def __init__(self):
        self.agent = ExtractSkillsAgent()

    @observe_node("extract_skills_agent_node")
    async def __call__(
        self,
        state: ProfileManagementState,
    ) -> Dict[str, Any]:
        try:
            collective = state.get("collective")
            documents = state.get("documents", [])
            mcp_client = state.get("mcp_client")

            if not isinstance(collective, dict):
                raise ValueError("Missing or invalid collective in state.")

            collective_id = collective.get("id")
            if not collective_id:
                raise ValueError("Missing collective ID.")

            if not isinstance(documents, list):
                raise ValueError("Documents must be a list.")

            if mcp_client is None:
                raise ValueError("Missing MCP client in state.")

            document_contents = [
                doc
                for doc in documents
                if isinstance(doc, dict)
                and isinstance(doc.get("content"), str)
                and doc["content"].strip()
            ]

            if not document_contents:
                raise ValueError(
                    "No documents contain usable text for skills extraction."
                )

            result = await self.agent.run(
                documents=document_contents
            )

            if not isinstance(result, dict):
                raise ValueError(
                    "ExtractSkillsAgent returned an invalid result."
                )

            content = result.get("content")
            open_questions = result.get("open_questions")

            if not isinstance(content, str) or not content.strip():
                raise ValueError(
                    "ExtractSkillsAgent returned empty content."
                )

            if not isinstance(open_questions, list) or not all(
                isinstance(question, str)
                for question in open_questions
            ):
                raise ValueError(
                    "ExtractSkillsAgent returned invalid open_questions."
                )

            # A skill entry must be a level-three heading inside
            # one of the recognized skill categories.
            current_category = None
            skill_entries = []

            for line in content.splitlines():
                heading = line.strip()

                if heading.startswith("## "):
                    current_category = (
                        heading
                        if heading in self.SKILL_CATEGORIES
                        else None
                    )
                    continue

                if (
                    current_category is not None
                    and heading.startswith("### ")
                    and heading[4:].strip()
                ):
                    skill_entries.append(heading)

            if not skill_entries:
                return {
                    "skills": {
                        "success": True,
                        "pages": [],
                        "open_questions": [],
                    },
                    "metadata": {
                        **state.get("metadata", {}),
                        "error": None,
                    },
                    "messages": [
                        AIMessage(
                            content=(
                                "Skills extraction completed. "
                                "No substantiated skills or competencies "
                                "were found; no page was created."
                            )
                        )
                    ],
                }

            config = CollectiveConfig(
                mode="single_page",
                page_title=self.PAGE_TITLE,
                graph_id=state.get("graph_id"),
                run_id=state.get("run_id"),
            )

            imported = await import_single_page(
                client=mcp_client,
                collective_id=collective_id,
                page_title=config.page_title,
                content=content,
                config=config,
                collective=collective,
            )

            if not isinstance(imported, dict) or not imported.get("success"):
                raise ValueError(
                    f"Failed to import {self.PAGE_TITLE}: {imported}"
                )

            page_id = imported.get("page_id")
            if not page_id:
                raise ValueError(
                    f"Import of {self.PAGE_TITLE} succeeded "
                    "but returned no page_id."
                )

            page_name = imported.get("page_name") or self.PAGE_TITLE

            return {
                "skills": {
                    "success": True,
                    "pages": [
                        {
                            "page_id": page_id,
                            "page_name": page_name,
                            "file_path": imported.get("path"),
                            "questions": open_questions,
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
                            "Successfully extracted skills and competencies "
                            f"and imported the {page_name} page."
                        )
                    )
                ],
            }

        except Exception as exc:
            return {
                "skills": {
                    "success": False,
                    "pages": [],
                    "open_questions": [],
                },
                "metadata": {
                    **state.get("metadata", {}),
                    "error": f"ExtractSkills failed: {exc}",
                },
                "messages": [
                    AIMessage(
                        content=f"Skills extraction failed: {exc}"
                    )
                ],
            }
