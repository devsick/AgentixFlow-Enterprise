import functools
import time
import traceback
from typing import Any, Callable, Coroutine
from src.shared.monitoring_writer import monitoring_writer

def observe_node(node_name: str):
    """
    Ein Decorator für LangGraph-Nodes, der den Lebenszyklus (Start, Ende, Fehler)
    automatisch erfasst und in den State sowie in das Filesystem schreibt.
    """
    def decorator(func: Callable[..., Coroutine[Any, Any, Any]]):
        @functools.wraps(func)
        async def wrapper(self, state: Any, *args, **kwargs) -> Any:
            graph_id = state.get("graph_id", "unknown_graph")
            run_id = state.get("run_id", "unknown_run")

            # 1. Node Start
            start_time = time.perf_counter()
            await monitoring_writer.log_event(
                graph_id, 
                run_id, 
                "node_started", 
                {"node": node_name, "timestamp": time.time()}
            )
            
            # Update State (für die API/Streaming)
            if "metadata" not in state:
                state["metadata"] = {}
            state["metadata"]["current_node"] = node_name
            state["metadata"]["node_status"] = "running"

            try:
                # 2. Node Ausführung
                result = await func(self, state, *args, **kwargs)

                # 3. Node Ende (Erfolg)
                duration_ms = (time.perf_counter() - start_time) * 1000
                await monitoring_writer.log_event(
                    graph_id, 
                    run_id, 
                    "node_finished", 
                    {"node": node_name, "duration_ms": duration_ms}
                )
                
                # Update State
                state["metadata"]["node_status"] = "completed"
                state["metadata"]["last_node_duration_ms"] = duration_ms

                # Falls der Node ein Dictionary zurückgibt, muss es in den State gemerged werden
                if isinstance(result, dict):
                    # Wir geben das Result zurück, der Graph/LangGraph erledigt das Merging
                    return result
                return result

            except Exception as e:
                # 4. Node Fehler (Failure)
                duration_ms = (time.perf_counter() - start_time) * 1000
                error_details = {
                    "node": node_name,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "traceback": traceback.format_exc(),
                    "duration_ms": duration_ms
                }
                
                await monitoring_writer.log_event(
                    graph_id, 
                    run_id, 
                    "node_failed", 
                    error_details
                )

                # Update State für API/Streaming
                state["metadata"]["node_status"] = "failed"
                state["metadata"]["last_error"] = error_details

                # Fehler weiterwerfen, damit der Graph das Routing (Error-Path) handhaben kann
                raise e

        return wrapper
    return decorator
