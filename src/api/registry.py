
from typing import Any, Dict, List, Optional, Callable, Awaitable

from src.graphs.pure_chat.graph import create_pure_chat_graph
from src.graphs.profile_management.graph import create_profile_management_graph
from src.graphs.profile_maintenance.graph import create_profile_maintenance_graph
from src.graphs.anki.graph import create_anki_graph


class GraphRegistry:
    """Registers and manages available LangGraph instances as 'models'."""

    def __init__(self):
        self._models: Dict[str, Callable[[], Awaitable[Any]]] = {}

    def register_model(
        self,
        model_id: str,
        factory: Callable[[], Awaitable[Any]],
    ):
        """Registers a factory function that creates a graph instance."""
        self._models[model_id] = factory

    def get_model_factory(
        self,
        model_id: str,
    ) -> Optional[Callable[[], Awaitable[Any]]]:
        """Returns the factory function for the model."""
        return self._models.get(model_id)

    def list_models(self) -> List[str]:
        """Lists all registered model IDs."""
        return list(self._models.keys())


# Singleton instance for the entire app
registry = GraphRegistry()


# --------------------------------------------------
# Graph Factories
# --------------------------------------------------

async def pure_chat_factory():
    return create_pure_chat_graph()


async def profile_management_factory():
    return create_profile_management_graph()


async def profile_maintenance_factory():
    return create_profile_maintenance_graph()


async def anki_factory():
    return create_anki_graph()


# --------------------------------------------------
# Model Registration
# --------------------------------------------------

registry.register_model("pure-chat", pure_chat_factory)
registry.register_model("profile-management", profile_management_factory)
registry.register_model("profile-maintenance", profile_maintenance_factory)
registry.register_model("anki", anki_factory)
