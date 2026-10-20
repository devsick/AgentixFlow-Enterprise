import json
import time
import uuid
import asyncio
from typing import AsyncGenerator
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from src.api.registry import registry
from src.api.schemas import (
    ResponseRequest,
    ResponseChunk,
    ResponseChunkChoice
)

async def responses_generator(
    model_id: str, 
    request: ResponseRequest,
    graph_factory: any
) -> AsyncGenerator[str, None]:
    """
    Generatort, der LangGraph-Events in OpenAI-konforme SSE-Chunks für die Responses API übersetzt.
    """
    graph = await graph_factory()
    
    from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
    
    input_messages = []
    for msg in request.messages:
        if msg.role == "system":
            input_messages.append(SystemMessage(content=msg.content or ""))
        elif msg.role == "user":
            input_messages.append(HumanMessage(content=msg.content or ""))
        elif msg.role == "assistant":
            input_messages.append(AIMessage(content=msg.content or ""))

    # Generiere Run-Identitäten für das Monitoring
    run_id = str(uuid.uuid4())
    graph_id = model_id 

    # Initialer State für den Graph inklusive Monitoring-IDs
    initial_state = {
        "messages": input_messages,
        "run_id": run_id,
        "graph_id": graph_id
    }

    # OpenAI-Metadaten
    stream_id = f"resp-{uuid.uuid4()}"
    created_time = int(time.time())

    async for event in graph.astream_events(initial_state, version="v2"):
        if event["event"] == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            if not chunk:
                continue
            
            content = getattr(chunk, 'content', "")
            reasoning_content = ""
            if hasattr(chunk, 'additional_kwargs'):
                reasoning_content = chunk.additional_kwargs.get("reasoning_content", "")
            if not reasoning_content and hasattr(chunk, 'reasoning_content'):
                reasoning_content = chunk.reasoning_content

            delta = {"content": content}
            if reasoning_content:
                delta["reasoning_content"] = reasoning_content
            
            if hasattr(chunk, 'tool_call_chunks') and chunk.tool_call_chunks:
                delta["tool_calls"] = chunk.tool_call_chunks

            chunk_obj = ResponseChunk(
                id=stream_id,
                object="response.chunk",
                created=created_time,
                model=model_id,
                choices=[ResponseChunkChoice(
                    index=0,
                    delta=delta
                )]
            )
            yield f"data: {chunk_obj.model_dump_json()}\n\n"

    yield "data: [DONE]\n\n"

router = APIRouter()

@router.post("/responses")
async def responses(request: Request):
    """
    OpenAI-kompatibler Responses Endpunkt.
    """
    body = await request.json()
    req = ResponseRequest(**body)
    
    factory = registry.get_model_factory(req.model)
    if not factory:
        return {"error": f"Model {req.model} not found"}

    if req.stream:
        return StreamingResponse(
            responses_generator(req.model, req, factory),
            media_type="text/event-stream"
        )
    else:
        return {"error": "Non-streaming mode not yet implemented for responses. Use stream=True."}
