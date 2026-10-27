
# extract_employments_agent_node.py

import re
from typing import Any

from langchain_core.messages import AIMessage

from src.graphs.profile_management.state import ProfileManagementState
from src.graphs.profile_management.agents.extract_employments.extract_employments_agent import (
    ExtractEmploymentAgent,
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





class ExtractEmploymentAgentNode:
    OVERVIEW_TITLE = "200-Employments"
    EMPLOYMENT_PREFIX = "Employment"
    FIRST_EMPLOYMENT_NUMBER = 201

    EMPLOYMENT_SCALAR_FIELDS = [
        "company_organization",
        "position",
        "employment_start",
        "employment_end",
        "location",
        "employment_type",
        "description",
    ]

    EMPLOYMENT_LIST_FIELDS = [
        "responsibilities",
        "own_activities",
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
        self.agent = ExtractEmploymentAgent()

    # ------------------------------------------------------------------
    # Employment naming and rendering
    # ------------------------------------------------------------------

    @staticmethod
    def _employment_name(entry: dict) -> str:
        company = entry.get("company_organization", "").strip()
        position = entry.get("position", "").strip()

        if company:
            name = company
            if position:
                name = f"{company} - {position}"
        else:
            name = "abstract_several"
            if position:
                name = f"{name} - {position}"

        start = entry.get("employment_start", "").strip() or "?"
        end = entry.get("employment_end", "").strip() or "present"

        return sanitize_page_name(f"{name} ({start}-{end})")

    @classmethod
    def _render_employment_markdown(cls, entry: dict) -> str:
        name = cls._employment_name(entry)

        sections = [
            f"# Employment: {name}",
            "",
            "## Master Data",
            f"- Company / Organization: {entry['company_organization']}",
            f"- Position: {entry['position']}",
            f"- Employment start: {entry['employment_start']}",
            f"- Employment end: {entry['employment_end']}",
            f"- Location: {entry['location']}",
            f"- Employment type: {entry['employment_type']}",
            "",
            "## Description",
            entry["description"].strip() or "None",
        ]

        rendered_fields = [
            ("Responsibilities", "responsibilities"),
            ("Own Activities", "own_activities"),
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
                "\n".join(f"- {item}" for item in entry[field]) if isinstance(entry.get(field), list) and entry[field] else "- None",
            ])

        return "\n".join(sections).rstrip() + "\n"

    @staticmethod
    def _render_overview_markdown(entries: list[dict]) -> str:
        lines = ["# Employments", ""]

        if not entries:
            lines.append("No employments available.")
        else:
            for entry in entries:
                name = entry.get("entry_name", "Unnamed employment")
                title = entry.get("page_title", name)
                lines.append(f"- [{name}]({title})")

        return "\n".join(lines).rstrip() + "\n"

    # ------------------------------------------------------------------
    # Node
    # ------------------------------------------------------------------

    @observe_node("extract_employment_agent_node")
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
            raw_employments = result.get("employments")

            config = CollectiveConfig(
                mode="overview_with_entries",
                overview_title=self.OVERVIEW_TITLE,
                entry_prefix=self.EMPLOYMENT_PREFIX,
                first_entry_number=self.FIRST_EMPLOYMENT_NUMBER,
                scalar_fields=self.EMPLOYMENT_SCALAR_FIELDS,
                list_fields=self.EMPLOYMENT_LIST_FIELDS,
                get_entry_name=self._employment_name,
                render_entry=self._render_employment_markdown,
                render_overview=self._render_overview_markdown,
                graph_id=state.get("graph_id"),
                run_id=state.get("run_id"),
            )

            imported = await import_collective_entries(
                client=mcp_client,
                collective_id=collective_id,
                entries=raw_employments,
                config=config,
            )

            errors = imported.get("errors", [])
            success = imported.get("success", False)

            metadata = dict(state.get("metadata") or {})
            metadata["error"] = "; ".join(errors) if errors else None

            return {
                "employments": {
                    "success": success,
                    "overview_page": imported.get("overview_page"),
                    "pages": imported.get("pages", []),
                    "open_questions": imported.get("open_questions", []),
                },
                "metadata": metadata,
                "messages": [
                    AIMessage(
                        content=(
                            "Employment extraction and synchronization "
                            f"completed: {len(imported.get('pages', []))}/"
                            f"{len(raw_employments)} employment pages processed."
                        )
                    )
                ],
            }

        except Exception as exc:
            result = error_result(exc)

            return {
                "employments": result,
                "metadata": {
                    **dict(state.get("metadata") or {}),
                    "error": f"ExtractEmployment failed: {exc}",
                },
                "messages": [
                    AIMessage(
                        content=(
                            f"ExtractEmployment failed: {exc}"
                        )
                    )
                ],
            }