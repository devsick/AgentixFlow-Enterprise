# Execution Plan: Profile Management Graph

## Phase 1: Infrastructure & Setup
- [ ] Create directory structure (`nodes/`, `prompts/`)
- [ ] Analyze `nextcloud_mcp.json` for tool mapping
- [ ] Define `ProfileManagementState` in `src/graphs/profile_management/state.py` (extending `MultiAgentState`)

## Phase 2: Component Implementation
- [ ] **Orchestrator**
    - [ ] Create `src/graphs/profile_management/prompts/orchestrator.txt` (truncated version of the master prompt)
    - [ ] Create `src/graphs/profile_management/nodes/orchestrator.py`
- [ ] **Detect Collective Agent**
    - [ ] Create `src/graphs/profile_management/prompts/detect_collective.txt` (full strict prompt)
    - [ ] Create `src/graphs/profile_management/nodes/detect_collective.py` (with tool limiting)

## Phase 3: Graph Orchestration
- [ ] Create `src/graphs/profile_management/graph.py`
- [ ] Implement routing logic (Conditional Edges) from Orchestrator to `detect_collective`
- [ ] Connect nodes to the StateGraph

## Phase 4: Validation & Testing
- [ ] Unit test: `detect_collective` with mock/real Nextcloud tools
- [ ] Integration test: Full flow from User Message $\rightarrow$ Orchestrator $\rightarrow$ Detect Collective $\rightarrow$ End
