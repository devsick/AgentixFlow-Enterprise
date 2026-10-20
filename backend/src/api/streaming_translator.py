
# src/api/streaming_translator.py

import json
import time
import uuid
from collections.abc import AsyncIterator
from typing import Any, Awaitable, Callable

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)

from src.api.schemas import (
    ChatCompletionRequest,
    ChatCompletionChunk,
    ChatCompletionChunkChoice,
)
from src.shared.monitoring_writer import monitoring_writer


STREAMING_MODE_LIVE = "live"
STREAMING_MODE_STATUS_ONLY = "status_only"

VALID_STREAMING_MODES = {
    STREAMING_MODE_LIVE,
    STREAMING_MODE_STATUS_ONLY,
}


def _model_dump(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value

    if hasattr(value, "model_dump"):
        return value.model_dump(exclude_none=True)

    if hasattr(value, "dict"):
        return value.dict(exclude_none=True)

    return {}


def _message_content(message: Any) -> str:
    if message is None:
        return ""

    content = getattr(message, "content", None)

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []

        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text", "")
                if isinstance(text, str):
                    parts.append(text)

        return "".join(parts)

    return ""


def _convert_request_messages(
    messages: list[Any],
) -> list[BaseMessage]:
    converted = []

    for message in messages:
        if isinstance(message, dict):
            role = message.get("role", "user")
            content = message.get("content", "")
        else:
            role = getattr(message, "role", "user")
            content = getattr(message, "content", "")

        if content is None:
            content = ""

        if role == "system":
            converted.append(SystemMessage(content=content))
        elif role == "assistant":
            converted.append(AIMessage(content=content))
        elif role == "user":
            converted.append(HumanMessage(content=content))

    return converted


def _extract_reasoning(chunk: Any) -> str:
    additional_kwargs = getattr(chunk, "additional_kwargs", {}) or {}

    reasoning = additional_kwargs.get("reasoning_content", "")

    if not reasoning:
        reasoning = getattr(chunk, "reasoning_content", "") or ""

    return reasoning if isinstance(reasoning, str) else ""


def _convert_tool_call_chunks(chunk: Any) -> list[dict[str, Any]]:
    tool_call_chunks = getattr(chunk, "tool_call_chunks", None) or []
    converted = []

    for tool_chunk in tool_call_chunks:
        if not isinstance(tool_chunk, dict):
            tool_chunk = _model_dump(tool_chunk)

        index = tool_chunk.get("index")
        if index is None:
            index = len(converted)

        tool_call = {"index": index}

        call_id = tool_chunk.get("id")
        if call_id:
            tool_call["id"] = call_id

        function = {}

        name = tool_chunk.get("name")
        if name:
            function["name"] = name

        arguments = tool_chunk.get("args")
        if arguments is None:
            arguments = tool_chunk.get("arguments")

        if arguments is not None:
            if not isinstance(arguments, str):
                arguments = json.dumps(arguments, ensure_ascii=False)

            function["arguments"] = arguments

        if function:
            tool_call["type"] = "function"
            tool_call["function"] = function
            converted.append(tool_call)

    return converted


def _extract_ai_messages(output: Any) -> list[AIMessage]:
    found = []

    def visit(value: Any) -> None:
        if isinstance(value, AIMessage):
            found.append(value)
            return

        if isinstance(value, BaseMessage):
            return

        if isinstance(value, dict):
            for key in ("messages", "output", "response", "result"):
                if key in value:
                    visit(value[key])
            return

        if isinstance(value, (list, tuple)):
            for item in value:
                visit(item)

    visit(output)
    return found


def _dump_chunk_for_monitoring(chunk: Any) -> dict[str, Any]:
    """Preserve the complete model chunk for monitoring."""
    try:
        if hasattr(chunk, "model_dump"):
            data = chunk.model_dump()
        elif hasattr(chunk, "dict"):
            data = chunk.dict()
        else:
            data = vars(chunk).copy()

        if hasattr(chunk, "additional_kwargs"):
            data["additional_kwargs"] = chunk.additional_kwargs

        return data

    except Exception as exc:
        return {
            "error": f"Could not dump chunk: {exc}",
            "raw_repr": str(chunk),
        }


class StreamingTranslator:
    def __init__(self, graph: Any):
        self.graph = graph

    async def stream(
        self,
        request: ChatCompletionRequest,
        initial_state: dict[str, Any] | None = None,
        model_id: str | None = None,
        graph_id: str | None = None,
        run_id: str | None = None,
    ) -> AsyncIterator[str]:

        model_name = model_id or getattr(request, "model", None) or "unknown"
        graph_id = graph_id or model_name
        run_id = run_id or str(uuid.uuid4())

        stream_id = f"chatcmpl-{uuid.uuid4()}"
        created_time = int(time.time())

        if initial_state is None:
            initial_state = {
                "messages": _convert_request_messages(
                    getattr(request, "messages", []) or []
                ),
                "run_id": run_id,
                "graph_id": graph_id,
            }
        else:
            initial_state.setdefault("run_id", run_id)
            initial_state.setdefault("graph_id", graph_id)

        # Monitoring muss initialisiert sein, bevor der Graph startet.
        await monitoring_writer.initialize_run(
            graph_id,
            run_id,
            {"model_id": model_name},
        )

        log_messages = []
        for msg in getattr(request, "messages", []) or []:
            if isinstance(msg, dict):
                role = msg.get("role")
                content = msg.get("content") or ""
            else:
                role = getattr(msg, "role", None)
                content = getattr(msg, "content", None) or ""

            log_messages.append({
                "role": role,
                "content": content,
            })

        await monitoring_writer.log_event(
            graph_id,
            run_id,
            "user_request",
            {"messages": log_messages},
        )

        emitted_node_runs: set[str] = set()

        async for event in self.graph.astream_events(
            initial_state,
            version="v2",
        ):
            event_type = event.get("event", "")
            event_data = event.get("data") or {}
            metadata = event.get("metadata") or {}

            print(f"Event: {event_type} | Metadata: {metadata}", flush=True)
            streaming_mode = metadata.get(
                "streaming_mode",
                STREAMING_MODE_LIVE,
            )

            if streaming_mode not in VALID_STREAMING_MODES:
                streaming_mode = STREAMING_MODE_LIVE

            node_name = metadata.get("langgraph_node")

            # -------------------------------------------------
            # 1. LLM-Streaming: vollständig protokollieren
            # -------------------------------------------------
            if event_type == "on_chat_model_stream":
                chunk = event_data.get("chunk")

                if chunk is None:
                    continue

                full_chunk_data = _dump_chunk_for_monitoring(chunk)

                await monitoring_writer.log_event(
                    graph_id,
                    run_id,
                    "llm_chunk_full",
                    {"data": full_chunk_data},
                )

                content = _message_content(chunk)
                reasoning_content = _extract_reasoning(chunk)

                if reasoning_content:
                    await monitoring_writer.log_event(
                        graph_id,
                        run_id,
                        "llm_thinking",
                        {"content": reasoning_content},
                    )

                if content:
                    await monitoring_writer.log_event(
                        graph_id,
                        run_id,
                        "llm_content",
                        {"content": content},
                    )

                # Nur Content wird abhängig vom Modus gefiltert.
                delta = {}

                if streaming_mode == STREAMING_MODE_LIVE and content:
                    delta["content"] = content

                if reasoning_content:
                    delta["reasoning_content"] = reasoning_content

                tool_calls = _convert_tool_call_chunks(chunk)
                if tool_calls:
                    delta["tool_calls"] = tool_calls

                if delta:
                    yield self._format_chunk(
                        stream_id,
                        created_time,
                        model_name,
                        delta,
                    )

                continue

            # -------------------------------------------------
            # 2. Tool-Monitoring und bestehende SSE-Events
            # -------------------------------------------------
            if event_type == "on_tool_start":
                tool_data = {
                    "name": event.get("name"),
                    "input": event_data.get("input", {}),
                }

                await monitoring_writer.log_event(
                    graph_id,
                    run_id,
                    "tool_start",
                    tool_data,
                )

                yield (
                    "data: "
                    + json.dumps(
                        {"type": "tool_start", **tool_data},
                        default=str,
                    )
                    + "\n\n"
                )

                continue

            if event_type == "on_tool_end":
                tool_data = {
                    "name": event.get("name"),
                    "output": str(event_data.get("output", "")),
                }

                await monitoring_writer.log_event(
                    graph_id,
                    run_id,
                    "tool_end",
                    tool_data,
                )

                yield (
                    "data: "
                    + json.dumps(
                        {"type": "tool_end", **tool_data},
                        default=str,
                    )
                    + "\n\n"
                )

                continue

            # -------------------------------------------------
            # 3. LLM-Ende weiterhin protokollieren
            # -------------------------------------------------
            if event_type == "on_chat_model_end":
                await monitoring_writer.log_event(
                    graph_id,
                    run_id,
                    "llm_end",
                    {"output": str(event_data.get("output"))},
                )

                continue

            # -------------------------------------------------
            # 4. Statusmeldung beim Ende eines status_only-Knotens
            # -------------------------------------------------
            if event_type != "on_chain_end":
                continue

            if not node_name:
                continue

            if streaming_mode != STREAMING_MODE_STATUS_ONLY:
                continue

            node_run_key = f"{node_name}:{event.get('run_id', '')}"

            if node_run_key in emitted_node_runs:
                continue

            ai_messages = _extract_ai_messages(event_data.get("output"))

            if not ai_messages:
                continue

            status_message = ai_messages[-1]
            status_text = _message_content(status_message)

            if not status_text:
                continue

            emitted_node_runs.add(node_run_key)

            await monitoring_writer.log_event(
                graph_id,
                run_id,
                "node_status",
                {
                    "node": node_name,
                    "content": status_text,
                    "streaming_mode": streaming_mode,
                },
            )

            yield self._format_chunk(
                stream_id,
                created_time,
                model_name,
                {"content": status_text},
            )

        yield "data: [DONE]\n\n"

    @staticmethod
    def _format_chunk(
        stream_id: str,
        created_time: int,
        model_name: str,
        delta: dict[str, Any],
        finish_reason: str | None = None,
    ) -> str:
        chunk = ChatCompletionChunk(
            id=stream_id,
            object="chat.completion.chunk",
            created=created_time,
            model=model_name,
            choices=[
                ChatCompletionChunkChoice(
                    index=0,
                    delta=delta,
                    finish_reason=finish_reason,
                )
            ],
        )

        if hasattr(chunk, "model_dump_json"):
            serialized = chunk.model_dump_json(exclude_none=True)
        else:
            serialized = chunk.json(exclude_none=True)

        return f"data: {serialized}\n\n"


async def stream_translator(
    model_id: str,
    request: ChatCompletionRequest,
    graph_factory: Callable[[], Awaitable[Any]],
) -> AsyncIterator[str]:
    """
    Kompatible öffentliche Schnittstelle für chat_completions.py.
    Erhält API-Key-Prüfung, Monitoring und Graph-Initialisierung.
    """

    factory = None

    # Bestehendes Verhalten: registriertes Modell auflösen.
    # Die Factory wird über den übergebenen Wrapper aufgerufen.
    graph = await graph_factory()

    # API-Key-Verifizierung aus der bisherigen Implementierung.
    from src.settings.config_store import config_store

    profile = config_store.llm_profiles.get(model_id)

    if profile and "api_key" in profile:
        if request.api_key != profile["api_key"]:
            yield (
                "data: "
                + json.dumps({"error": "Invalid API Key"})
                + "\n\n"
            )
            yield "data: [DONE]\n\n"
            return

    # API-Key an Graph bzw. Agent weitergeben.
    if hasattr(graph, "set_api_key"):
        await graph.set_api_key(request.api_key)
    elif hasattr(graph, "api_key"):
        graph.api_key = request.api_key
    elif hasattr(graph, "agent") and hasattr(graph.agent, "set_api_key"):
        await graph.agent.set_api_key(request.api_key)
    elif hasattr(graph, "agent") and hasattr(graph.agent, "api_key"):
        graph.agent.api_key = request.api_key

    run_id = str(uuid.uuid4())
    graph_id = model_id

    translator = StreamingTranslator(graph)

    async for chunk in translator.stream(
        request=request,
        model_id=model_id,
        graph_id=graph_id,
        run_id=run_id,
        initial_state={
            "messages": _convert_request_messages(
                getattr(request, "messages", []) or []
            ),
            "run_id": run_id,
            "graph_id": graph_id,
        },
    ):
        yield chunk
