
from typing import Any, Dict
import json
import re
from pathlib import Path

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from src.settings.config_store import config_store
from src.shared.reasoning_chat_openai import ReasoningChatOpenAI


class ExtractProjectAgent:
    """
    Agent responsible for analyzing supplied documents and extracting
    structured project information.

    The agent only analyzes documents and returns JSON.
    Page creation and updates are handled by the node.
    """

    PROMPT_PATH = Path(__file__).with_name("extract_project_systemprompt.md")

    PROJECT_STRING_FIELDS = (
        "project_name",
        "project_start",
        "project_end",
        "company_organization",
        "associated_employment",
        "role",
        "description",
        "initial_situation",
        "goals_tasks",
    )

    PROJECT_LIST_FIELDS = (
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
    )

    def __init__(self):
        with self.PROMPT_PATH.open("r", encoding="utf-8") as file:
            self.system_prompt = file.read()

        self._init_llm()

    def _init_llm(self) -> None:
        profile = config_store.llm_profiles.get("oogabooga")

        if not profile:
            raise ValueError(
                "LLM Profile 'oogabooga' not found in configuration."
            )

        LLMClass = (
            ReasoningChatOpenAI
            if getattr(profile, "type", None) == "reasoning"
            else ChatOpenAI
        )

        self.llm = LLMClass(
            base_url=profile.url,
            api_key=profile.api_key,
            model=profile.model,
            temperature=0.0,
            streaming=True,
            stream_usage=True,
            use_responses_api=False,
            extra_body=profile.extra_body,
        )

    def _parse_json_content(self, content: Any) -> Dict[str, Any]:
        """Parse and validate the JSON returned by the LLM."""

        if isinstance(content, list):
            content = "".join(
                block.get("text", "")
                for block in content
                if isinstance(block, dict)
                and isinstance(block.get("text", ""), str)
            )

        if not isinstance(content, str):
            raise ValueError("LLM response content is not a string.")

        content = content.strip()

        # Accept JSON wrapped in a Markdown code fence.
        match = re.search(
            r"```(?:json)?\s*(.*?)\s*```",
            content,
            re.DOTALL | re.IGNORECASE,
        )

        if match:
            content = match.group(1).strip()
        else:
            # Tolerate explanatory text before or after the JSON object.
            start = content.find("{")
            end = content.rfind("}")

            if start != -1 and end != -1 and end >= start:
                content = content[start:end + 1]

        try:
            result = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Agent response is not valid JSON: {exc}"
            ) from exc

        if not isinstance(result, dict):
            raise ValueError(
                "Agent response must contain a JSON object."
            )

        projects = result.get("projects")

        if not isinstance(projects, list):
            raise ValueError(
                "Agent response must contain a list field 'projects'."
            )

        validated_projects = []

        for index, project in enumerate(projects, start=1):
            if not isinstance(project, dict):
                raise ValueError(
                    f"Project at index {index} must be a JSON object."
                )

            missing_fields = [
                field
                for field in (
                    self.PROJECT_STRING_FIELDS
                    + self.PROJECT_LIST_FIELDS
                )
                if field not in project
            ]

            if missing_fields:
                raise ValueError(
                    f"Project at index {index} is missing fields: "
                    f"{', '.join(missing_fields)}."
                )

            for field in self.PROJECT_STRING_FIELDS:
                value = project[field]

                if not isinstance(value, str):
                    raise ValueError(
                        f"Project at index {index}: field '{field}' "
                        "must be a string."
                    )

            for field in self.PROJECT_LIST_FIELDS:
                value = project[field]

                if not isinstance(value, list):
                    raise ValueError(
                        f"Project at index {index}: field '{field}' "
                        "must be a list."
                    )

                if not all(isinstance(item, str) for item in value):
                    raise ValueError(
                        f"Project at index {index}: all entries in "
                        f"'{field}' must be strings."
                    )

            if not project["project_name"].strip():
                raise ValueError(
                    f"Project at index {index} has an empty 'project_name'."
                )

            validated_projects.append(project)

        # Return a normalized object with the validated project list.
        result["projects"] = validated_projects
        return result

    async def run(
        self,
        documents: list[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Analyze the already-loaded documents and return structured
        project information as JSON.
        """

        if not documents:
            raise ValueError(
                "No documents were provided to ExtractProjectAgent."
            )

        document_sections = []

        for index, doc in enumerate(documents, start=1):
            name = doc.get("name") or Path(
                doc.get("path", "unknown")
            ).name
            path = doc.get("path", "unknown")
            content = doc.get("content", "")

            if not isinstance(content, str) or not content.strip():
                continue

            document_sections.append(
                f"--- Document {index}: {name} (Path: {path}) ---\n"
                f"{content}"
            )

        if not document_sections:
            raise ValueError(
                "None of the provided documents contain usable text."
            )

        doc_content = "\n\n".join(document_sections)

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(
                content=(
                    "Analyze the following source documents and return "
                    "the project data in the required JSON format.\n\n"
                    f"Source Documents:\n{doc_content}"
                )
            ),
        ]

        response = await self.llm.ainvoke(messages)

        return self._parse_json_content(response.content)
