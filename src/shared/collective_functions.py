from typing import Any
import logging

from src.shared.collectives.collective_tools import (
    CollectiveConfig,
    load_collective_tools,
    log_collective_tool_event,
    utc_timestamp,
)
from src.shared.collectives.collective_pages import (
    get_collective_pages,
    create_collective_page,
    refresh_created_page,
    find_page_by_title,
    page_id,
    page_title as get_page_title,
)
from src.shared.collectives.collective_storage import (
    get_collective_page_path,
    write_and_verify_markdown,
)
from src.shared.collectives.entry_validation import validate_entries

logger = logging.getLogger(__name__)


async def _log_function_event(
    config: CollectiveConfig | None,
    operation: str,
    phase: str,
    **details: Any,
) -> None:
    """Writes a high-level event with run_id and graph_id."""
    if config is None:
        return

    await log_collective_tool_event(
        config,
        {
            "event_type": "collective_function",
            "timestamp": utc_timestamp(),
            "operation": operation,
            "phase": phase,
            **details,
        },
    )


def error_result(exc: Exception) -> dict:
    """Creates a uniform error response."""
    return {
        "success": False,
        "error": str(exc),
        "error_type": type(exc).__name__,
    }


def _get_readme_page(pages: list[dict]) -> dict | None:
    """Finds the Readme/home page of a Collective."""
    for page in pages:
        file_name = page.get("fileName") or page.get("file_name")
        parent_id = page.get("parentId", page.get("parent_id"))

        if (
            str(file_name or "").casefold() == "readme.md"
            or parent_id == 0
            or str(parent_id) == "0"
        ):
            if page_id(page):
                return page

    return None


