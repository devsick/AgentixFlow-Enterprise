# Flow-Agent-API

## Projektziel
Die **Flow-Agent-API** ist eine hochperformante, OpenAI-kompatible Proxy-Schnittstelle für LangGraph-basierte Workflows. 

Das Ziel ist es, komplexe Agenten-Logiken (mit Flows, Tool-Calls, Bedingungen und komplexen Zuständen) so einfach zu abstrahieren, dass sie wie ein Standard-LLM-Modell angesprochen werden können. Dies ermöglicht eine extrem schnelle Entwicklung von Agenten-Workflows, die sofort in bestehende Ökosysteme (wie AnythingLLM, Custom UIs oder andere LLM-Clients) integriert werden können, ohne auf schwerfällige Low-Code-Builder wie Flowise-AI angewiesen zu sein.

## Kernmerkmale
- **OpenAI-Kompatibilität:** Implementierung der Standards für `/v1/chat/completions`, `/v1/responses` und `/v1/models`.
- **Echtzeit-Streaming:** Unterstützung von `astream_events`, um Token-Generierung, "Thinking/Reasoning"-Content und Tool-Call-Informationen in Echtzeit an den Client zu senden.
- **Hybrid Observability:** 
    - **Hot Path:** Sofortiges Feedback über den Stream für die UI.
    - **Cold Path:** Dateibasierte Persistenz von Laufzeitdaten (`meta.json`, `state.json`, `events.jsonl`) im Verzeichnis `monitoring_runs/` zur nachträglichen Analyse, ohne den Overhead einer Datenbank.
- **Automatisches Monitoring:** Ein `observe_node` Decorator übernimmt das Tracing von Node-Lebenszyklen, Fehlermeldungen und Metriken.

## Aktueller Stand
Die Grundarchitektur der API ist implementiert und einsatzbereit:

### ✅ Implementiert
- [x] **API-Struktur:** FastAPI-Basis mit modularer Router-Architektur.
- [x] **Model Registry:** Dynamische Registrierung von LangGraph-Graphen als Modelle.
- [x] **Chat Completions:** Streaming-fähiger Endpunkt inklusive Unterstützung für Reasoning-Content.
- [x] **Responses API:** Implementierung des neuen OpenAI-Standards für strukturierte Antworten.
- [x] **Models Discovery:** Endpoint zur Auflistung verfügbarer Agenten-Modelle.
- [x] **Monitoring Writer:** Dateibasierte Protokollierung von Run-IDs, States und Events.
- [x] **Node Observer:** Decorator zur automatisierten Erfassung von Node-Laufzeiten und Fehlern.
- [x] **Containerisierung:** Optimierte Multi-Stage `Containerfile` und `docker-compose.yml` (Podman-ready).

### 🛠 In Arbeit / Nächste Schritte
- [ ] Vollständige Implementierung des `responses`-Modells (Vollständiger State-Mapping).
- [ ] Erweiterung der Error-Handling-Patterns für komplexere Retry-Logiken.
- [ ] Optimierung der Bereinigung (Retention) der `monitoring_runs`.
