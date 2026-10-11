import json
import time
import uuid
from typing import AsyncGenerator
from src.api.registry import registry
from src.api.schemas import (
    ChatCompletionRequest,
    ChatCompletionChunk,
    ChatCompletionChunkChoice
)

async def stream_translator(
    model_id: str, 
    request: ChatCompletionRequest,
    graph_factory: any
) -> AsyncGenerator[str, None]:
    """
    Übersetzt LangGraph-Events in OpenAI-konforme SSE-Chunks.
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

    initial_state = {"messages": input_messages}
    stream_id = f"chatcmpl-{uuid.uuid4()}"
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

            chunk_obj = ChatCompletionChunk(
                id=stream_id,
                object="chat.completion.chunk",
                created=created_time,
                model=model_id,
                choices=[ChatCompletionChunkChoice(index=0, delta=delta)]
            )
            yield f"data: {chunk_obj.model_dump_json()}\n\n"

    yield "data: [DONE]\n\n"
