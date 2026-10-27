
from typing import Any, Dict

from langchain_core.messages import AIMessage

from src.graphs.profile_management.state import ProfileManagementState
from src.graphs.profile_management.agents.extract_certificates.extract_certificates_agent import (
    ExtractCertificatesAgent,
)
from src.shared.node_wrapper import observe_node
from src.shared.collective_functions import (
    CollectiveConfig,
    import_single_page,
)


class ExtractCertificatesAgentNode:
    """
    Node that calls ExtractCertificatesAgent and writes the resulting
    certificate page to the Collective when substantiated certificates
    are found.

    The agent performs extraction only. All page operations are handled
    deterministically by this node.
    """

    PAGE_TITLE = "031-Zertifikate"

    def __init__(self):
        self.agent = ExtractCertificatesAgent()

    @observe_node("extract_certificates_agent_node")
    async def __call__(
        self,
        state: ProfileManagementState,
    ) -> Dict[str, Any]:
        # 1. Retrieve data from the state.
        collective = state.get("collective")
        documents = state.get("documents", [])

        if not collective:
            return {
                "certificates": {
                    "success": False,
                    "pages": [],
                    "open_questions": [],
                },
                "metadata": {
                    **state.get("metadata", {}),
                    "error": "Collective information missing from state.",
                },
                "messages": [
                    AIMessage(
                        content=(
                            "Error: Collective information is missing. "
                            "Certificate extraction was not started."
                        )
                    )
                ],
            }

        # 2. Extract Collective ID and name.
        collective_id = collective.get("id")
        collective_name = collective.get("name")

        if not collective_id or not collective_name:
            return {
                "certificates": {
                    "success": False,
                    "pages": [],
                    "open_questions": [],
                },
                "metadata": {
                    **state.get("metadata", {}),
                    "error": (
                        "Collective ID or collective name is missing."
                    ),
                },
                "messages": [
                    AIMessage(
                        content=(
                            "Error: The collective ID or collective name "
                            "is missing. Certificate extraction was not started."
                        )
                    )
                ],
            }

        # 3. Validate the documents.
        if not isinstance(documents, list):
            return {
                "certificates": {
                    "success": False,
                    "pages": [],
                    "open_questions": [],
                },
                "metadata": {
                    **state.get("metadata", {}),
                    "error": "documents must be a list.",
                },
                "messages": [
                    AIMessage(
                        content=(
                            "Error: The loaded documents have an invalid format. "
                            "Certificate extraction was not started."
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
                "certificates": {
                    "success": False,
                    "pages": [],
                    "open_questions": [],
                },
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
                            "were found. Certificate extraction was not started."
                        )
                    )
                ],
            }

        # 4. Retrieve the MCP client from the state.
        client = state.get("mcp_client")

        if client is None:
            return {
                "certificates": {
                    "success": False,
                    "pages": [],
                    "open_questions": [],
                },
                "metadata": {
                    **state.get("metadata", {}),
                    "error": "MCP client missing from state.",
                },
                "messages": [
                    AIMessage(
                        content=(
                            "Error: The MCP client is unavailable. "
                            "Certificate extraction was not started."
                        )
                    )
                ],
            }

        try:
            # 5. Call the agent. It extracts content only and executes no tools.
            result = await self.agent.run(
                documents=document_contents,
            )

            if not isinstance(result, dict):
                raise ValueError(
                    "ExtractCertificatesAgent returned an invalid result; "
                    "expected a dictionary."
                )

            content = result.get("markdown")
            open_questions = result.get("open_questions", [])

            if not isinstance(content, str) or not content.strip():
                raise ValueError(
                    "ExtractCertificatesAgent returned empty or invalid "
                    "page content."
                )

            if not isinstance(open_questions, list):
                raise ValueError(
                    "ExtractCertificatesAgent returned invalid open_questions; "
                    "expected a list."
                )

            if not all(
                isinstance(question, str)
                for question in open_questions
            ):
                raise ValueError(
                    "ExtractCertificatesAgent returned non-string "
                    "open questions."
                )

            # 6. Determine whether the extracted page contains certificates.
            #
            # The SystemPrompt defines the page structure and requires
            # a separate level-two heading for each certificate.
            # The fixed top-level heading is "# Zertifikate".
            certificate_headings = [
                line.strip()
                for line in content.splitlines()
                if line.strip().startswith("## ")
                and line.strip() not in {
                    "## Quellen",
                    "## Notes",
                }
            ]

            if not certificate_headings:
                # No certificates were found. Do not create or update a page.
                return {
                    "certificates": {
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
                                "Certificate extraction completed successfully "
                                f"for collective '{collective_name}'. "
                                "No substantiated certificates were found. "
                                "No page was created or updated."
                            )
                        )
                    ],
                }

            # 7. Build the configuration for a single page.
            config = CollectiveConfig(
                mode="single_page",
                page_title=self.PAGE_TITLE,
                graph_id=state.get("graph_id"),
                run_id=state.get("run_id"),
            )

            # 8. Create or update the certificate page using the shared function.
            imported = await import_single_page(
                client=client,
                collective_id=collective_id,
                page_title=config.page_title,
                content=content,
                config=config,
                collective=collective,
            )

            # 9. Verify the import result.
            if not isinstance(imported, dict) or not imported.get("success"):
                raise RuntimeError(
                    "Certificate page import did not complete successfully."
                )

            page_id = imported.get("page_id")

            if not page_id:
                raise RuntimeError(
                    "Certificate page import reported success but returned "
                    "no Page ID."
                )

            page_name = imported.get("page_name", self.PAGE_TITLE)

            # 10. Update the state only after successful writing.
            return {
                "certificates": {
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
                            "Certificate extraction completed successfully "
                            f"for collective '{collective_name}'. "
                            f"Page '{page_name}' was written and verified."
                        )
                    )
                ],
            }

        except Exception as exc:
            return {
                "certificates": {
                    "success": False,
                    "pages": [],
                    "open_questions": [],
                },
                "metadata": {
                    **state.get("metadata", {}),
                    "error": f"ExtractCertificates failed: {exc}",
                },
                "messages": [
                    AIMessage(
                        content=(
                            "Error during certificate extraction: "
                            f"{exc}"
                        )
                    )
                ],
            }
