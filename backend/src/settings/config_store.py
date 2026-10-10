"""
config_store.py – Configuration store that loads from config.json.

Loads the settings from:
    /app/server/storage/anythingllm-fs/repos/agents/backend/src/config/config.json

Provides access to the loaded configuration via:
    - config_store.mcp_server: dictionary of MCP server configs
    - config_store.llm_profiles: dictionary of LLM profile configs
    - config_store.settings: the full ConfigModel instance

Usage example (inside or after import):
    from agents.backend.src.settings.config_store import config_store

    # Access individual values:
    print(config_store.mcp_server["nextcloud-mcp"].url)
    print(config_store.llm_profiles["oogabooga"].model)

    # Access full settings:
    print(config_store.settings.mcp_server)
    print(config_store.settings.llm_profiles)
"""

import json
from pathlib import Path
from typing import Any

# Path to the config file
CONFIG_FILE = Path(
    "/app/server/storage/anythingllm-fs/repos/agents/backend/src/config/config.json"
)


def load_config() -> dict[str, Any]:
    """Load the configuration from config.json."""
    with CONFIG_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


# Load the configuration at module level
_config_data: dict[str, Any] = load_config()


class ConfigStore:
    """Configuration store that exposes config values as attributes.

    Usage:
        from agents.backend.src.settings.config_store import config_store

        # Access all values:
        print(config_store.mcp_server)       # dict with MCP server configs
        print(config_store.llm_profiles)     # dict with LLM profiles
        print(config_store.settings)         # full ConfigModel with settings

        # Access specific values:
        print(config_store.mcp_server["nextcloud-mcp"].url)
        print(config_store.llm_profiles["oogabooga"].url)
    """

    @property
    def settings(self) -> Any:
        """Returns a dictionary-like object for the full settings."""
        return ConfigDictWrapper(self._settings_dict)

    @property
    def mcp_server(self) -> Any:
        """Returns a dictionary-like object with MCP server configs."""
        return ConfigDictWrapper(self._settings_dict["mcp_servers"])

    @property
    def llm_profiles(self) -> Any:
        """Returns a dictionary-like object with LLM profile configs."""
        return ConfigDictWrapper(self._settings_dict["llm_profiles"])

    def __init__(self) -> None:
        """Initialize the config store by loading the JSON data."""
        self._data = load_config()
        self._settings_dict = self._data

    def __getitem__(self, key: str) -> Any:
        """Allow dictionary-style access."""
        return self._data[key]

    def __repr__(self) -> str:
        return f"ConfigStore({self._data})"


class ConfigDictWrapper:
    """Wrapper that provides dictionary access and attribute access for config values."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __repr__(self) -> str:
        return f"ConfigDictWrapper({self._data})"


# Create the global config_store instance
config_store = ConfigStore()