
from typing import Any


def render_markdown_list(entries: list[dict[str, Any]], config: Any) -> str:
    """
    Rendert Einträge als Markdown.

    Verwendet die in der Konfiguration hinterlegten Render-Callbacks,
    sofern vorhanden. Andernfalls wird eine generische Markdown-
    Darstellung erzeugt.
    """
    if config.render_callback:
        return config.render_callback(entries, config)

    lines: list[str] = []

    for entry in entries:
        name = config.get_entry_name(entry) if config.get_entry_name else None

        if name:
            lines.append(f"## {name}")
        else:
            lines.append("## Eintrag")

        if config.render_entry:
            lines.append(config.render_entry(entry, config))
        else:
            for key, value in entry.items():
                if isinstance(value, list):
                    lines.append(f"- **{key}:** {', '.join(str(item) for item in value)}")
                else:
                    lines.append(f"- **{key}:** {value}")

        lines.append("")

    return "\n".join(lines).strip()
