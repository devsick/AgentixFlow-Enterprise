
from typing import Any
import asyncio

from src.shared.collectives.collective_tools import (
    MonitoredTool,
    CollectiveConfig,
    call_collective_tool,
    extract_list,
    log_collective_tool_event,
    utc_timestamp,
)


async def _log_page_event(
    config: CollectiveConfig | None,
    operation: str,
    phase: str,
    **details: Any,
) -> None:
    """Schreibt ein High-Level-Event mit run_id und graph_id ins Monitoring."""
    if config is None:
        return

    await log_collective_tool_event(
        config,
        {
            "event_type": "collective_page_operation",
            "timestamp": utc_timestamp(),
            "operation": operation,
            "phase": phase,
            **details,
        },
    )


async def get_collective_pages(
    tools: dict[str, MonitoredTool],
    collective_id: str | int,
    config: CollectiveConfig | None = None,
) -> list[dict]:
    """Ruft alle Seiten eines Collectives ab und protokolliert den Vorgang."""
    operation = "get_collective_pages"

    await _log_page_event(
        config,
        operation,
        "started",
        collective_id=str(collective_id),
    )

    try:
        response = await call_collective_tool(
            tools,
            "collectives_get_pages",
            {
                "collective_id": collective_id,
            },
        )

        pages = extract_list(response, "pages", "results", "data")

        await _log_page_event(
            config,
            operation,
            "completed",
            collective_id=str(collective_id),
            page_count=len(pages),
        )

        return pages

    except Exception as exc:
        await _log_page_event(
            config,
            operation,
            "failed",
            collective_id=str(collective_id),
            error=str(exc),
            error_type=type(exc).__name__,
        )
        raise


async def create_collective_page(
    tools: dict[str, MonitoredTool],
    collective_id: str | int,
    parent_id: str | int,
    title: str,
    config: CollectiveConfig | None = None,
) -> Any:
    """Erstellt eine Collective-Seite und protokolliert das Ergebnis."""
    operation = "create_collective_page"

    arguments = {
        "collective_id": collective_id,
        "parent_id": parent_id,
        "title": title,
    }

    await _log_page_event(
        config,
        operation,
        "started",
        collective_id=str(collective_id),
        parent_id=str(parent_id),
        title=title,
    )

    try:
        result = await call_collective_tool(
            tools,
            "collectives_create_page",
            arguments,
        )

        await _log_page_event(
            config,
            operation,
            "completed",
            collective_id=str(collective_id),
            parent_id=str(parent_id),
            title=title,
            page_id=page_id(result),
            result=result,
        )

        return result

    except Exception as exc:
        await _log_page_event(
            config,
            operation,
            "failed",
            collective_id=str(collective_id),
            parent_id=str(parent_id),
            title=title,
            error=str(exc),
            error_type=type(exc).__name__,
        )
        raise


async def refresh_created_page(
    tools: dict[str, MonitoredTool],
    page_id_value: str | int,
    collective_id: str | int,
    retries: int = 3,
    delay_seconds: float = 0.5,
    config: CollectiveConfig | None = None,
) -> dict | None:
    """Lädt eine Seite erneut, falls sie noch nicht verfügbar ist."""
    operation = "refresh_created_page"
    attempts = max(1, retries)

    await _log_page_event(
        config,
        operation,
        "started",
        collective_id=str(collective_id),
        page_id=str(page_id_value),
        retries=attempts,
        delay_seconds=delay_seconds,
    )

    for attempt in range(1, attempts + 1):
        try:
            response = await call_collective_tool(
                tools,
                "collectives_get_page",
                {
                    "page_id": page_id_value,
                    "collective_id": collective_id,
                },
            )

            # Die MCP-Antwort kann die Seitendaten direkt oder in "page"
            # enthalten. Beide üblichen Formen werden unterstützt.
            if isinstance(response, dict):
                page = response.get("page")
                if isinstance(page, dict):
                    result_page = page
                elif page_id(response) is not None:
                    result_page = response
                else:
                    result_page = None

                if result_page is not None:
                    await _log_page_event(
                        config,
                        operation,
                        "completed",
                        collective_id=str(collective_id),
                        page_id=str(page_id_value),
                        attempt=attempt,
                        title=page_title(result_page),
                    )
                    return result_page

            await _log_page_event(
                config,
                operation,
                "retry",
                collective_id=str(collective_id),
                page_id=str(page_id_value),
                attempt=attempt,
                reason="Die Antwort enthielt keine erkennbaren Seitendaten.",
            )

        except Exception as exc:
            await _log_page_event(
                config,
                operation,
                "attempt_failed",
                collective_id=str(collective_id),
                page_id=str(page_id_value),
                attempt=attempt,
                error=str(exc),
                error_type=type(exc).__name__,
            )

            if attempt == attempts:
                await _log_page_event(
                    config,
                    operation,
                    "failed",
                    collective_id=str(collective_id),
                    page_id=str(page_id_value),
                    attempts=attempt,
                    error=str(exc),
                    error_type=type(exc).__name__,
                )
                raise

        if attempt < attempts:
            await asyncio.sleep(max(0, delay_seconds))

    await _log_page_event(
        config,
        operation,
        "failed",
        collective_id=str(collective_id),
        page_id=str(page_id_value),
        attempts=attempts,
        error="Die Seite war nach allen Versuchen nicht verfügbar.",
    )

    return None


