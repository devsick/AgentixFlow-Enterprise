# Flow-Agent-API

## Project Goal
The **Flow-Agent-API** is a high-performance, OpenAI-compatible proxy interface for LangGraph-based workflows.

The goal is to abstract complex agent logics (with flows, tool calls, conditions, and complex states) so simply that they can be addressed like a standard LLM model. This enables extremely fast development of agent workflows that can be immediately integrated into existing ecosystems (such as AnythingLLM, custom UIs, or other LLM clients) without relying on cumbersome low-code builders like Flowise-AI.

## Core Features
- **OpenAI Compatibility:** Implementation of the standards for `/v1/chat/completions`, `/v1/responses`, and `/v1/models`.
- **Real-time Streaming:** Support for `astream_events` to send token generation, "thinking/reasoning" content, and tool-call information to the client in real-time.
- **Hybrid Observability:**
    - **Hot Path:** Immediate feedback via the stream for the UI.
    - **Cold Path:** File-based persistence of runtime data (`meta.json`, `state.json`, `events.jsonl`) in the `monitoring_runs/` directory for subsequent analysis, without the overhead of a database.
- **Automatic Monitoring:** An `observe_node` decorator handles the tracing of node lifecycles, error messages, and metrics.

## How to Create a New Graph (Model)
To implement a new agentic workflow and expose it as a model, follow these steps:

### 1. Configuration
Update `src/config/config.json` to include any necessary new components:
- Add new **MCP servers** if required.
- Add or modify **LLM profiles** as needed.

*Note: If you are adding a new MCP server, you must first create a corresponding `mcp_client.py` in `src/tools/`.*

### 2. Directory Structure
Create a new directory for your graph under `src/graphs/graph_name/` with the following structure:
```text
src/graphs/graph_name/
├── agents/        # Contains the agent definition (created by LLM) and its system prompt
├── nodes/         # Contains the individual node implementations
├── state.py       # Defines the graph state
└── graph.py        # Defines the LangGraph workflow
```

### 3. Implementation Details
- **State Management:** In `state.py`, define properties to store initialized MCP clients. This allows any node within the graph to access the client directly from the state.
- **MCP Initialization:** Implement an `mcp_initializer` node for every required MCP client. This node is responsible for initializing the client and saving it into the graph state.
- **Node Standard:** Every node must:
    - Import `node_wrapper`.
    - Use the `observe_node()` decorator to enable automated lifecycle monitoring.
    - Import `monitoring_writer.py` if additional custom telemetry/logging is required.
- **Registration:** Finally, register your new graph in `src/api/registry.py` to make it discoverable via the Models Discovery endpoint.

## Current Status
The basic architecture of the API is implemented and ready for use:

### ✅ Implemented
- [x] **API Structure:** FastAPI basis with modular router architecture.
- [x] **Model Registry:** Dynamic registration of LangGraph graphs as models.
- [x] **Chat Completions:** Streaming-capable endpoint including support for reasoning content.
- [x] **Responses API:** Implementation of the new OpenAI standard for structured responses.
- [x] **Models Discovery:** Endpoint for listing available agent models.
- [x] **Monitoring Writer:** File-based logging of run IDs, states, and events.
- [x] **Node Observer:** Decorator for automated capture of node runtimes and errors.
- [x] **Containerization:** Optimized multi-stage `Containerfile` and `docker-compose.yml` (Podman-ready).

### 🛠 In Progress / Next Steps
- [ ] Full implementation of the `responses` model (complete state mapping).
- [ ] Extension of error-handling patterns for more complex retry logics.
- [ ] Optimization of the cleanup (retention) of `monitoring_runs`.