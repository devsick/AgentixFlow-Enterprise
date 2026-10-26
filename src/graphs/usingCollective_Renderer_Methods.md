# `collective_functions.py` – Architektur und Verwendung von Callbacks

## 1. Zweck dieser Datei

`collective_functions.py` enthält die gemeinsame Logik für den Import von Einträgen in ein Collective.

Die Datei soll unabhängig davon funktionieren, welche Art von Daten importiert wird. Sie kennt beispielsweise weder die fachliche Struktur eines Projekts noch die einer Beschäftigung.

Die jeweilige Node legt fest:

- welche Daten importiert werden,
- welche Felder für die Validierung relevant sind,
- wie der Name eines Eintrags gebildet wird,
- wie eine einzelne Eintragsseite als Markdown dargestellt wird,
- welche Konfiguration für den Import verwendet wird.

`collective_functions.py` übernimmt anschließend die gemeinsame Verarbeitung:

- Konfiguration prüfen,
- Einträge validieren,
- Overview-Seite suchen oder erstellen,
- Eintragsnamen über den konfigurierten Callback ermitteln,
- Seitentitel zusammensetzen,
- vorhandene Seiten suchen oder neue Seiten erstellen,
- Markdown-Inhalte schreiben und überprüfen,
- Ergebnisse und Fehler zurückgeben.

**Grundprinzip:** Die Node beschreibt die fachlichen Besonderheiten. `collective_functions.py` steuert den allgemeinen Importablauf.

---

## 2. Das Prinzip der Callback-Funktionen

Ein Callback ist eine Funktion, die nicht unmittelbar ausgeführt, sondern zunächst an eine andere Funktion übergeben wird. Diese andere Funktion ruft sie später bei Bedarf auf.

In diesem Projekt werden die Callback-Funktionen über `CollectiveConfig` übergeben.

Das ist wichtig, weil `import_collective_entries()` nicht wissen muss, welche konkrete Node den Import ausgelöst hat.

### Beispiel: Projects-Node

In `extract_project_agent_node.py` wird die Konfiguration beispielsweise so erstellt:

```python
config = CollectiveConfig(
    mode="overview_with_entries",
    overview_title=self.OVERVIEW_TITLE,
    entry_prefix=self.PROJECT_PREFIX,
    first_entry_number=self.FIRST_PROJECT_NUMBER,
    scalar_fields=self.PROJECT_SCALAR_FIELDS,
    list_fields=self.PROJECT_LIST_FIELDS,
    get_entry_name=self._project_name,
    render_entry=self._render_project_markdown,
    render_overview=self._render_overview_markdown,
    graph_id=state.get("graph_id"),
    run_id=state.get("run_id"),
)
```

Die entscheidenden Zeilen sind:

```python
get_entry_name=self._project_name,
render_entry=self._render_project_markdown,
```

Hier werden die Methoden als Funktionsreferenzen übergeben.

Es steht dort bewusst **kein Klammerpaar hinter dem Methodennamen**. Die Funktionen sollen an dieser Stelle noch nicht ausgeführt werden.

### Beispiel: Employments-Node

Die Employments-Node verwendet dieselbe gemeinsame Importfunktion, übergibt aber andere Callbacks:

```python
config = CollectiveConfig(
    mode="overview_with_entries",
    overview_title=self.OVERVIEW_TITLE,
    entry_prefix=self.EMPLOYMENT_PREFIX,
    first_entry_number=self.FIRST_EMPLOYMENT_NUMBER,
    scalar_fields=self.EMPLOYMENT_SCALAR_FIELDS,
    list_fields=self.EMPLOYMENT_LIST_FIELDS,
    get_entry_name=self._employment_name,
    render_entry=self._render_employment_markdown,
    render_overview=self._render_overview_markdown,
    graph_id=state.get("graph_id"),
    run_id=state.get("run_id"),
)
```

