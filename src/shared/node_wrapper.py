
import functools
import time
import traceback
from collections.abc import Mapping
from typing import Any, Callable, Coroutine, Optional

from src.shared.monitoring_writer import monitoring_writer


def observe_node(node_name_or_func: Optional[Any] = None):
    """
    Decorator for LangGraph nodes.

    Supports:

        @observe_node
        async def my_node(state):
            ...

        @observe_node("my_node")
        async def my_node(state):
            ...

        @observe_node
        async def __call__(self, state):
            ...
    """

    def decorator(func: Callable[..., Coroutine[Any, Any, Any]]):

        resolved_node_name = (
            node_name_or_func
            if isinstance(node_name_or_func, str)
            else func.__name__
        )

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):

            # Detect function-based nodes and class-based nodes.
            if args and isinstance(args[0], Mapping):
                state = args[0]

            elif len(args) >= 2 and isinstance(args[1], Mapping):
                state = args[1]

            else:
                raise TypeError(
                    f"Node '{resolved_node_name}' received no valid "
                    f"LangGraph state. Arguments: {args}"
                )

            graph_id = state.get("graph_id", "unknown_graph")
            run_id = state.get("run_id", "unknown_run")

            # Ensure metadata exists.
            metadata = dict(state.get("metadata") or {})
            metadata["current_node"] = resolved_node_name
            metadata["node_status"] = "running"

            start_time = time.perf_counter()

            await monitoring_writer.log_event(
                graph_id,
                run_id,
                "node_started",
                {
                    "node": resolved_node_name,
                    "timestamp": time.time(),
                },
            )

            try:
                # Execute the original function with its original arguments.
                result = await func(*args, **kwargs)

                duration_ms = (
                    time.perf_counter() - start_time
                ) * 1000

                await monitoring_writer.log_event(
                    graph_id,
                    run_id,
                    "node_finished",
                    {
                        "node": resolved_node_name,
                        "duration_ms": duration_ms,
                    },
                )

                if not isinstance(result, dict):
                    raise TypeError(
                        f"Node '{resolved_node_name}' returned "
                        f"{type(result).__name__} instead of dict."
                    )

                result_metadata = result.get("metadata") or {}

                updated_metadata = {
                    **metadata,
                    **result_metadata,
                    "current_node": resolved_node_name,
                    "node_status": "completed",
                    "last_node_duration_ms": duration_ms,
                }

                return {
                    **result,
                    "metadata": updated_metadata,
                }

            except Exception as e:

                duration_ms = (
                    time.perf_counter() - start_time
                ) * 1000

                error_details = {
                    "node": resolved_node_name,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "traceback": traceback.format_exc(),
                    "duration_ms": duration_ms,
                }

                await monitoring_writer.log_event(
                    graph_id,
                    run_id,
                    "node_failed",
                    error_details,
                )

                raise

        return wrapper

    if callable(node_name_or_func):
        return decorator(node_name_or_func)

    return decorator
