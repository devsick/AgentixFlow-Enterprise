
from typing import Any, Dict
import json
import re
from pathlib import Path

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from src.settings.config_store import config_store
from src.shared.reasoning_chat_openai import ReasoningChatOpenAI


class ExtractCertificatesAgent:
    """
    Agent responsible for extracting substantiated certificates
    from supplied documents and generating the 031-Zertifikate
    Markdown content.

    This agent performs extraction only. Page creation, updates,
    and other external operations are handled by the calling node.
    """

    PROMPT_PATH = Path(__file__).with_name(
        "extract_certificates_systemprompt.md"
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
        """Extract and validate the JSON object returned by the LLM."""

        if isinstance(content, list):
            content = "".join(
                block.get("text", "")
                for block in content
                if isinstance(block, dict)
            )

        if not isinstance(content, str):
            raise ValueError(
                "LLM response content is not a string."
            )

        match = re.search(
            r"```json\s*(.*?)\s*```",
            content,
            re.DOTALL | re.IGNORECASE,
        )

        if match:
            content = match.group(1)
        else:
            start = content.find("{")
            end = content.rfind("}")

            if start != -1 and end != -1:
                content = content[start:end + 1]

        try:
            result = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"LLM returned invalid JSON: {exc}"
            ) from exc

        if not isinstance(result, dict):
            raise ValueError(
                "LLM response must contain a JSON object."
            )

        if not isinstance(result.get("content"), str):
            raise ValueError(
                "Agent response must contain a string field 'content'."
            )

        if not isinstance(result.get("open_questions"), list):
            raise ValueError(
                "Agent response must contain a list field 'open_questions'."
            )

        if not all(
            isinstance(question, str)
            for question in result["open_questions"]
        ):
            raise ValueError(
                "All entries in 'open_questions' must be strings."
            )

        return {
            "content": result["content"],
            "open_questions": result["open_questions"],
        }

    async def run(
        self,
        documents: list[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Extracts substantiated certificates from the supplied documents.

        Returns:
            A dictionary containing:
            - content: Complete Markdown content for 031-Zertifikate.
            - open_questions: Relevant unanswered certificate questions.

        No tools or external services are called by this method,
        apart from the configured LLM invocation.
        """

        if not isinstance(documents, list) or not documents:
            raise ValueError(
                "No documents were provided to ExtractCertificatesAgent."
            )

        doc_parts = []

        for index, doc in enumerate(documents, start=1):
            if not isinstance(doc, dict):
                continue

            path_value = doc.get("path")
            name_value = doc.get("name")

            path = (
                path_value
                if isinstance(path_value, str) and path_value.strip()
                else "unknown"
            )

            name = (
                name_value
                if isinstance(name_value, str) and name_value.strip()
                else Path(path).name
            )

            content = doc.get("content", "")

            if not isinstance(content, str) or not content.strip():
                continue

            doc_parts.append(
                f"--- Document {index}: {name} (Path: {path}) ---\n"
                f"{content}\n"
            )

        if not doc_parts:
            raise ValueError(
                "None of the provided documents contain usable text."
            )

        doc_content = "\n".join(doc_parts)

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(
                content=(
                    "Extract and consolidate all substantiated certificates "
                    "from the following source documents. Follow the system "
                    "prompt exactly and return only the required JSON object.\n\n"
                    f"Source Documents:\n{doc_content}"
                )
            ),
        ]

        response = await self.llm.ainvoke(messages)

        return self._parse_json_content(response.content)
