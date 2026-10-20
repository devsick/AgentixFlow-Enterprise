
from typing import Any, AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.api.registry import registry
from src.api.schemas import ChatCompletionRequest
from src.api.streaming_translator import stream_translator

router = APIRouter()


@router.post("/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """
    OpenAI-kompatibler Chat-Completions-Endpunkt.
    Erzeugt den passenden Graphen und delegiert das Streaming
    an den Streaming-Translator.
    """

    async def graph_factory():
        factory = registry.get_model_factory(request.model)

        if factory is None:
            raise ValueError(
                f"No model factory registered for: {request.model}"
            )

        return await factory()

    return StreamingResponse(
        stream_translator(
            request.model,
            request,
            graph_factory,
        ),
        media_type="text/event-stream",
    )


async def stream_generator(
    model_id: str,
    request: ChatCompletionRequest,
    graph_factory: Any,
) -> AsyncGenerator[str, None]:
    """
    Wrapper für interne Aufrufe des Streaming-Translators.
    """
    async for chunk in stream_translator(
        model_id,
        request,
        graph_factory,
    ):
        yield chunk
