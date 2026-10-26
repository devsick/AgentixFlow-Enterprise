from typing import Any, Dict
import json


def extract_mcp_structured_content(result: Any) -> Dict[str, Any]:
    """
    Extract the structured application payload from an MCP tool result.

    MCP/LangChain tool results can arrive either as:
        - a Python dict
        - a JSON string containing a dict

    When structuredContent is available, it is the preferred
    machine-readable payload.

    Example:

        {
            "_meta": None,
            "content": [...],
            "structuredContent": {
                "success": True,
                "collectives": [...]
            },
            "isError": False,
            "resultType": "complete"
        }

    Returns:
        The contents of `structuredContent` as a dictionary.

    Raises:
        RuntimeError: If the result cannot be normalized or does not
                      contain a valid structuredContent dictionary.
    """

    # ---------------------------------------------------------
    # 1. Normalize outer result
    # ---------------------------------------------------------

    if isinstance(result, str):
        try:
            result = json.loads(result)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Could not parse MCP tool result as JSON: {exc}"
            ) from exc

    if not isinstance(result, dict):
        raise RuntimeError(
            "Unexpected MCP tool result type: "
            f"expected dict or JSON string, "
            f"got {type(result).__name__}."
        )

    # ---------------------------------------------------------
    # 2. Check MCP error flag
    # ---------------------------------------------------------

    if result.get("isError") is True:
        raise RuntimeError(
            f"MCP tool returned an error: {result}"
        )

    # ---------------------------------------------------------
    # 3. Extract structuredContent
    # ---------------------------------------------------------

    structured_content = result.get("structuredContent")

    if structured_content is None:
        raise RuntimeError(
            "MCP tool result does not contain 'structuredContent'."
        )

    # ---------------------------------------------------------
    # 4. Normalize structuredContent
    # ---------------------------------------------------------

    if isinstance(structured_content, str):
        try:
            structured_content = json.loads(structured_content)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "Could not parse MCP 'structuredContent' as JSON: "
                f"{exc}"
            ) from exc

    if not isinstance(structured_content, dict):
        raise RuntimeError(
            "Unexpected 'structuredContent' type: "
            f"expected dict, "
            f"got {type(structured_content).__name__}."
        )

    return structured_content