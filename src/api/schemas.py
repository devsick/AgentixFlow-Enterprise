from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime

# --- Request Schemas ---

class ChatMessage(BaseModel):
    role: str  # user, assistant, system, tool, function
    content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    function_call: Optional[Dict[str, Any]] = None

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    api_key: Optional[str] = None
    stream: Optional[bool] = False
    temperature: Optional[float] = 1.0
    top_p: Optional[float] = 1.0
    n: Optional[int] = 1
    max_tokens: Optional[int] = None
    presence_penalty: Optional[float] = 0.0
    frequency_penalty: Optional[float] = 0.0
    stop: Optional[Union[str, List[str]]] = None
    response_format: Optional[Dict[str, Any]] = None

# --- Response Schemas ---

class ChatCompletionChoice(BaseModel):
    index: int
    message: Optional[ChatMessage] = None
    logprobs: Optional[Dict[str, Any]] = None
    finish_reason: Optional[str] = None

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: Optional[Dict[str, Any]] = None

class ChatCompletionChunkChoice(BaseModel):
    index: int
    delta: Dict[str, Any]  # Contains content, reasoning_content, tool_calls, etc.
    logprobs: Optional[Dict[str, Any]] = None
    finish_reason: Optional[str] = None

class ChatCompletionChunk(BaseModel):
    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: List[ChatCompletionChunkChoice]

class ChatCompletionUsage(BaseModel):
    object: str = "chat.completion.usage"
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

# --- NEW: Responses API Schemas (OpenAI Migration Standard) ---

class ResponseMessage(BaseModel):
    role: str
    content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None

class ResponseRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    api_key: Optional[str] = None
    stream: Optional[bool] = False
    # Conversations können über eine ID gesteuert werden (für zukünftiges State-Management)
    conversation_id: Optional[str] = None 

class ResponseChoice(BaseModel):
    index: int
    message: Optional[ResponseMessage] = None
    finish_reason: Optional[str] = None

class ResponseResponse(BaseModel):
    id: str
    object: str = "response"
    created: int
    model: str
    choices: List[ResponseChoice]

class ResponseChunkChoice(BaseModel):
    index: int
    delta: Dict[str, Any]
    finish_reason: Optional[str] = None

class ResponseChunk(BaseModel):
    id: str
    object: str = "response.chunk"
    created: int
    model: str
    choices: List[ResponseChunkChoice]

# --- Model Schemas ---

class ModelData(BaseModel):
    id: str
    object: str = "model"
    created: int
    owned_by: str = "agents-backend"

class ModelListResponse(BaseModel):
    object: str = "list"
    data: List[ModelData]
