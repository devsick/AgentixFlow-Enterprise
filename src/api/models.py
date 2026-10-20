import time
from fastapi import APIRouter
from src.api.registry import registry
from src.api.schemas import ModelListResponse, ModelData

router = APIRouter()

@router.get("/models")
async def list_models():
    """
    Listet alle registrierten Graphen als OpenAI-kompatible Modelle auf.
    """
    model_ids = registry.list_models()
    now = int(time.time())
    
    model_data_list = [
        ModelData(id=mid, created=now)
        for mid in model_ids
    ]
    
    return ModelListResponse(data=model_data_list)
