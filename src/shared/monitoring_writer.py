import json
import os
import asyncio
import aiofiles
from pathlib import Path
from datetime import datetime
from typing import Any, Dict

class MonitoringWriter:
    """
    Writes graph runtime data to the filesystem.
    Structure: backend/src/monitoring_runs/{graph_id}/{run_id}/
    """

    def __init__(self, base_dir: str = "/app/monitoring_runs"):
        self.base_dir = Path(base_dir)

    def _get_run_dir(self, graph_id: str, run_id: str) -> Path:
        return self.base_dir / graph_id / run_id

    async def initialize_run(self, graph_id: str, run_id: str, initial_meta: Dict[str, Any]):
        """Initializes the directory and writes the meta.json."""
        run_dir = self._get_run_dir(graph_id, run_id)
        run_dir.mkdir(parents=True, exist_ok=True)

        meta_path = run_dir / "meta.json"
        meta_data = {
            "run_id": run_id,
            "graph_id": graph_id,
            "start_time": datetime.now().isoformat(),
            **initial_meta
        }

        async with aiofiles.open(meta_path, mode='w', encoding='utf-8') as f:
            await f.write(json.dumps(meta_data, indent=2))

    async def write_state(self, graph_id: str, run_id: str, state: Dict[str, Any]):
        """Writes a snapshot of the state to state.json (atomically via rename)."""
        run_dir = self._get_run_dir(graph_id, run_id)
        state_path = run_dir / "state.json"
        temp_path = run_dir / "state.json.tmp"

        async with aiofiles.open(temp_path, mode='w', encoding='utf-8') as f:
            await f.write(json.dumps(state, indent=2))
        
        # Atomic replace

        os.replace(temp_path, state_path)

    async def log_event(self, graph_id: str, run_id: str, event_type: str, details: Dict[str, Any]):
        """Writes an event to events.jsonl."""
        run_dir = self._get_run_dir(graph_id, run_id)
        events_path = run_dir / "events.jsonl"

        event_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": event_type,
            **details
        }

        async with aiofiles.open(events_path, mode='a', encoding='utf-8') as f:
            await f.write(json.dumps(event_entry) + "\n")

# Singleton for the application
monitoring_writer = MonitoringWriter()
