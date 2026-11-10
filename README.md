# AgentixFlow-Enterprise

## Project Vision
**AgentixFlow-Enterprise** is a high-performance, enterprise-grade orchestration framework designed to transform complex business processes into scalable, autonomous agentic workflows. 

Unlike simple chatbot implementations, this framework provides the industrial-strength infrastructure required to deploy, manage, and monitor sophisticated multi-agent systems. It abstracts complex agentic logic into standardized "models," allowing them to be seamlessly integrated into any existing ecosystem (such as AnythingLLM, custom enterprise UIs, or standard LLM clients) via OpenAI-compatible interfaces.

## Core Capabilities

### 🚀 Enterprise Orchestration
*   **Model-as-a-Service:** Abstract complex LangGraph workflows (with multi-step flows, tool-use, and conditional logic) into standardized, addressable models.
*   **Dynamic Model Registry:** A robust registry system that allows for the rapid deployment and discovery of new agentic workflows without system downtime.
*   **Multi-Protocol Connectivity:** Designed to bridge the gap between diverse LLM backends (OpenAI, Anthropic, Ollama, etc.) and specialized enterprise tools via the Model Context Protocol (MCP).

### 📡 Real-Time Intelligence
*   **Continuous Streaming:** Leverages `astream_events` to provide a "live" experience, streaming token generation, reasoning/thinking content, and real-time tool-call updates via Server-Sent Events (SSE).
*   **Seamless Integration:** Highly compatible with the OpenAI API standard (`/v1/chat/completions`, `/v1/responses`, `/v1/models`), making it a "drop-in" upgrade for any existing LLM application.

### 👁️ Industrial-Grade Observability
*   **Hybrid Monitoring Architecture:** 
    *   **Hot Path:** Real-time feedback streamed directly to the user for immediate interaction.
    *   **Cold Path:** Deep, file-based persistence of every runtime event, state change, and metadata in the `monitoring_runs/` directory for forensic analysis, auditing, and debugging.
*   **Automated Lifecycle Tracing:** Built-in decorators for automated capture of node runtimes, error states, and performance metrics.

---

## Developer Guide: Implementing an Agentic Workflow

To integrate a new business process into the framework, follow this standardized workflow:

### 1. Configuration
Update `src/config/config.json` to define your environment:
- Register new **MCP servers** to provide tools to your agents.
- Configure **LLM profiles** for different model backends.

### 2. Workflow Structure
Create a new directory under `src/graphs/<graph_name>/` following this architecture:
```text
src/graphs/graph_name/
├── agents/        # Agent definitions and specialized system prompts
├── nodes/         # Individual node implementations (the "steps" of the process)
├── state.py       # Defines the shared state and token aggregation logic
└── graph.py        # Defines the LangGraph orchestration workflow
```

### 3. Implementation Standards
*   **State-Driven Tooling:** Use the graph state to store and pass initialized MCP clients, ensuring any node can access enterprise tools securely.
*   **Automated Monitoring:** Every node must use the `observe_node()` decorator to ensure the workflow is fully traceable in the monitoring logs.
*   **Standardized Registration:** Register your new graph in `src/api/registry.py` to make it instantly available as a model.

---

## Current Implementation Status

### ✅ Core Infrastructure
- [x] **High-Performance API:** Modular FastAPI architecture designed for scale.
- [x] **Dynamic Model Registry:** Automates the management of agentic workflows.
- [x] **Streaming Engine:** Full support for reasoning and tool-call streaming.
- [x] **Observability Suite:** Integrated monitoring for real-time and forensic analysis.
- [x] **Containerized Deployment:** Production-ready multi-stage containerization.

### 🛠 Roadmap & Future Directions
- [ ] **Advanced Multi-Protocol Support:** Deep native integration for Ollama, Anthropic, and more.
- [ ] **Modular Memory Service:** Connectivity for diverse vector databases with built-in GDPR/Privacy compliance.
- [ ] **Automated QA & Evaluation:** Framework for testing and validating agentic reliability.
- [ ] **Distributed Orchestration:** Support for cross-node, decentralized agent execution.
