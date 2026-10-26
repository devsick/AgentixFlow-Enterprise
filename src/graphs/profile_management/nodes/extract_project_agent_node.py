
# extract_project_agent_node.py

from langchain_core.messages import AIMessage

from src.graphs.profile_management.state import ProfileManagementState
from src.graphs.profile_management.agents.extract_project.extract_project_agent import (
    ExtractProjectAgent,
)
from src.shared.node_wrapper import observe_node
from src.shared.collective_functions import (
    CollectiveConfig,
    import_collective_entries,
    error_result,
)
from src.shared.collectives.collective_pages import(
    sanitize_page_name
)





class ExtractProjectAgentNode:
    OVERVIEW_TITLE = "100-Projects"
    PROJECT_PREFIX = "Project"
    FIRST_PROJECT_NUMBER = 101

    # Diese Felder bitte mit der bestehenden Project-Node abgleichen.
    PROJECT_SCALAR_FIELDS = [
        "project_name",
        "project_start",
        "project_end",
        "company_organization",
        "associated_employment",
        "role",
        "description",
        "initial_situation",
        "goals_tasks",
    ]

    PROJECT_LIST_FIELDS = [
        "own_activities",
        "responsibilities",
        "skills",
        "methods_technologies",
        "stakeholders_collaboration",
        "results",
        "measurable_results",
        "sources",
        "notes",
        "open_questions",
    ]

    def __init__(self):
        self.agent = ExtractProjectAgent()

    # ------------------------------------------------------------------
    # Project naming and rendering
    # ------------------------------------------------------------------

    @staticmethod
    def _project_name(entry: dict) -> str:
        name = entry.get("project_name", "").strip()

        if not name:
            raise ValueError("Project is missing 'project_name'.")

        return sanitize_page_name(name)

    @classmethod
    def _render_project_markdown(cls, entry: dict) -> str:
        name = cls._project_name(entry)

        sections = [
            f"# Project: {name}",
            "",
            "## Master Data",
            f"- Company / Organization: {entry['company_organization']}",
            f"- Associated Employment: {entry['associated_employment']}",
            f"- Project start: {entry['project_start']}",
            f"- Project end: {entry['project_end']}",
            f"- Role: {entry['role']}",
            "",
            "## Initial Situation",
            entry["initial_situation"].strip() or "None",
            "",
            "## Description",
            entry["description"].strip() or "None",
            "",
            "## Goals and Tasks",
            entry["goals_tasks"].strip() or "None",
        ]

        rendered_fields = [
            ("Own Activities", "own_activities"),
            ("Responsibilities", "responsibilities"),
            ("Skills", "skills"),
            ("Methods / Technologies", "methods_technologies"),
            ("Stakeholders / Collaboration", "stakeholders_collaboration"),
            ("Results", "results"),
            ("Measurable Results", "measurable_results"),
            ("Sources", "sources"),
            ("Notes", "notes"),
            ("Open Questions", "open_questions"),
        ]

        for heading, field in rendered_fields:
            sections.extend([
                "",
                f"## {heading}",
                "\n".join(f"- {item}" for item in entry[field]) or "- None",
            ])

        return "\n".join(sections).rstrip() + "\n"

    @staticmethod
    def _render_overview_markdown(entries: list[dict]) -> str:
        lines = ["# Projects", ""]

        if not entries:
            lines.append("No projects available.")
        else:
            for entry in entries:
                name = entry.get("entry_name", "Unnamed project")
                title = entry.get("page_title", name)
                lines.append(f"- [{name}]({title})")

        return "\n".join(lines).rstrip() + "\n"

    # ------------------------------------------------------------------
    # Node
    # ------------------------------------------------------------------

    @observe_node("extract_project_agent_node")
    async def __call__(self, state: ProfileManagementState) -> dict:
        try:
            documents = state.get("documents", [])
            collective = state.get("collective")
            mcp_client = state.get("mcp_client")

            if not isinstance(documents, list):
                raise ValueError("documents must be a list.")

            if not isinstance(collective, dict):
                raise ValueError("Collective information is missing.")

            if mcp_client is None:
                raise ValueError("mcp_client is missing from state.")

            collective_id = int(collective["id"])

            documents = [
                document
                for document in documents
                if isinstance(document, dict)
                and isinstance(document.get("content"), str)
                and document["content"].strip()
            ]

            if not documents:
                raise ValueError("No usable documents found.")

            result = await self.agent.run(documents=documents)
            projects = result.get("projects")

            config = CollectiveConfig(
                mode="overview_with_entries",
                overview_title=self.OVERVIEW_TITLE,
                entry_prefix=self.PROJECT_PREFIX,
                first_entry_number=self.FIRST_PROJECT_NUMBER,
                scalar_fields=self.PROJECT_SCALAR_FIELDS,
                list_fields=self.PROJECT_LIST_FIELDS,
                get_entry_name=self._project_name,
                render_entry=self._render_project_markdown,
                render_overview=self._render_overview_markdown,
                graph_id=state.get("graph_id"),
                run_id=state.get("run_id"),
                )

            imported = await import_collective_entries(
                client=mcp_client,
                collective_id=collective_id,
                entries=projects,
                config=config,
            )

            errors = imported.get("errors", [])
            metadata = dict(state.get("metadata") or {})
            metadata["error"] = "; ".join(errors) if errors else None

            return {
                "projects": {
                    "success": imported.get("success", False),
                    "overview_page": imported.get("overview_page"),
                    "pages": imported.get("pages", []),
                    "open_questions": imported.get("open_questions", []),
                },
                "metadata": metadata,
                "messages": [
                    AIMessage(
                        content=(
                            "Project extraction and synchronization "
                            f"completed: {len(imported.get('pages', []))}/"
                            f"{len(projects)} project pages processed."
                        )
                    )
                ],
            }

        except Exception as exc:
            return error_result(
                state,
                key="projects",
                message=f"ExtractProject failed: {exc}",
            )