async def ensure_page(
    tools: dict[str, MonitoredTool],
    collective_id: str | int,
    title: str,
    parent_id: str | int,
    config: CollectiveConfig | None = None,
) -> dict:
    """Findet eine Seite oder erstellt sie und lädt sie erneut."""
    operation = "ensure_page"

    await _log_page_event(
        config,
        operation,
        "started",
        collective_id=str(collective_id),
        title=title,
        parent_id=str(parent_id),
    )

    try:
        pages = await get_collective_pages(
            tools,
            collective_id=collective_id,
            config=config,
        )

        existing = find_page_by_title(pages, title)

        if existing is not None:
            await _log_page_event(
                config,
                operation,
                "completed",
                collective_id=str(collective_id),
                title=title,
                page_id=page_id(existing),
                action="existing",
            )
            return existing

        created = await create_collective_page(
            tools,
            collective_id=collective_id,
            parent_id=parent_id,
            title=title,
            config=config,
        )

        created_id = page_id(created)

        if created_id:
            refreshed = await refresh_created_page(
                tools,
                collective_id=collective_id,
                page_id_value=created_id,
                config=config,
            )

            if refreshed is not None:
                await _log_page_event(
                    config,
                    operation,
                    "completed",
                    collective_id=str(collective_id),
                    title=title,
                    page_id=page_id(refreshed),
                    action="created_and_refreshed",
                )
                return refreshed

        # Wenn die Erstellungsantwort selbst die Seitendaten enthält,
        # diese zurückgeben. Andernfalls den fehlgeschlagenen Refresh melden.
        if isinstance(created, dict) and page_id(created) is not None:
            await _log_page_event(
                config,
                operation,
                "completed",
                collective_id=str(collective_id),
                title=title,
                page_id=page_id(created),
                action="created_refresh_unavailable",
            )
            return created

        raise RuntimeError(
            f"Die Collective-Seite {title!r} konnte nicht erstellt "
            "oder erneut geladen werden."
        )

    except Exception as exc:
        await _log_page_event(
            config,
            operation,
            "failed",
            collective_id=str(collective_id),
            title=title,
            parent_id=str(parent_id),
            error=str(exc),
            error_type=type(exc).__name__,
        )
        raise


async def ensure_root_page(
    tools: dict[str, MonitoredTool],
    collective_id: str | int,
    title: str,
    config: CollectiveConfig | None = None,
) -> dict:
    """Stellt sicher, dass eine Seite unterhalb der Readme-Seite existiert.

    parent_id=0 wird hier bewusst nicht verwendet, da die API diesen Wert
    beim Erstellen einer Seite nicht als gültigen Parent akzeptiert.
    """
    operation = "ensure_root_page"

    await _log_page_event(
        config,
        operation,
        "started",
        collective_id=str(collective_id),
        title=title,
    )

    try:
        pages = await get_collective_pages(
            tools,
            collective_id=collective_id,
            config=config,
        )

        readme_page = next(
            (
                page
                for page in pages
                if str(
                    get_value(page, "fileName", "file_name", default="")
                ).casefold()
                == "readme.md"
            ),
            None,
        )

        if readme_page is None:
            raise RuntimeError(
                f"Die Readme-/Startseite des Collectives "
                f"{collective_id!r} konnte nicht gefunden werden."
            )

        readme_id = page_id(readme_page)

        if not readme_id:
            raise RuntimeError(
                f"Die Readme-/Startseite des Collectives "
                f"{collective_id!r} hat keine gültige Seiten-ID."
            )

        result = await ensure_page(
            tools,
            collective_id=collective_id,
            title=title,
            parent_id=readme_id,
            config=config,
        )

        await _log_page_event(
            config,
            operation,
            "completed",
            collective_id=str(collective_id),
            title=title,
            parent_id=readme_id,
            page_id=page_id(result),
        )

        return result

    except Exception as exc:
        await _log_page_event(
            config,
            operation,
            "failed",
            collective_id=str(collective_id),
            title=title,
            error=str(exc),
            error_type=type(exc).__name__,
        )
        raise


