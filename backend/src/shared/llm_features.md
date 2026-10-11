# LLM Features: Reasoning and Token Usage

To enable advanced features like reasoning (thoughts) and detailed token usage in LLM agents, follow these patterns when initializing your `LLMClass`.

## 1. Enabling Reasoning (Thoughts)

To receive the reasoning/thought process from models (like oobabooga/Gemma 4), the agent must use the `ReasoningChatOpenAI` class and pass the appropriate `extra_body` parameters via the configuration profile.

### Implementation Pattern

In your agent's `__init__` method, determine the class and parameters based on the profile type:

```python
# 1. Determine the class based on profile type
if profile.type == "reasoning":
    LLMClass = ReasoningChatOpenAI
else:
    LLMClass = ChatOpenAI

# 2. Initialize with extra_body from config
self.llm = LLMClass(
    base_url=profile.url,
    model=profile.model,
    api_key=effective_api_key,
    # ... other params
    extra_body=profile.extra_body  # This must contain {'enable_thinking': True, ...}
)
```

### Required Configuration (`config.json`)

Ensure your profile in `src/config/config.json` includes the `extra_body` field:

```json
"oogabooga": {
    "type": "reasoning",
    "url": "http://oogabooga:5000/v1",
    "model": "gemma-4-26B-A4B-it-UD-Q3_K_XL.gguf",
    "extra_body": {
        "enable_thinking": true,
        "reasoning_effort": "high"
    }
}
```

## 2. Enabling Token Usage Tracking

To enable the `usage_metadata` field in the LLM response (which includes `input_tokens`, `output_tokens`, and `total_tokens`), set `stream_usage=True` during initialization.

### Implementation Pattern

```python
self.llm = LLMClass(
    # ... other params
    streaming=True,
    stream_usage=True,  # <--- This enables token usage tracking
    # ...
)
```

By combining these two patterns, you get full visibility into both the model's reasoning process and its resource consumption.
