# settings module – public API
# Re-export the config model and store so that code like:
#   from agents.backend.src.settings import config_model, config_store
#   from agents.backend.src.settings import mcp_server, llm_profiles
# can be used globally.

from agents.backend.src.settings.config_model import ConfigModel
from agents.backend.src.settings.config_store import config_store
from agents.backend.src.settings.config_store import mcp_server
from agents.backend.src.settings.config_store import llm_profiles

__all__ = [
    "ConfigModel",
    "config_store",
    "mcp_server",
    "llm_profiles",
]