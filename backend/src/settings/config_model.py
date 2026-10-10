"""
config_model.py – Data models for the settings configuration.

Provides Pydantic models that represent the structure of the
settings configuration stored in /app/server/storage/anythingllm-fs/repos/agents/backend/src/config/config.json.
"""

from pydantic import BaseModel, Field


class McpServerConfig(BaseModel):
    """Configuration for a single MCP server instance."""

    type: str = Field(..., description="Server type, e.g. 'http'")
    url: str = Field(..., description="Server URL endpoint")

    def __repr__(self) -> str:
        return f"McpServerConfig(type={self.type}, url={self.url})"


class LlmProfileConfig(BaseModel):
    """Configuration for a single LLM profile."""

    type: str = Field(..., description="LLM type, e.g. 'reasoning'")
    name: str = Field(..., description="Profile name")
    url: str = Field(..., description="LLM server URL")
    model: str = Field(..., description="Model identifier")

    def __repr__(self) -> str:
        return f"LlmProfileConfig(type={self.type}, name={self.name}, url={self.url}, model={self.model})"


class ConfigModel(BaseModel):
    """Top-level settings configuration model.

    Mirrors the structure found in:
        /app/server/storage/anythingllm-fs/repos/agents/backend/src/config/config.json
    """

    class Settings(BaseModel):
        mcp_servers: dict[str, McpServerConfig] = Field(
            ..., description="Dictionary of MCP server configurations"
        )
        llm_profiles: dict[str, LlmProfileConfig] = Field(
            ..., description="Dictionary of LLM profile configurations"
        )

        @property
        def mcp_server(self) -> dict[str, McpServerConfig]:
            """Shortcut access to the MCP servers dictionary."""
            return self.mcp_servers

        @property
        def llm_profiles(self) -> dict[str, LlmProfileConfig]:
            """Shortcut access to the LLM profiles dictionary."""
            return self.llm_profiles

    settings: Settings = Field(..., description="Top-level settings")

    def __repr__(self) -> str:
        return f"ConfigModel(settings={self.settings})"