
from pathlib import PurePosixPath
from typing import Any
import json

from src.shared.collectives.collective_tools import (
    CollectiveConfig,
    MonitoredTool,
    call_collective_tool,
    log_collective_tool_event,
    utc_timestamp,
)


async def _log_storage_event(
    config: CollectiveConfig | None,
    operation: str,
    phase: str,
    **details: Any,
) -> None:
    """Is recording a storage-operation with run_id and graph_id."""
    if config is None:
        return

    await log_collective_tool_event(
        config,
        {
            "event_type": "collective_storage_operation",
            "timestamp": utc_timestamp(),
            "operation": operation,
            "phase": phase,
            **details,
        },
    )


def get_collective_page_path(page: Any) -> PurePosixPath | None:
    """Determines the complete filepath of the collective page"""
    collective_path = get_page_value(
        page,
        "collectivePath",
        "collective_path",
    )
    file_path = get_page_value(
        page,
        "filePath",
        "file_path",
        "path",
    )
    file_name = get_page_value(
        page,
        "fileName",
        "file_name",
    )

    if not collective_path or not file_name:
        return None

    try:
        path = PurePosixPath(str(collective_path))

        if file_path:
            path = path / str(file_path)

        path = path / str(file_name)
        return path

    except (TypeError, ValueError):
        return None


def get_page_value(
    page: Any,
    *keys: str,
    default: Any = None,
) -> Any:
    """Extracs the value from a dictionary or object property."""
    if isinstance(page, dict):
        for key in keys:
            if key in page and page[key] is not None:
                return page[key]

    for key in keys:
        result = getattr(page, key, None)
        if result is not None:
            return result

    return default


def extract_file_content(response: Any) -> str:
    """Extracts the file content from a webDav response"""
    if isinstance(response, str):
        return response

    if isinstance(response, dict):
        for key in ("content", "text", "body", "data"):
            value = response.get(key)
            if isinstance(value, str):
                return value

    return str(response)


def extract_etag(response: Any) -> str | None:
    """Extracts the ETag from the direct or nested mcp-responses"""
    if isinstance(response, str):
        try:
            response = json.loads(response)
        except (json.JSONDecodeError, TypeError):
            return None

    if not isinstance(response, dict):
        return None

    # Direct WebDAV response or structuredContent.
    for key in ("etag", "eTag", "ETag"):
        value = response.get(key)
        if value is not None and str(value).strip():
            return str(value).strip().strip('"')

    for key in ("structuredContent", "structured_content", "data"):
        nested = response.get(key)
        if isinstance(nested, dict):
            etag = extract_etag(nested)
            if etag:
                return etag

    # MCP-Tool response: content[0]["text"] contains JSON.
    content_items = response.get("content")
    if isinstance(content_items, list):
        for item in content_items:
            if not isinstance(item, dict):
                continue

            text = item.get("text")
            if not isinstance(text, str):
                continue

            try:
                parsed = json.loads(text)
            except (json.JSONDecodeError, TypeError):
                continue

            etag = extract_etag(parsed)
            if etag:
                return etag



async def read_markdown_file(
    tools: dict[str, MonitoredTool],
    path: str,
    config: CollectiveConfig | None = None,
) -> Any:
    """Reads a file with WebDav in markdown-format"""
    operation = "read_markdown_file"

    await _log_storage_event(
        config,
        operation,
        "started",
        path=path,
        parse_document="markdown",
    )

    try:
        response = await call_collective_tool(
            tools,
            "nc_webdav_read_file",
            {
                "path": path,
                "parse_document": "markdown",
            },
        )

        content = extract_file_content(response)
        etag = extract_etag(response)

        await _log_storage_event(
            config,
            operation,
            "completed",
            path=path,
            parse_document="markdown",
            content_length=len(content),
            etag=etag,
        )

        return response

    except Exception as exc:
        await _log_storage_event(
            config,
            operation,
            "failed",
            path=path,
            parse_document="markdown",
            error=str(exc),
            error_type=type(exc).__name__,
        )
        raise


async def write_markdown_file(
    tools: dict[str, MonitoredTool],
    path: str,
    content: str,
    config: CollectiveConfig | None = None,
) -> Any:
    """
    Writes Markdown using a previously read ETag.

    The current file is read before every write attempt. The ETag
    is passed via if_match to ensure that changes between reading and
    writing are not overwritten unnoticed.

    If the file cannot be read or no ETag is available,
    the write operation is aborted.
    """
    operation = "write_markdown_file"

    await _log_storage_event(
        config,
        operation,
        "started",
        path=path,
        content_length=len(content),
        content_type="text/markdown",
    )

    try:
        # Always read the current state of the file first.
        read_response = await read_markdown_file(
            tools,
            path,
            config=config,
        )

        current_etag = extract_etag(read_response)

        if not current_etag:
            raise RuntimeError(
                f"The file {path!r} was read before writing, "
                "but the WebDAV response does not contain an ETag. "
                "The write operation is aborted for security reasons."
            )

        await _log_storage_event(
            config,
            operation,
            "etag_obtained",
            path=path,
            etag=current_etag,
        )

        # Pass the current ETag as a write condition.
        response = await call_collective_tool(
            tools,
            "nc_webdav_write_file",
            {
                "path": path,
                "content": content,
                "content_type": "text/markdown",
                "if_match": current_etag,
            },
        )

        new_etag = extract_etag(response)

        await _log_storage_event(
            config,
            operation,
            "completed",
            path=path,
            content_length=len(content),
            previous_etag=current_etag,
            etag=new_etag,
        )

        return response

    except Exception as exc:
        await _log_storage_event(
            config,
            operation,
            "failed",
            path=path,
            content_length=len(content),
            error=str(exc),
            error_type=type(exc).__name__,
        )
        raise


async def write_and_verify_markdown(
    tools: dict[str, MonitoredTool],
    path: str,
    content: str,
    config: CollectiveConfig | None = None,
) -> Any:
    """
    Writes Markdown with ETag verification and subsequently verifies
    the actually stored content by re-reading.
    """
    operation = "write_and_verify_markdown"

    await _log_storage_event(
        config,
        operation,
        "started",
        path=path,
        expected_content_length=len(content),
    )

    try:
        # write_markdown_file reads the file immediately before writing
        # and passes its ETag as if_match.
        write_response = await write_markdown_file(
            tools,
            path,
            content,
            config=config,
        )

        # Subsequently re-read the stored state.
        read_response = await read_markdown_file(
            tools,
            path,
            config=config,
        )

        actual_content = extract_file_content(read_response)
        verified = actual_content == content

        if not verified:
            await _log_storage_event(
                config,
                operation,
                "verification_failed",
                path=path,
                expected_content_length=len(content),
                actual_content_length=len(actual_content),
                write_etag=extract_etag(write_response),
                read_etag=extract_etag(read_response),
            )

            raise RuntimeError(
                f"The Markdown file {path!r} was written, "
                "but the subsequent content verification failed."
            )

        await _log_storage_event(
            config,
            operation,
            "completed",
            path=path,
            content_length=len(actual_content),
            verified=True,
            etag=extract_etag(read_response),
        )

        return read_response

    except Exception as exc:
        await _log_storage_event(
            config,
            operation,
            "failed",
            path=path,
            expected_content_length=len(content),
            error=str(exc),
            error_type=type(exc).__name__,
        )
        raise
