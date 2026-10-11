from typing import Any, Dict, Optional, Type

from langchain_core.messages import AIMessageChunk
from langchain_core.outputs import ChatGenerationChunk
from langchain_openai import ChatOpenAI


class ReasoningChatOpenAI(ChatOpenAI):
    """ChatOpenAI, das Reasoning-Felder von oobabooga erhält."""

    def _convert_chunk_to_generation_chunk(
        self,
        chunk: dict,
        default_chunk_class: Type,
        base_generation_info: Optional[Dict],
    ) -> Optional[ChatGenerationChunk]:

        generation_chunk = super()._convert_chunk_to_generation_chunk(
            chunk,
            default_chunk_class,
            base_generation_info,
        )

        if generation_chunk is None:
            return None

        choices = chunk.get("choices", [])
        if not choices and "chunk" in chunk:
            choices = chunk["chunk"].get("choices", [])

        if not choices:
            return generation_chunk

        delta = choices[0].get("delta", {})

        reasoning = (
            delta.get("reasoning_content")
            or delta.get("reasoning")
            or ""
        )

        if reasoning and isinstance(
            generation_chunk.message, AIMessageChunk
        ):
            generation_chunk.message.additional_kwargs[
                "reasoning_content"
            ] = reasoning

        return generation_chunk