async def ensure_single_page(
    tools: dict[str, MonitoredTool],
    collective_id: str | int,
    title: str,
    parent_id: str | int,
    config: CollectiveConfig | None = None,
) -> dict:
    """Stellt sicher, dass eine einzelne Seite im Collective existiert."""
    operation = "ensure_single_page"

    await _log_page_event(
        config,
        operation,
        "started",
        collective_id=str(collective_id),
        title=title,
        parent_id=str(parent_id),
    )

    try:
        result = await ensure_page(
            tools,
            collective_id=collective_id,
            title=title,
            parent_id=parent_id,
            config=config,
        )

        await _log_page_event(
            config,
            operation,
            "completed",
            collective_id=str(collective_id),
            title=title,
            parent_id=str(parent_id),
            page_id=page_id(result),
        )

        return result

    except Exception as exc:
        await _log_page_event(
            config,
            operation,
            "failed",
            collective_id=str(collective_id),
            title=title,
            parent_id=str(parent_id),
            error=str(exc),
            error_type=type(exc).__name__,
        )
        raise


def normalize_id(value: Any) -> str | None:
    """Normalisiert eine ID oder extrahiert sie aus einem Objekt."""
    if value is None:
        return None

    if isinstance(value, dict):
        value = (
            value.get("id")
            or value.get("page_id")
            or value.get("pageId")
            or value.get("collective_id")
            or value.get("collectiveId")
        )

    if value is None:
        return None

    text = str(value).strip()
    return text or None


def get_value(
    value: Any,
    *keys: str,
    default: Any = None,
) -> Any:
    """Liest einen Wert aus einem Dictionary oder Objektattribut."""
    if isinstance(value, dict):
        for key in keys:
            if key in value and value[key] is not None:
                return value[key]

    for key in keys:
        result = getattr(value, key, None)
        if result is not None:
            return result

    return default


def page_id(page: Any) -> str | None:
    return normalize_id(
        get_value(page, "id", "page_id", "pageId", "collective_id")
    )


def page_title(page: Any) -> str:
    value = get_value(page, "title", "name", default="")
    return str(value) if value is not None else ""


def page_parent_id(page: Any) -> str | None:
    parent = get_value(
        page,
        "parent_id",
        "parentId",
        "parent",
        default=None,
    )
    return normalize_id(parent)


def find_page_by_title(
    pages: list[dict],
    title: str,
) -> dict | None:
    """Findet eine Seite anhand ihres Titels, ohne Groß-/Kleinschreibung."""
    expected = title.strip().casefold()

    for page in pages:
        if page_title(page).strip().casefold() == expected:
            return page

    return None


def find_page_by_id(
    pages: list[dict],
    target_id: str | int,
) -> dict | None:
    """Findet eine Seite anhand ihrer ID."""
    expected = normalize_id(target_id)

    for page in pages:
        if page_id(page) == expected:
            return page

    return None


def parse_collective_id(value: Any) -> str | None:
    """Normalisiert eine Collective-ID aus einem String oder Objekt."""
    if isinstance(value, dict):
        return normalize_id(value)

    if value is None:
        return None

    text = str(value).strip()
    return text or None


def sanitize_page_name(
    name: str,
    default: str = "New File",
    db4_byte_support: bool = True,
) -> str:
    """Python-Äquivalent zu Nextcloud Collectives sanitiseFilename()."""

    # '/' durch '-' ersetzen, um Pfadtrenner zu verhindern.
    name = name.replace("/", "-")

    # Unter Windows unzulässige Zeichen entfernen.
    name = name.translate(str.maketrans("", "", '*|\\:"<>?'))

    # Falls die Datenbank kein 4-Byte-UTF-8 unterstützt,
    # Unicode-Zeichen außerhalb der Basic Multilingual Plane entfernen.
    if not db4_byte_support:
        name = re.sub(
            r"[\U00010000-\U0010FFFF]",
            "",
            name,
        )

    # Führende und nachgestellte Leerzeichen und Punkte entfernen.
    name = name.strip(" .")

    # Fallback wie in der PHP-Funktion.
    if name == "":
        name = default

    return name