Damit erhält `collective_functions.py` für Beschäftigungen andere Funktionen als für Projekte, ohne dass dort eine Unterscheidung zwischen diesen Datentypen notwendig ist.

---

## 3. Ablauf beim Aufruf von `import_collective_entries()`

Die Node ruft die gemeinsame Importfunktion auf:

```python
imported = await import_collective_entries(
    client=mcp_client,
    collective_id=collective_id,
    entries=projects,
    config=config,
)
```

Bei Beschäftigungen wird entsprechend `entries=raw_employments` übergeben.

Der Ablauf innerhalb der gemeinsamen Importfunktion ist vereinfacht:

```python
validated_entries = validate_entries(entries, config)

for index, entry in enumerate(validated_entries):
    entry_number = config.first_entry_number + index

    entry_name = config.get_entry_name(entry)

    prefix = str(config.entry_prefix or "").strip("-_ ")
    name = str(entry_name).strip()

    title = (
        f"{entry_number:03d}-"
        f"{prefix + '-' if prefix else ''}"
        f"{name}"
    )

    content = config.render_entry(entry, config)

    # Anschließend:
    # - vorhandene Seite suchen oder neue Seite erstellen
    # - Seite aktualisieren
    # - Markdown schreiben und überprüfen
```

Dieses Beispiel verdeutlicht das Callback-Prinzip. Die eigentliche Funktion enthält zusätzlich Fehlerbehandlung, Logging und weitere Verarbeitungsschritte.

### Was passiert beim Namens-Callback?

Bei dieser Zeile:

```python
entry_name = config.get_entry_name(entry)
```

wird der Callback tatsächlich ausgeführt.

- Bei Projects wird `_project_name(entry)` aufgerufen.
- Bei Employments wird `_employment_name(entry)` aufgerufen.

Welche Funktion aufgerufen wird, steht bereits in der Konfiguration der jeweiligen Node.

Die gemeinsame Importfunktion muss deshalb weder den Klassennamen der Node prüfen noch Bedingungen wie `if project` oder `if employment` enthalten.

### Was passiert beim Markdown-Callback?

Bei dieser Zeile:

```python
content = config.render_entry(entry, config)
```

wird der konfigurierte Markdown-Renderer ausgeführt.

- Bei Projects soll `_render_project_markdown()` die Projektseite erzeugen.
- Bei Employments soll `_render_employment_markdown()` die Beschäftigungsseite erzeugen.

**Wichtig:** Der aktuelle Aufruf übergibt zwei Argumente: `entry` und `config`. Die konfigurierte Renderer-Methode muss daher zu dieser Signatur passen.

---

## 4. Verbindliche Schnittstellen der Callbacks

Damit neue Nodes zuverlässig mit `collective_functions.py` zusammenarbeiten, müssen die übergebenen Funktionen die erwarteten Argumente akzeptieren.

### 4.1 `get_entry_name`

Erwarteter Aufruf:

```python
entry_name = config.get_entry_name(entry)
```

Erwartete Signatur:

```python
def get_entry_name(entry: dict) -> str:
    ...
```

Die Funktion erhält genau einen Eintrag und gibt dessen fachlichen Namen zurück.

Beispiel für Projekte:

```python
@staticmethod
def _project_name(entry: dict) -> str:
    name = entry.get("project_name", "").strip()

    if not name:
        raise ValueError("Project is missing 'project_name'.")

    return sanitize_page_name(name)
```

Beispiel für Beschäftigungen:

```python
@staticmethod
def _employment_name(entry: dict) -> str:
    company = entry.get("company_organization", "").strip()
    position = entry.get("position", "").strip()

    parts = [part for part in (company, position) if part]
    name = " - ".join(parts)

    start = entry.get("employment_start", "").strip() or "?"
    end = entry.get("employment_end", "").strip() or "present"

    return sanitize_page_name(f"{name} ({start}-{end})")
```

