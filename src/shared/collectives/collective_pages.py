
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
    """Writes a high-level event with run_id and graph_id to monitoring."""
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
    """Fetches all pages of a Collective and logs the process."""
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
    """Creates a Collective page and logs the result."""
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
    """Reloads a page if it is not yet available."""
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

            # The MCP response may contain the page data directly or in "page".
            # Both common forms are supported.
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
                reason="The response contained no recognizable page data.",
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
        error="The page was not available after all attempts.",
    )

    return None


async def ensure_page(
    tools: dict[str, MonitoredTool],
    collective_id: str | int,
    title: str,
    parent_id: str | int,
    config: CollectiveConfig | None = None,
) -> dict:
    """Finds a page or creates it and reloads it."""
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

        # If the creation response itself contains the page data,
        # return it. Otherwise, report the failed refresh.
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
            f"The Collective page {title!r} could not be created "
            "or reloaded."
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
    """Ensures a page exists below the Readme page.

    parent_id=0 is deliberately not used here because the API does not
    accept this value as a valid parent when creating a page.
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
            f"The Readme/home page of the Collective "
            f"{collective_id!r} could not be found."
        )

        readme_id = page_id(readme_page)

        if not readme_id:
            raise RuntimeError(
                f"The Readme/home page of the Collective "
                f"{collective_id!r} does not have a valid page ID."
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
    """Ensures that a single page exists in the Collective."""
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
    """Normalizes an ID or extracts it from an object."""
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
    """Reads a value from a dictionary or object attribute."""
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
    """Finds a page by its title, case-insensitive."""
    expected = title.strip().casefold()

    for page in pages:
        if page_title(page).strip().casefold() == expected:
            return page

    return None


def find_page_by_id(
    pages: list[dict],
    target_id: str | int,
) -> dict | None:
    """Finds a page by its ID."""
    expected = normalize_id(target_id)

    for page in pages:
        if page_id(page) == expected:
            return page

    return None


def parse_collective_id(value: Any) -> str | None:
    """Normalizes a Collective ID from a string or object."""
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
    """Python equivalent to Nextcloud Collectives sanitizeFilename()."""

    # Replace '/' with '-' to prevent path separators.
    name = name.replace("/", "-")

    # Remove characters invalid on Windows.
    name = name.translate(str.maketrans("", "", '*|\\:"<>?'))

    # If the database does not support 4-byte UTF-8,
    # remove Unicode characters outside the Basic Multilingual Plane.
    if not db4_byte_support:
        name = re.sub(
            r"[\U00010000-\U0010FFFF]",
            "",
            name,
        )

    # Remove leading and trailing spaces and dots.
    name = name.strip(" .")

    # Fallback wie in der PHP-Funktion.
    if name == "":
        name = default

    return name
