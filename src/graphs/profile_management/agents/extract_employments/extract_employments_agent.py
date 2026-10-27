from typing import Any, Dict
import json
import re
from pathlib import Path

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from src.settings.config_store import config_store
from src.shared.reasoning_chat_openai import ReasoningChatOpenAI


class ExtractEmploymentAgent:
    """
    Agent responsible for analyzing supplied documents and extracting
    structured employment information.

    The agent only analyzes documents and returns JSON.
    Page creation and updates are handled by the node.
    """

    PROMPT_PATH = Path(__file__).with_name(
        "extract_employments_systemprompt.md"
    )

    EMPLOYMENT_STRING_FIELDS = (
        "company_organization",
        "employment_start",
        "employment_end",
        "position",
        "employment_type",
        "location",
        "description",
    )

    EMPLOYMENT_LIST_FIELDS = (
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
    )

    def __init__(self):
        with self.PROMPT_PATH.open(
            "r",
            encoding="utf-8",
        ) as file:
            self.system_prompt = file.read()

        self._init_llm()

    def _init_llm(self) -> None:
        profile = config_store.llm_profiles.get(
            "oogabooga"
        )

        if not profile:
            raise ValueError(
                "LLM Profile 'oogabooga' not found in configuration."
            )

        LLMClass = (
            ReasoningChatOpenAI
            if getattr(
                profile,
                "type",
                None,
            )
            == "reasoning"
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

    def _parse_json_content(
        self,
        content: Any,
    ) -> Dict[str, Any]:
        """Parse and validate the JSON returned by the LLM."""

        if isinstance(content, list):
            content = "".join(
                block.get("text", "")
                for block in content
                if isinstance(block, dict)
                and isinstance(
                    block.get("text", ""),
                    str,
                )
            )

        if not isinstance(content, str):
            raise ValueError(
                "LLM response content is not a string."
            )

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
            # Tolerate explanatory text before or after
            # the JSON object.
            start = content.find("{")
            end = content.rfind("}")

            if (
                start != -1
                and end != -1
                and end >= start
            ):
                content = content[
                    start : end + 1
                ]

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

        employments = result.get(
            "employments"
        )

        if not isinstance(employments, list):
            raise ValueError(
                "Agent response must contain a list field "
                "'employments'."
            )

        validated_employments = []

        for index, employment in enumerate(
            employments,
            start=1,
        ):
            if not isinstance(
                employment,
                dict,
            ):
                raise ValueError(
                    f"Employment at index {index} "
                    "must be a JSON object."
                )

            missing_fields = [
                field
                for field in (
                    self.EMPLOYMENT_STRING_FIELDS
                    + self.EMPLOYMENT_LIST_FIELDS
                )
                if field not in employment
            ]

            if missing_fields:
                raise ValueError(
                    f"Employment at index {index} is missing "
                    f"fields: {', '.join(missing_fields)}."
                )

            for field in self.EMPLOYMENT_STRING_FIELDS:
                value = employment[field]

                if not isinstance(
                    value,
                    str,
                ):
                    raise ValueError(
                        f"Employment at index {index}: "
                        f"field '{field}' must be a string."
                    )

            for field in self.EMPLOYMENT_LIST_FIELDS:
                value = employment[field]

                if not isinstance(
                    value,
                    list,
                ):
                    raise ValueError(
                        f"Employment at index {index}: "
                        f"field '{field}' must be a list."
                    )

                if not all(
                    isinstance(item, str)
                    for item in value
                ):
                    raise ValueError(
                        f"Employment at index {index}: "
                        f"all entries in '{field}' "
                        "must be strings."
                    )

            if not employment[
                "company_organization"
            ].strip():
                raise ValueError(
                    f"Employment at index {index} "
                    "has an empty 'company_organization'."
                )

            # Position is not strictly required to be non-empty.
            # We allow empty strings if no position is found.
            if not isinstance(employment.get("position"), str):
                raise ValueError(
                    f"Employment at index {index}: "
                    f"field 'position' must be a string."
                )

            validated_employments.append(
                employment
            )

        # Return a normalized object with the
        # validated employment list.
        result["employments"] = (
            validated_employments
        )

        return result

    async def run(
        self,
        documents: list[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Analyze the already-loaded documents and return
        structured employment information as JSON.
        """

        if not documents:
            raise ValueError(
                "No documents were provided to "
                "ExtractEmploymentAgent."
            )

        document_sections = []

        for index, doc in enumerate(
            documents,
            start=1,
        ):
            name = (
                doc.get("name")
                or Path(
                    doc.get(
                        "path",
                        "unknown",
                    )
                ).name
            )

            path = doc.get(
                "path",
                "unknown",
            )

            content = doc.get(
                "content",
                "",
            )

            if (
                not isinstance(
                    content,
                    str,
                )
                or not content.strip()
            ):
                continue

            document_sections.append(
                f"--- Document {index}: {name} "
                f"(Path: {path}) ---\n"
                f"{content}"
            )

        if not document_sections:
            raise ValueError(
                "None of the provided documents "
                "contain usable text."
            )

        doc_content = "\n\n".join(
            document_sections
        )

        messages = [
            SystemMessage(
                content=self.system_prompt
            ),
            HumanMessage(
                content=(
                    "Analyze the following source documents "
                    "and return the employment data in the "
                    "required JSON format.\n\n"
                    f"Source Documents:\n{doc_content}"
                )
            ),
        ]

        response = await self.llm.ainvoke(
            messages
        )

        return self._parse_json_content(
            response.content
        )