Die Beispiele verdeutlichen, dass die fachliche Namensbildung in der Node bleibt. Die gemeinsame Importfunktion muss diese Details nicht kennen.

### 4.2 `render_entry`

Erwarteter Aufruf:

```python
content = config.render_entry(entry, config)
```

Erwartete Signatur für eine normale Funktion:

```python
def render_entry(entry: dict, config: CollectiveConfig) -> str:
    ...
```

Bei einer Instanzmethode muss zusätzlich der implizite Parameter `self` berücksichtigt werden:

```python
def _render_entry(
    self,
    entry: dict,
    config: CollectiveConfig,
) -> str:
    ...
```

Bei einer `@staticmethod` sind nur die beiden expliziten Parameter erforderlich.

**Achtung bei `@classmethod`:** Eine Klassenmethode erhält zusätzlich den impliziten Parameter `cls`. Eine Methode mit der Signatur `def _render_project_markdown(cls, entry)` akzeptiert deshalb nicht automatisch den aktuellen Aufruf mit `entry` und `config`. Die Signaturen müssen zusammenpassen.

### 4.3 `render_overview`

Die Konfiguration kann auch einen Callback für die Overview-Darstellung enthalten:

```python
render_overview=self._render_overview_markdown,
```

Die gewünschte Schnittstelle hängt davon ab, wie der Callback verwendet wird. Die bisher gezeigte Methode erwartet:

```python
def _render_overview_markdown(entries: list[dict]) -> str:
    ...
```

**Aktueller Implementierungsstand:** In der bisher gezeigten Version von `import_collective_entries()` wird `config.render_overview` nicht aufgerufen. Die Angabe in der Konfiguration allein führt noch nicht dazu, dass der Overview-Inhalt gerendert oder geschrieben wird.

Dieser Callback sollte deshalb nicht mit der tatsächlich ausgeführten Eintragsseiten-Renderfunktion verwechselt werden.

---

## 5. Bedeutung der übrigen Konfigurationsfelder

Die folgenden Felder beschreiben den Import und werden nicht mit Callback-Funktionen verwechselt.

| Konfigurationsfeld | Bedeutung |
|---|---|
| `mode` | Legt den vorgesehenen Importmodus fest. |
| `overview_title` | Titel der übergeordneten Overview-Seite. |
| `entry_prefix` | Präfix für die Seitentitel der Einträge. |
| `first_entry_number` | Erste laufende Nummer der Einträge. |
| `scalar_fields` | Namen der Felder mit einzelnen Werten. |
| `list_fields` | Namen der Felder mit Listenwerten. |
| `get_entry_name` | Callback zur Ermittlung des Eintragsnamens. |
| `render_entry` | Callback zur Erstellung des Markdown-Inhalts einer Eintragsseite. |
| `render_overview` | Vorgesehener Callback zur Erstellung des Overview-Markdowns. |
| `graph_id` | Kontext für Graph-/Node-Monitoring. |
| `run_id` | Kontext für die Zuordnung zu einem Lauf. |

`scalar_fields` und `list_fields` beschreiben die erwartete Datenstruktur. Sie bestimmen nicht automatisch die Überschriften oder die Reihenfolge der Abschnitte im Markdown. Diese Gestaltung erfolgt im jeweiligen Renderer.

---

## 6. Regeln für neue Nodes

Wenn eine neue Node dieselbe Importfunktion verwenden soll, gelten folgende Regeln.

1. **Eigene Datenfelder definieren.**  
   Die Node legt ihre `scalar_fields` und `list_fields` entsprechend dem Datenschema fest.

2. **Eigenen Namens-Callback bereitstellen.**  
   Die Methode muss einen einzelnen Eintrag entgegennehmen und einen passenden Namen zurückgeben.

3. **Eigenen Markdown-Renderer bereitstellen.**  
   Die Methode erstellt den vollständigen Markdown-Inhalt einer einzelnen Eintragsseite und muss die von `collective_functions.py` verwendete Signatur akzeptieren.

