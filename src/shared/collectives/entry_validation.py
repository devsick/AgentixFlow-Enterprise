
from typing import Any


def validate_entries(
    entries: list[Any],
    config: Any,
) -> tuple[list[dict[str, Any]], list[str]]:
    """
    Validiert und normalisiert Einträge anhand der Konfiguration.

    Rückgabe:
        - valid_entries: normalisierte Einträge
        - errors: aufgetretene Validierungsfehler
    """
    valid_entries: list[dict[str, Any]] = []
    errors: list[str] = []

    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(
                f"Eintrag {index + 1}: Erwartet wurde ein Dictionary."
            )
            continue

        normalized = dict(entry)

        for field_name in config.scalar_fields:
            if field_name in normalized and normalized[field_name] is not None:
                normalized[field_name] = str(normalized[field_name])

        for field_name in config.list_fields:
            if field_name not in normalized or normalized[field_name] is None:
                normalized[field_name] = []
            elif not isinstance(normalized[field_name], list):
                errors.append(
                    f"Eintrag {index + 1}: "
                    f"Feld '{field_name}' muss eine Liste sein."
                )
            else:
                normalized[field_name] = [
                    str(item) for item in normalized[field_name]
                ]

        if config.validate_callback:
            result = config.validate_callback(normalized, config)

            if result:
                if isinstance(result, list):
                    errors.extend(
                        f"Eintrag {index + 1}: {error}"
                        for error in result
                    )
                else:
                    errors.append(
                        f"Eintrag {index + 1}: {result}"
                    )

        valid_entries.append(normalized)

    return valid_entries, errors
