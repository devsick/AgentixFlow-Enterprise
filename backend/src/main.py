from fastapi import FastAPI
from src.api.chat_completions import router as chat_router
from src.api.responses import router as responses_router
from src.api.models import router as models_router

app = FastAPI(
    title="Agents Backend - OpenAI Compatible API",
    description="A LangGraph-based API mimicking OpenAI's chat completions, responses, and models.",
    version="0.1.0"
)

# Registering the routers under the /v1 prefix to match OpenAI API standards
app.include_router(chat_router, prefix="/v1")
app.include_router(responses_router, prefix="/v1")
app.include_router(models_router, prefix="/v1")

@app.get("/")
async def root():
    """
    Root endpoint for health check and basic info.
    """
    return {
        "message": "Agents Backend API is running.",
        "endpoints": [
            "/v1/models",
            "/v1/chat/completions",
            "/v1/responses"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
