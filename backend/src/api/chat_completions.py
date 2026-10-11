import json
import time
import uuid
import asyncio
from typing import AsyncGenerator
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from src.api.registry import registry
from src.api.schemas import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionChunk,
    ChatCompletionChunkChoice,
    ChatCompletionUsage
)
from src.shared.monitoring_writer import monitoring_writer

router = APIRouter()

async def stream_generator(
    model_id: str, 
    request: ChatCompletionRequest
) -> AsyncGenerator[str, None]:
    """
    Generatort, der LangGraph-Events in OpenAI-konforme SSE-Chunks übersetzt.
    """
    factory = registry.get_model_factory(model_id)
    if not factory:
        yield f"data: {json.dumps({'error': f'Model {model_id} not found'})}\n\n"
        return

    # API Key Verifizierung
    from src.settings.config_store import config_store
    profile = config_store.llm_profiles.get(model_id)
    
    if profile and "api_key" in profile:
        if request.api_key != profile["api_key"]:
            yield f"data: {json.dumps({'error': 'Invalid API Key'})}\n\n"
            return

    graph = await factory()
    # Pass the api_key to the graph/agent if needed
    if hasattr(graph, 'set_api_key'):
        await graph.set_api_key(request.api_key)
    elif hasattr(graph, 'api_key'):
        graph.api_key = request.api_key
    elif hasattr(graph, 'agent') and hasattr(graph.agent, 'set_api_key'):
        await graph.agent.set_api_key(request.api_key)
    elif hasattr(graph, 'agent') and hasattr(graph.agent, 'api_key'):
        graph.agent.api_key = request.api_key

    
    # Konvertiere ChatMessage aus Request in LangChain Nachrichten
    from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
    
    input_messages = []
    for msg in request.messages:
        if msg.role == "system":
            input_messages.append(SystemMessage(content=msg.content or ""))
        elif msg.role == "user":
            input_messages.append(HumanMessage(content=msg.content or ""))
        elif msg.role == "assistant":
            input_messages.append(AIMessage(content=msg.content or ""))
        # Andere Rollen (tool, function) können hier ergänzt werden

    # Generiere Run-Identitäten für das Monitoring
    run_id = str(uuid.uuid4())
    graph_id = model_id # In diesem Kontext ist das Modell der Graph-ID gleich

    # Initialer State für den Graph inklusive Monitoring-IDs
    initial_state = {
        "messages": input_messages,
        "run_id": run_id,
        "graph_id": graph_id
    }

    # WICHTIG: Verzeichnis für Monitoring initialisieren, bevor der Graph startet!
    await monitoring_writer.initialize_run(graph_id, run_id, {"model_id": model_id})

    # Logge den User Request sofort zu Beginn
    # Wir nutzen die ursprünglichen Pydantic-Modelle aus dem Request, um auf .role zuzugreifen
    log_messages = []
    for msg in request.messages:
        log_messages.append({"role": msg.role, "content": msg.content or ""})

    await monitoring_writer.log_event(
        graph_id, 
        run_id, 
        "user_request", 
        {"messages": log_messages}
    )

    # OpenAI-Metadaten
    stream_id = f"chatcmpl-{uuid.uuid4()}"
    created_time = int(time.time())

    # Wir nutzen astream_events, um die internen LLM-Events (Streaming) einzufangen.
    async for event in graph.astream_events(initial_state, version="v2"):
        
        # 1. Handle LLM Streaming Chunks (on_chat_model_stream)
        if event["event"] == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            if not chunk:
                continue
            
            # --- LOGGING (FULL DUMP) ---
            # Wir loggen den kompletten Chunk, um alle Attribute (inkl. Thinking/Reasoning) zu erfassen.
            try:
                if hasattr(chunk, 'model_dump'):
                    full_chunk_data = chunk.model_dump()
                elif hasattr(chunk, 'dict'):
                    full_chunk_data = chunk.dict()
                else:
                    full_chunk_data = vars(chunk).copy()
                
                # Sicherstellen, dass additional_kwargs explizit enthalten sind
                if hasattr(chunk, 'additional_kwargs'):
                    full_chunk_data['additional_kwargs'] = chunk.additional_kwargs
            except Exception as e:
                full_chunk_data = {"error": f"Could not dump chunk: {str(e)}", "raw_repr": str(chunk)}

            await monitoring_writer.log_event(graph_id, run_id, "llm_chunk_full", {"data": full_chunk_data})
            # ----------------------------

            # Für den OpenAI-Stream extrahieren wir weiterhin die benötigten Felder
            content = getattr(chunk, 'content', "")
            
            # Reasoning Content ist oft in additional_kwargs versteckt
            reasoning_content = ""
            if hasattr(chunk, 'additional_kwargs'):
                reasoning_content = chunk.additional_kwargs.get("reasoning_content", "")
            
            if not reasoning_content and hasattr(chunk, 'reasoning_content'):
                reasoning_content = chunk.reasoning_content

            # --- LOGGING (PREVIOUS) ---
            if reasoning_content:
                await monitoring_writer.log_event(graph_id, run_id, "llm_thinking", {"content": reasoning_content})
            if content:
                await monitoring_writer.log_event(graph_id, run_id, "llm_content", {"content": content})
            # ----------------------------


            # Erstelle den OpenAI Chunk
            delta = {"content": content}
            if reasoning_content:
                delta["reasoning_content"] = reasoning_content
            
            if hasattr(chunk, 'tool_call_chunks') and chunk.tool_call_chunks:
                delta["tool_calls"] = chunk.tool_call_chunks

            chunk_obj = ChatCompletionChunk(
                id=stream_id,
                object="chat.completion.chunk",
                created=created_time,
                model=model_id,
                choices=[ChatCompletionChunkChoice(
                    index=0,
                    delta=delta
                )]
            )
            yield f"data: {chunk_obj.model_dump_json()}\n\n"

        # 2. Handle Tool Calls
        elif event["event"] == "on_tool_call":
            await monitoring_writer.log_event(
                graph_id, 
                run_id, 
                "tool_call", 
                {"tool_call": event["data"].get("tool_call")}
            )

        # 3. Handle LLM End (Final Response)
        elif event["event"] == "on_chat_model_end":
            await monitoring_writer.log_event(
                graph_id, 
                run_id, 
                "llm_end", 
                {"output": str(event["data"].get("output"))}
            )

@router.post("/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """
    OpenAI-kompatibler Chat Completions Endpunkt.
    """
    model_id = request.model
    
    if request.stream:
        return StreamingResponse(
            stream_generator(model_id, request),
            media_type="text/event-stream"
        )
    else:
        return {"error": "Only streaming is supported at this endpoint. Set stream=true."}
