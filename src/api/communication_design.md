# Kommunikations- und Streaming-Architektur: Analyse & Design

Diese Dokumentation beschreibt den aktuellen Stand und das geplante Kommunikationsmodell für das Streaming von Agenten-Antworten an den User. Das Ziel ist eine granulare Steuerung darüber, welche Informationen (Text, Status, Tool-Aufrufe) wann an den User gesendet werden.

## 1. Kernkonzept: Die `streaming_policy`

Das System nutzt eine `StreamMode`-Logik, um zu entscheiden, wie ein Node (und damit der dahinterliegende Agent) kommuniziert. Die Policy wird anhand des Node-Namens oder expliziter Metadaten bestimmt.

### Stream-Modi (`src/shared/streaming_policy.py`)

| Modus | Verhalten | Zielsetzung |
| :--- | :--- | :--- |
| `live` | Streamt jeden LLM-Text-Chunk sofort (`on_chat_model_stream`). | Standard für Chat-Agents. |
| `final_only` | Streamt keine internen Chunks. Gibt nur die fertige `AIMessage` am Ende des Nodes aus. | Für Agenten, die nur "schweigen" sollen, bis das Ergebnis feststeht. |
| `status_only` | Streamt keine Text-Chunks. Gibt nur Statusinformationen (oder die finale Nachricht) aus. | Für Funktions-Nodes/Tool-Agenten, die nur dem User sagen sollen, was sie gerade tun. |

---

## 2. Kommunikations-Graph & Event-Flow

Der Datenfluss von der LLM-Antwort bis zum User-Streaming folgt diesem Pfad:

### A. Agent-Ebene (`src/graphs/pure_chat/agents/chat_agent.py`)
Der Agent führt den eigentlichen LLM-Call aus (via `self.llm.ainvoke`). 
- **Output:** Eine `AIMessage` (oder ein `AIMessageChunk` beim Streaming).
- **Wichtig:** Der Agent selbst ist noch "dumm" bezüglich der Streaming-Policy; er liefert einfach die Daten, die das LLM generiert.

### B. Node-Ebene (`src/graphs/pure_chat/nodes/chat_node.py`)
Der Node fungiert als Wrapper für den Agenten und bereitet die Daten für den Graph-State vor.
- **Aktion:** Ruft `agent.run(messages)` auf.
- **Output:** Ein Dictionary, das die neue `AIMessage` und `metadata` (Tokens, Reasoning, Tool-Calls) enthält.
- **Integration:** Hier wird der `@observe_node` Decorator (`src/shared/node_wrapper.py`) genutzt, um den Lebenszyklus (`node_started`, `node_finished`) zu tracken.

### C. Streaming-Übersetzer (`src/api/streaming_translator.py`)
Dies ist die zentrale Instanz, die die LangGraph-Events (`astream_events`) überwacht und in das OpenAI-konforme SSE-Format umwandelt.

**Der aktuelle (fehlerhafte/unvollständige) Flow:**
Der `stream_translator` iteriert über `graph.astream_events`. Aktuell reagiert er primär auf:
- `on_chat_model_stream`: Hier werden Chunks direkt an den User gesendet.

**Das Problem:** Der Translator "weiß" aktuell noch nicht ausreichend, welche `streaming_policy` für den gerade laufenden Node gilt. Er streamt `on_chat_model_stream` Events blindlings durch, was dem Ziel widerspricht, dass ein `status_only` Node keine Text-Chunks senden darf.

### D. API-Endpoint (`src/api/chat_completions.py`)
Der Endpoint startet den Prozess und stellt die Verbindung zum Client her. Er nutzt die `get_stream_mode(event)` Funktion, um die Policy aus den Metadaten des Events zu extrahieren.

---

## 3. Detaillierter Kommunikations-Workflow (Ziel-Zustand)

Um das Ziel zu erreichen, muss der `stream_translator` die `streaming_policy` auf Event-Ebene berücksichtigen.

### Event-Matrix für den `stream_translator`

| Event-Typ | Kontext / Policy | Aktion des Translators | Ziel-Output |
| :--- | :--- | :--- | :--- |
| `on_chat_model_stream` | `live` | Chunk extrahieren & senden. | `delta: {content: "..."}` |
| `on_chat_model_stream` | `final_only` | **Ignorieren.** | (Keine Ausgabe) |
| `on_chat_model_stream` | `status_only` | **Ignorieren.** | (Keine Ausgabe) |
| `on_chain_end` (Node) | `status_only` | Wenn der Node eine Status-Nachricht hat, senden. | `delta: {content: "Suche..."}` |
| `on_chain_end` (Node) | `any` | Die finale `AIMessage` des Nodes senden. | `content: "Fertig!"` |

### Beispiel: Ein "Funktions-Agent" (Status-only)

1. **Node startet:** `chat_node` wird aufgerufen.
2. **Agent arbeitet:** `chat_agent` ruft LLM auf. Das LLM generiert Text-Chunks.
3. **Streaming-Event:** `on_chat_model_stream` feuert.
4. **Translator-Logik:**
   - Der Translator prüft `event["metadata"]["langgraph_node"]`.
   - Er sieht: Mode ist `status_only`.
   - **Ergebnis:** Er verwirft die `on_chat_model_stream` Events. Der User sieht nichts.
5. **Node endet:** `on_chain_end` feuert.
6. **Translator-Logik:**
   - Er sieht die finale `AIMessage` im State (z.B. "Ich habe die Datei gefunden").
   - Er sendet diese als einen einzigen, finalen Chunk.
   - **Ergebnis:** Der User sieht nur: "Ich habe die Datei gefunden." (Kein getipptes Text-Streaming).

---

## 4. Zusammenfassung der Verantwortlichkeiten

- **`streaming_policy.py`**: Definiert die erlaubten Modi.
- **`node_wrapper.py`**: Sorgt dafür, dass Metadaten (Node-Name) im State landen, damit sie im Streaming genutzt werden können.
- **`chat_agent.py`**: Liefert die Rohdaten (Messages).
- **`streaming_translator.py` (Kritisch!)**: Muss die Logik implementieren, die `on_chat_model_stream` Events basierend auf der `streaming_policy` filtert.
- **`chat_completions.py`**: Orchestriert den Start.

**Wichtig für die Umsetzung:** 
`thinking` (Reasoning) und `tool_calls` bleiben unberührt. Das bedeutet, selbst im `status_only` Modus könnten (falls technisch so implementiert) Reasoning-Chunks oder Tool-Call-Informationen durchgelassen werden, sofern dies gewünscht ist. Die Policy bezieht sich primär auf die `content`-Eigenschaft der `AIMessage`.
