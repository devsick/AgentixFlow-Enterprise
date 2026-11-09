import asyncio
from typing import Any, Dict, List, Optional, Callable, Awaitable
from src.graphs.pure_chat.graph import create_pure_chat_graph
from src.graphs.profile_management.graph import create_profile_management_graph
from src.graphs.profile_maintenance.graph import create_profile_maintenance_graph

class GraphRegistry:
    """Registriert und verwaltet verfügbare LangGraph-Instanzen als 'Modelle'."""
    
    def __init__(self):
        self._models: Dict[str, Callable[[], Awaitable[Any]]] = {}

    def register_model(self, model_id: str, factory: Callable[[], Awaitable[Any]]):
        """Registriert eine Factory-Funktion, die eine Graph-Instanz erstellt."""
        self._models[model_id] = factory

    def get_model_factory(self, model_id: str) -> Optional[Callable[[], Awaitable[Any]]]:
        """Gibt die Factory-Funktion für das Modell zurück."""
        return self._models.get(model_id)

    def list_models(self) -> List[str]:
        """Listet alle registrierten Modell-IDs auf."""
        return list(self._models.keys())

# Singleton-Instanz für die gesamte App
registry = GraphRegistry()

# --- Registrierung der vorhandenen Graphen ---

async def pure_chat_factory():
    return create_pure_chat_graph()

async def profile_management_factory():
    return create_profile_management_graph()

async def profile_maintenance_factory():
    return create_profile_maintenance_graph()

# Wir registrieren die Graphen hier.
# Da die Registry global ist, wird dies beim Import der API-Module ausgeführt.
registry.register_model("pure-chat", pure_chat_factory)
registry.register_model("profile-management", profile_management_factory)
registry.register_model("profile-maintenance", profile_maintenance_factory)