async def import_collective_entries(
    client: Any,
    collective_id: str,
    entries: list[dict],
    config: CollectiveConfig | None = None,
) -> dict:
    """
    Imports structured entries as individual subpages.

    The overview page is created if necessary.
    Existing entry pages are updated.
    Missing entry pages are created.

    All high-level events are logged via CollectiveConfig with run_id
    and graph_id.
    """
    config = config or CollectiveConfig()
    operation = "import_collective_entries"

    imported_pages: list[dict] = []
    errors: list[dict] = []
    overview_id: str | None = None

    await _log_function_event(
        config,
        operation,
        "started",
        collective_id=str(collective_id),
        entry_count=len(entries) if isinstance(entries, list) else None,
        overview_title=config.overview_title,
    )

    try:
        if not isinstance(collective_id, (str, int)) or not str(
            collective_id
        ).strip():
            raise ValueError("collective_id must not be empty.")

        if not isinstance(entries, list):
            raise TypeError("entries must be a list.")

        tools = await load_collective_tools(client, config)

        if not config.overview_title or not config.overview_title.strip():
            raise ValueError(
                "CollectiveConfig.overview_title must not be empty."
            )

        if config.get_entry_name is None:
            raise ValueError(
                "CollectiveConfig.get_entry_name is not configured."
            )

        if config.render_entry is None:
            raise ValueError(
                "CollectiveConfig.render_entry is not configured."
            )

        await _log_function_event(
            config,
            operation,
            "validation_started",
            collective_id=str(collective_id),
            entry_count=len(entries),
        )

        validated_entries, validation_errors = validate_entries(
            entries,
            config,
        )

        errors.extend(
            {
                "error": message,
                "error_type": "ValidationError",
            }
            for message in validation_errors
        )

        await _log_function_event(
            config,
            operation,
            "validation_completed",
            collective_id=str(collective_id),
            input_count=len(entries),
            validated_count=len(validated_entries),
            validation_error_count=len(validation_errors),
        )

        # Fetch all pages and search for the overview page.
        pages = await get_collective_pages(
            tools,
            collective_id=collective_id,
            config=config,
        )

        overview_page = find_page_by_title(
            pages,
            config.overview_title,
        )

        if overview_page is None:
            readme_page = _get_readme_page(pages)

            if readme_page is None:
                raise RuntimeError(
                    f"The Readme/home page of the Collective "
                    f"{collective_id!r} could not be found."
                )

            readme_id = page_id(readme_page)

            if not readme_id:
                raise RuntimeError(
                    "The Readme/home page was found, "
                    "but its ID is missing."
                )

            await _log_function_event(
                config,
                operation,
                "overview_creation_started",
                collective_id=str(collective_id),
                overview_title=config.overview_title,
                parent_id=readme_id,
            )

            created_overview = await create_collective_page(
                tools,
                collective_id=collective_id,
                parent_id=readme_id,
                title=config.overview_title,
                config=config,
            )

            overview_id = page_id(created_overview)

            if not overview_id:
                raise RuntimeError(
                    f"The overview page {config.overview_title!r} "
                    "was created, but its ID is missing."
                )

            await _log_function_event(
                config,
                operation,
                "overview_creation_completed",
                collective_id=str(collective_id),
                overview_title=config.overview_title,
                overview_page_id=overview_id,
            )

        else:
            overview_id = page_id(overview_page)

            if not overview_id:
                raise RuntimeError(
                    f"For the overview page {config.overview_title!r} "
                    "the ID is missing."
                )

            await _log_function_event(
                config,
                operation,
                "overview_found",
                collective_id=str(collective_id),
                overview_title=config.overview_title,
                overview_page_id=overview_id,
            )

        # Reload the page so that we get current API metadata.
        overview_page = await refresh_created_page(
            tools,
            page_id_value=overview_id,
            collective_id=collective_id,
            retries=config.refresh_retries,
            delay_seconds=config.refresh_delay_seconds,
            config=config,
        )

        if overview_page is None:
            raise RuntimeError(
                f"Die Übersichtsseite {config.overview_title!r} "
                "konnte nicht geladen werden."
            )

        overview_id = page_id(overview_page)

        if not overview_id:
            raise RuntimeError(
                "Die ID der geladenen Übersichtsseite fehlt."
            )

        # The MCP function returns all pages of the Collective.
        # The page cache is updated after each successful import.
        child_pages = await get_collective_pages(
            tools,
            collective_id=collective_id,
            config=config,
        )

        for index, entry in enumerate(validated_entries):
            entry_number = config.first_entry_number + index
            title: str | None = None

            await _log_function_event(
                config,
                operation,
                "entry_started",
                collective_id=str(collective_id),
                overview_page_id=overview_id,
                entry_index=index,
                entry_number=entry_number,
            )

            try:
                entry_name = config.get_entry_name(entry)

                if entry_name is None or not str(entry_name).strip():
                    raise ValueError(
                        f"Entry {index + 1} has no valid name."
                    )

                prefix = str(config.entry_prefix or "").strip("-_ ")
                name = str(entry_name).strip()

                title = (
                    f"{entry_number:03d}-"
                    f"{prefix + '-' if prefix else ''}"
                    f"{name}"
                )

                content = config.render_entry(entry)

                if not isinstance(content, str):
                    raise TypeError(
                        f"The renderer for {title!r} "
                        "must return a string."
                    )

                    # Search for existing page by title.
                existing_page = find_page_by_title(
                    child_pages,
                    title,
                )

                if existing_page is not None:
                    target_id = page_id(existing_page)
                    action = "updated"

                    if not target_id:
                        raise RuntimeError(
                            f"Für die vorhandene Seite {title!r} "
                            "fehlt die ID."
                        )

                    await _log_function_event(
                        config,
                        operation,
                        "entry_page_found",
                        collective_id=str(collective_id),
                        entry_number=entry_number,
                        title=title,
                        page_id=target_id,
                        action=action,
                    )

                else:
                    # The new page is created under the overview page.
                    created_page = await create_collective_page(
                        tools,
                        collective_id=collective_id,
                        parent_id=overview_id,
                        title=title,
                        config=config,
                    )

                    target_id = page_id(created_page)
                    action = "created"

                    if not target_id:
                        raise RuntimeError(
                            f"The page {title!r} was created, "
                            "but its ID is missing."
                        )

                    await _log_function_event(
                        config,
                        operation,
                        "entry_page_created",
                        collective_id=str(collective_id),
                        overview_page_id=overview_id,
                        entry_number=entry_number,
                        title=title,
                        page_id=target_id,
                        action=action,
                    )

                # Get current page data for the file path.
                page = await refresh_created_page(
                    tools,
                    page_id_value=target_id,
                    collective_id=collective_id,
                    retries=config.refresh_retries,
                    delay_seconds=config.refresh_delay_seconds,
                    config=config,
                )

                if page is None:
                    raise RuntimeError(
                        f"Die Seite {title!r} konnte nicht geladen werden."
                    )

                path = get_collective_page_path(page)

                if path is None:
                    raise RuntimeError(
                        f"Für die Seite {title!r} "
                        "konnte kein Dateipfad ermittelt werden."
                    )

                await _log_function_event(
                    config,
                    operation,
                    "entry_write_started",
                    collective_id=str(collective_id),
                    entry_number=entry_number,
                    title=title,
                    page_id=target_id,
                    path=str(path),
                    content_length=len(content),
                    action=action,
                )

                await write_and_verify_markdown(
                    tools,
                    str(path),
                    content,
                    config=config,
                )

                imported_page = {
                    "page_id": page_id(page),
                    "title": get_page_title(page) or title,
                    "path": str(path),
                    "action": action,
                    "entry_number": entry_number,
                }
                imported_pages.append(imported_page)

                await _log_function_event(
                    config,
                    operation,
                    "entry_completed",
                    collective_id=str(collective_id),
                    overview_page_id=overview_id,
                    entry_number=entry_number,
                    title=imported_page["title"],
                    page_id=imported_page["page_id"],
                    path=str(path),
                    action=action,
                )

                # Cache update, so that subsequently processed entries
                # can find already imported pages.
                page_identifier = page_id(page)

                existing_index = next(
                    (
                        i
                        for i, child in enumerate(child_pages)
                        if page_id(child) == page_identifier
                    ),
                    None,
                )

                if existing_index is None:
                    child_pages.append(page)
                else:
                    child_pages[existing_index] = page

            except Exception as exc:
                error = {
                    "index": index,
                    "entry_number": entry_number,
                    "title": title,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                }
                errors.append(error)

                logger.exception(
                    "Import of a Collective entry failed: "
                    "collective_id=%s, entry_number=%s, title=%r",
                    collective_id,
                    entry_number,
                    title,
                )

                await _log_function_event(
                    config,
                    operation,
                    "entry_failed",
                    collective_id=str(collective_id),
                    overview_page_id=overview_id,
                    entry_index=index,
                    entry_number=entry_number,
                    title=title,
                    error=str(exc),
                    error_type=type(exc).__name__,
                )

        created_count = sum(
            item["action"] == "created"
            for item in imported_pages
        )
        updated_count = sum(
            item["action"] == "updated"
            for item in imported_pages
        )

        result = {
            "success": not errors,
            "overview_page_id": overview_id,
            "overview_title": config.overview_title,
            "entry_count": len(entries),
            "validated_count": len(validated_entries),
            "imported_count": len(imported_pages),
            "created_count": created_count,
            "updated_count": updated_count,
            "failed_count": len(errors),
            "pages": imported_pages,
            "errors": errors,
        }

        await _log_function_event(
            config,
            operation,
            "completed" if result["success"] else "completed_with_errors",
            collective_id=str(collective_id),
            overview_page_id=overview_id,
            entry_count=len(entries),
            validated_count=len(validated_entries),
            imported_count=len(imported_pages),
            created_count=created_count,
            updated_count=updated_count,
            failed_count=len(errors),
            success=result["success"],
        )

        return result

    except Exception as exc:
        logger.exception(
            "Import of Collective entries failed: collective_id=%s",
            collective_id,
        )

        await _log_function_event(
            config,
            operation,
            "failed",
            collective_id=str(collective_id),
            overview_page_id=overview_id,
            error=str(exc),
            error_type=type(exc).__name__,
        )

        return error_result(exc)


