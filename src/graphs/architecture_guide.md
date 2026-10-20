# Graph Architektur Dokumentation

Dieses Dokument beschreibt die Struktur und das Organisationsprinzip für alle LangGraph-Projekte innerhalb dieses Backends.

## Grundprinzip

Jeder Graph erhält ein eigenes, isoliertes Verzeichnis unter `src/graphs/`. Dies gewährleistet eine saubere Trennung der Zustände, Logiken und Prompts.

## Verzeichnisstruktur eines einzelnen Graphen

Ein Graph-Modul muss folgende Struktur aufweisen:

```text
graphs/[graph_name]/
├── state.py          # Definition des LangGraph State (TypedDict)
├── graph.py           # Definition des Graphen (Nodes, Edges, Workflow)
├── agents/            # Logik-Wrapper für die Agenten-Interaktion
│   └── [agent_name].py
├── nodes/             # Die eigentlichen Node-Funktionen (Workflows)
│   └── [node_name].py
└── prompts/           # Alle Prompts als Markdown-Dateien
    └── [prompt_name].md
```

## Komponentenbeschreibung

### 1. `state.py`
Hier wird das `TypedDict` definiert, welches den Zustand über den gesamten Lebenszyklus des Graphen hinweg hält. Dies ist die "Single Source of Truth" für die Daten innerhalb des Graphen.

### 2. `graph.py`
Dies ist die zentrale Orchestrierungsdatei. Hier wird:
- Der `StateGraph` instanziiert.
- Die Nodes aus dem `nodes/` Verzeichnis hinzugefügt.
- Die Kanten (`edges`) und die logische Flusssteuerung definiert.
- Der `compile()`-Aufruf durchgeführt.

### 3. `nodes/`
Jeder Node ist eine reine Funktion (oder Klasse), die den aktuellen `State` erhält, eine Operation ausführt und den aktualisierten `State` zurückgibt. Die Logik innerhalb der Nodes sollte so granular wie möglich sein.

### 4. `agents/`
Diese Komponente dient als Schnittstelle zwischen dem Graph und der Außenwelt (oder anderen Graphen). Sie kann dazu genutzt werden, spezifische Parameter für einen Durchlauf des Graphen zu setzen oder die Ergebnisse des Graphen aufzubereiten.

### 5. `prompts/`
Um die Logik von der Instruktion zu trennen, werden sämtliche System-Prompts, User-Instructionen oder Few-Shot-Beispiele in `.md` Dateien gespeichert. 
- **Vorteil:** Prompts können ohne Code-Änderungen optimiert werden.
- **Vorteil:** Bessere Lesbarkeit und Versionierung der Instruktionen.
- **Laden:** Die Prompts werden zur Laufzeit aus diesen Dateien eingelesen und in die Nodes injiziert.

---

*Dokumentation erstellt am: $(date +%Y-%m-%d)*
