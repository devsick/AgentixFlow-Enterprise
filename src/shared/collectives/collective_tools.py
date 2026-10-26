import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from src.shared.monitoring_writer import monitoring_writer


PageMode = str


COLLECTIVE_ALLOWED_TOOLS = [
    "collectives_get_pages",
    "collectives_create_page",
    "collectives_get_page",
    "nc_webdav_read_file",
    "nc_webdav_write_file",
]

COLLECTIVE_REQUIRED_TOOLS = {
    "collectives_get_pages",
    "collectives_create_page",
    "collectives_get_page",
    "nc_webdav_read_file",
    "nc_webdav_write_file",
}


@dataclass
class CollectiveConfig:
    mode: PageMode = "single_page"

    allowed_tools: list[str] = field(
        default_factory=lambda: list(COLLECTIVE_ALLOWED_TOOLS)
    )
    required_tools: set[str] = field(
        default_factory=lambda: set(COLLECTIVE_REQUIRED_TOOLS)
    )

    graph_id: str | None = None
    run_id: str | None = None

    page_title: str = "001-Person"

    overview_title: str = ""
    entry_prefix: str = ""
    first_entry_number: int = 1

    scalar_fields: list[str] = field(default_factory=list)
    list_fields: list[str] = field(default_factory=list)

    # Funktionen aus den jeweiligen Nodes
    get_entry_name: Any = None
    render_entry: Any = None
    render_overview: Any = None

    # Rückwärtskompatible optionale Callbacks
    validate_callback: Any = None
    render_callback: Any = None

    refresh_retries: int = 3
    refresh_delay_seconds: float = 0.5


def utc_timestamp() -> str:
    """Gibt einen UTC-Zeitstempel im ISO-8601-Format zurück."""
    return datetime.now(timezone.utc).isoformat()


def json_safe(value: Any) -> Any:
    """Konvertiert Werte möglichst verlustarm in JSON-kompatible Objekte."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, dict):
        return {
            str(key): json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [json_safe(item) for item in value]

    if hasattr(value, "model_dump"):
        try:
            return json_safe(value.model_dump())
        except Exception:
            pass

    if hasattr(value, "dict") and callable(value.dict):
        try:
            return json_safe(value.dict())
        except Exception:
            pass

    if hasattr(value, "content"):
        try:
            return json_safe(value.content)
        except Exception:
            pass

    return str(value)


def extract_result(response: Any) -> Any:
    """
    Extrahiert den Nutzinhalt einer MCP-Antwort.

    Die ursprüngliche Antwort wird separat im Monitoring erfasst.
    """
    if not isinstance(response, dict):
        return response

    structured = response.get("structuredContent")

    if structured is None:
        structured = response.get("structured_content")

    if structured is not None:
        return structured

    return response


def _response_error(response: Any) -> str | None:
    """Ermittelt Fehler aus einer MCP-Antwort, sofern vorhanden."""
    if not isinstance(response, dict):
        return None

    if response.get("isError") is True:
        return str(
            response.get("error")
            or response.get("message")
            or response
        )

    structured = response.get("structuredContent")

    if structured is None:
        structured = response.get("structured_content")

    if isinstance(structured, dict):
        if structured.get("success") is False:
            return str(
                structured.get("error")
                or structured.get("message")
                or structured
            )

    if response.get("success") is False:
        return str(
            response.get("error")
            or response.get("message")
            or response
        )

    return None


def extract_list(value: Any, *keys: str) -> list:
    """Extrahiert eine Liste direkt oder aus einem bekannten Antwortfeld."""
    if isinstance(value, list):
        return value

    if isinstance(value, dict):
        for key in keys:
            candidate = value.get(key)
            if isinstance(candidate, list):
                return candidate

    return []


async def log_collective_tool_event(
    config: CollectiveConfig,
    event: dict,
) -> None:
    """
    Schreibt ein MCP-Tool-Event direkt in events.jsonl.

    Monitoringfehler dürfen den eigentlichen MCP-Aufruf nicht verhindern.
    """
    graph_id = config.graph_id
    run_id = config.run_id

    if not graph_id or not run_id:
        return

    event_type = event.get("event_type", "mcp_tool_call")

    details = {
        key: json_safe(value)
        for key, value in event.items()
        if key not in {"event_type", "timestamp"}
    }

    try:
        await monitoring_writer.log_event(
            graph_id=str(graph_id),
            run_id=str(run_id),
            event_type=event_type,
            details=details,
        )
    except Exception:
        # Monitoring darf die Fachoperation nicht blockieren.
        pass


class MonitoredTool:
    """Wrapper, der MCP-Aufrufe vor und nach der Ausführung protokolliert."""

    def __init__(
        self,
        tool: Any,
        config: CollectiveConfig,
    ):
        self.tool = tool
        self.config = config
        self.name = getattr(tool, "name", type(tool).__name__)

    async def ainvoke(self, arguments: dict) -> Any:
        started_at = time.perf_counter()

        base_event = {
            "event_type": "mcp_tool_call",
            "timestamp": utc_timestamp(),
            "tool_name": self.name,
            "arguments": json_safe(arguments),
        }

        await log_collective_tool_event(
            self.config,
            {
                **base_event,
                "phase": "started",
            },
        )

        try:
            result = await self.tool.ainvoke(arguments)

            duration_seconds = time.perf_counter() - started_at
            response_error = _response_error(result)

            if response_error:
                await log_collective_tool_event(
                    self.config,
                    {
                        **base_event,
                        "phase": "failed",
                        "duration_seconds": duration_seconds,
                        "result": json_safe(result),
                        "error": response_error,
                        "error_type": "MCPToolError",
                    },
                )
            else:
                await log_collective_tool_event(
                    self.config,
                    {
                        **base_event,
                        "phase": "completed",
                        "duration_seconds": duration_seconds,
                        "result": json_safe(result),
                    },
                )

            return result

        except Exception as exc:
            duration_seconds = time.perf_counter() - started_at

            await log_collective_tool_event(
                self.config,
                {
                    **base_event,
                    "phase": "failed",
                    "duration_seconds": duration_seconds,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
            )

            raise


async def load_collective_tools(
    client: Any,
    config: CollectiveConfig,
) -> dict[str, MonitoredTool]:
    """Lädt die benötigten MCP-Tools und versieht sie mit Monitoring."""
    try:
        tools = await client.get_tools(config.allowed_tools)
    except TypeError:
        # Fallback für MCP-Clients, deren get_tools keine Toolliste annimmt.
        tools = await client.get_tools()

    tools_by_name = {
        getattr(tool, "name", ""): tool
        for tool in tools
    }

    missing = config.required_tools - set(tools_by_name)

    if missing:
        raise RuntimeError(
            "Folgende erforderliche MCP-Tools fehlen: "
            + ", ".join(sorted(missing))
        )

    return {
        name: MonitoredTool(tools_by_name[name], config)
        for name in config.allowed_tools
        if name in tools_by_name
    }


async def call_collective_tool(
    tools: dict[str, MonitoredTool],
    tool_name: str,
    arguments: dict,
) -> Any:
    """Ruft ein MCP-Tool auf, prüft Fehler und extrahiert das Ergebnis."""
    tool = tools.get(tool_name)

    if tool is None:
        raise RuntimeError(
            f"MCP-Tool {tool_name!r} ist nicht verfügbar."
        )

    response = await tool.ainvoke(arguments)
    error = _response_error(response)

    if error:
        raise RuntimeError(
            f"MCP-Tool {tool_name!r} fehlgeschlagen: {error}"
        )

    return extract_result(response)