async def import_single_page(
    client: Any,
    collective_id: str,
    title: str | None = None,
    content: str = "",
    config: CollectiveConfig | None = None,
    parent_id: str | None = None,
    page_title: str | None = None,
    collective: Any = None,
) -> dict:
    """
    Creates or updates a single Collective page.

    Searches by title in the entire Collective.
    If the page exists, its Markdown content is updated.
    Otherwise, a new page is created under the specified parent.

    If parent_id is missing or 0, the Readme/home page is used as
    the parent, as parent_id=0 is not accepted during creation.
    """
    config = config or CollectiveConfig()
    resolved_title = page_title or title
    operation = "import_single_page"
    target_id: str | None = None
    path: str | None = None

    await _log_function_event(
        config,
        operation,
        "started",
        collective_id=str(collective_id),
        title=resolved_title,
        requested_parent_id=parent_id,
        content_length=len(content) if isinstance(content, str) else None,
    )

    try:
        if not isinstance(collective_id, (str, int)) or not str(
            collective_id
        ).strip():
            raise ValueError("collective_id must not be empty.")

        if not resolved_title or not resolved_title.strip():
            raise ValueError("The page title must not be empty.")

        if not isinstance(content, str):
            raise TypeError("The page content must be a string.")

        resolved_title = resolved_title.strip()

        tools = await load_collective_tools(client, config)

        pages = await get_collective_pages(
            tools,
            collective_id=collective_id,
            config=config,
        )

        logger.info(
            "import_single_page: %d Seiten im Collective gefunden.",
            len(pages),
        )

        await _log_function_event(
            config,
            operation,
            "pages_loaded",
            collective_id=str(collective_id),
            page_count=len(pages),
            title=resolved_title,
        )

        page = find_page_by_title(pages, resolved_title)

        if page is not None:
            target_id = page_id(page)

            if not target_id:
                raise RuntimeError(
                    f"Für die vorhandene Seite {resolved_title!r} "
                    "fehlt die ID."
                )

            action = "updated"

            await _log_function_event(
                config,
                operation,
                "existing_page_found",
                collective_id=str(collective_id),
                title=resolved_title,
                page_id=target_id,
                action=action,
            )

        else:
            # parent_id fehlt oder ist 0: Readme-ID verwenden.
            if parent_id is None or str(parent_id).strip() in {"", "0"}:
                readme_page = _get_readme_page(pages)

                if readme_page is None:
                    raise RuntimeError(
                        f"Die Readme-/Startseite des Collectives "
                        f"{collective_id!r} konnte nicht gefunden werden."
                    )

                effective_parent_id = page_id(readme_page)

                if not effective_parent_id:
                    raise RuntimeError(
                        "Die Readme-/Startseite wurde gefunden, "
                        "aber ihre ID fehlt."
                    )
            else:
                effective_parent_id = str(parent_id).strip()

            await _log_function_event(
                config,
                operation,
                "page_creation_started",
                collective_id=str(collective_id),
                title=resolved_title,
                parent_id=effective_parent_id,
            )

            created_page = await create_collective_page(
                tools,
                collective_id=collective_id,
                parent_id=effective_parent_id,
                title=resolved_title,
                config=config,
            )

            target_id = page_id(created_page)
            action = "created"

            if not target_id:
                raise RuntimeError(
                    f"Die Seite {resolved_title!r} wurde erstellt, "
                    f"aber ihre ID fehlt. Antwort: {created_page!r}"
                )

            await _log_function_event(
                config,
                operation,
                "page_creation_completed",
                collective_id=str(collective_id),
                title=resolved_title,
                parent_id=effective_parent_id,
                page_id=target_id,
            )

        # Seite laden, damit Dateipfad und Metadaten aktuell sind.
        page = await refresh_created_page(
            tools,
            page_id_value=target_id,
            collective_id=collective_id,
            retries=config.refresh_retries,
            delay_seconds=config.refresh_delay_seconds,
            config=config,
        )

        if page is None:
            raise RuntimeError(
                f"The page {resolved_title!r} (ID {target_id}) "
                "could not be loaded after creation/finding."
            )

        path_object = get_collective_page_path(page)

        if path_object is None:
            raise RuntimeError(
                f"No file path could be determined for the page {resolved_title!r}."
            )

        path = str(path_object)

        await _log_function_event(
            config,
            operation,
            "write_started",
            collective_id=str(collective_id),
            title=resolved_title,
            page_id=target_id,
            path=path,
            content_length=len(content),
            action=action,
        )

        await write_and_verify_markdown(
            tools,
            path,
            content,
            config=config,
        )

        result = {
            "success": True,
            "page_id": page_id(page),
            "title": get_page_title(page) or resolved_title,
            "path": path,
            "action": action,
        }

        logger.info(
            "import_single_page erfolgreich abgeschlossen: %r",
            result,
        )

        await _log_function_event(
            config,
            operation,
            "completed",
            collective_id=str(collective_id),
            title=result["title"],
            page_id=result["page_id"],
            path=path,
            action=action,
            success=True,
        )

        return result

    except Exception as exc:
        logger.exception(
            "import_single_page failed: collective_id=%s, title=%r",
            collective_id,
            resolved_title,
        )

        await _log_function_event(
            config,
            operation,
            "failed",
            collective_id=str(collective_id),
            title=resolved_title,
            page_id=target_id,
            path=path,
            error=str(exc),
            error_type=type(exc).__name__,
        )

        return error_result(exc)
