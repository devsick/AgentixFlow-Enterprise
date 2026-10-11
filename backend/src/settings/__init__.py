# settings module – public API
# Re-export the config model and store so that code like:
#   from src.settings import config_model, config_store
#   from src.settings import mcp_server, llm_profiles
# can be used globally.
#

from src.settings.config_model import ConfigModel
from src.settings.config_store import config_store

mcp_server = config_store.mcp_server
llm_profiles = config_store.llm_profiles

__all__ = [
    "ConfigModel",
    "config_store",
    "mcp_server",
    "llm_profiles",
]