4. **Callbacks in `CollectiveConfig` hinterlegen.**  
   Die Funktionsreferenzen werden ohne aufrufende Klammern übergeben.

5. **Gemeinsame Importfunktion aufrufen.**  
   Die Node übergibt Client, Collective-ID, Einträge und Konfiguration an `import_collective_entries()`.

6. **Keine fachlichen Sonderfälle in `collective_functions.py` ergänzen.**  
   Änderungen an der fachlichen Namensbildung oder am individuellen Markdown-Layout gehören grundsätzlich in die jeweilige Node. Die gemeinsame Importfunktion bleibt für den Importablauf verantwortlich.

Beispiel für das Muster:

```python
config = CollectiveConfig(
    mode="overview_with_entries",
    overview_title=self.OVERVIEW_TITLE,
    entry_prefix=self.ENTRY_PREFIX,
    first_entry_number=self.FIRST_ENTRY_NUMBER,
    scalar_fields=self.SCALAR_FIELDS,
    list_fields=self.LIST_FIELDS,
    get_entry_name=self._entry_name,
    render_entry=self._render_entry_markdown,
    render_overview=self._render_overview_markdown,
    graph_id=state.get("graph_id"),
    run_id=state.get("run_id"),
)

result = await import_collective_entries(
    client=mcp_client,
    collective_id=collective_id,
    entries=entries,
    config=config,
)
```

Die Namen der Konstanten und Methoden sind hier Platzhalter und müssen zur jeweiligen Node passen.

---

## 7. Häufige Fehlerquellen

### Callback wird versehentlich ausgeführt

Falsch:

```python
get_entry_name=self._project_name(entry)
```

Hier würde die Methode bereits beim Erstellen der Konfiguration aufgerufen. Außerdem ist `entry` an dieser Stelle möglicherweise noch gar nicht verfügbar.

Richtig:

```python
get_entry_name=self._project_name
```

Die Methode wird erst später von `collective_functions.py` aufgerufen.

### Callback-Signatur passt nicht

Wenn der Aufrufer zwei Argumente übergibt, die Funktion aber nur eines akzeptiert, entsteht ein `TypeError`.

Daher immer den tatsächlichen Aufruf in `collective_functions.py` mit der Methodensignatur in der Node abgleichen.

### Seitentitel werden doppelt oder an der falschen Stelle bereinigt

Die Namens-Callbacks sollten die fachlichen Eintragsnamen bereinigen, wenn dies Teil ihrer vorgesehenen Aufgabe ist. Andere Titel, beispielsweise Overview-Titel, können einen separaten Bereinigungspfad benötigen.

### Konfiguration allein führt keine Funktion aus

Das Hinterlegen von

```python
render_overview=self._render_overview_markdown
```

führt die Methode nicht aus. Der entsprechende Callback muss später ausdrücklich aufgerufen werden.

---

## 8. Zusammenfassung

Die Architektur beruht auf einer klaren Aufgabenteilung:

- **Node:** Kennt die fachlichen Daten und definiert die passenden Callbacks.
- **`CollectiveConfig`:** Transportiert die Funktionsreferenzen und die Importparameter.
- **`collective_functions.py`:** Ruft die Callbacks an den vorgesehenen Stellen auf und steuert den gemeinsamen Importprozess.
- **`collective_pages.py`:** Stellt Funktionen für das Suchen, Erstellen und Verwalten der Collective-Seiten bereit.

Die entscheidende Idee lautet:

**Die gemeinsame Importfunktion muss nicht wissen, welche konkrete Node sie aufgerufen hat. Sie verwendet die Funktionen, die ihr die Node über `CollectiveConfig` übergeben hat.**

Dadurch können weitere Nodes denselben Importablauf nutzen, ohne dass `collective_functions.py` für jeden neuen Datentyp angepasst werden muss.
