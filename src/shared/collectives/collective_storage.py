
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
    """Protokolliert eine Storage-Operation mit run_id und graph_id."""
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
    """Ermittelt den vollständigen Dateipfad einer Collective-Seite."""
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
    """Liest einen Wert aus einem Dictionary oder Objektattribut."""
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
    """Extrahiert den Dateiinhalt aus einer WebDAV-Antwort."""
    if isinstance(response, str):
        return response

    if isinstance(response, dict):
        for key in ("content", "text", "body", "data"):
            value = response.get(key)
            if isinstance(value, str):
                return value

    return str(response)


def extract_etag(response: Any) -> str | None:
    """Extrahiert den ETag aus direkten oder verschachtelten MCP-Antworten."""
    if isinstance(response, str):
        try:
            response = json.loads(response)
        except (json.JSONDecodeError, TypeError):
            return None

    if not isinstance(response, dict):
        return None

    # Direkte WebDAV-Antwort oder structuredContent.
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

    # MCP-Tool-Antwort: content[0]["text"] enthält JSON.
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
    """Liest eine Datei über WebDAV im Markdown-Modus."""
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
    Schreibt Markdown unter Verwendung eines zuvor gelesenen ETags.

    Vor jedem Schreibversuch wird die aktuelle Datei gelesen. Der ETag
    wird mit if_match übergeben, damit Änderungen zwischen Lesen und
    Schreiben nicht unbemerkt überschrieben werden.

    Wenn die Datei nicht gelesen werden kann oder kein ETag vorliegt,
    wird der Schreibvorgang abgebrochen.
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
        # Immer zuerst den aktuellen Stand der Datei lesen.
        read_response = await read_markdown_file(
            tools,
            path,
            config=config,
        )

        current_etag = extract_etag(read_response)

        if not current_etag:
            raise RuntimeError(
                f"Die Datei {path!r} wurde vor dem Schreiben gelesen, "
                "aber die WebDAV-Antwort enthält keinen ETag. "
                "Der Schreibvorgang wird aus Sicherheitsgründen abgebrochen."
            )

        await _log_storage_event(
            config,
            operation,
            "etag_obtained",
            path=path,
            etag=current_etag,
        )

        # Den aktuellen ETag als Schreibbedingung übergeben.
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
    Schreibt Markdown mit ETag-Prüfung und kontrolliert anschließend
    den tatsächlich gespeicherten Inhalt durch erneutes Lesen.
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
        # write_markdown_file liest unmittelbar vor dem Schreiben
        # die Datei und übergibt ihren ETag als if_match.
        write_response = await write_markdown_file(
            tools,
            path,
            content,
            config=config,
        )

        # Anschließend den gespeicherten Stand erneut lesen.
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
                f"Die Markdown-Datei {path!r} wurde geschrieben, "
                "aber die anschließende Inhaltsprüfung ist fehlgeschlagen."
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
