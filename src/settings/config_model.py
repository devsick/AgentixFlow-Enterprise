
from typing import Optional, Any, Dict
from pydantic import BaseModel, Field


class McpServerConfig(BaseModel):
    """Configuration for a single MCP server instance."""

    type: str = Field(
        ...,
        description="Server type, e.g. 'http'"
    )

    url: str = Field(
        ...,
        description="Server URL endpoint"
    )

    headers: Dict[str, str] = Field(
        default_factory=dict,
        description="Optional HTTP headers for MCP authentication"
    )

    def __repr__(self) -> str:
        return (
            f"McpServerConfig("
            f"type={self.type}, "
            f"url={self.url}, "
            f"headers={'configured' if self.headers else 'none'}"
            f")"
        )


class LlmProfileConfig(BaseModel):
    """Configuration for a single LLM profile."""

    type: str = Field(..., description="LLM type, e.g. 'reasoning'")
    name: str = Field(..., description="Profile name")
    url: str = Field(..., description="LLM server URL")
    model: str = Field(..., description="Model identifier")

    extra_body: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional parameters for the LLM provider"
    )

    def __repr__(self) -> str:
        return (
            f"LlmProfileConfig("
            f"type={self.type}, "
            f"name={self.name}, "
            f"url={self.url}, "
            f"model={self.model}, "
            f"extra_body={self.extra_body}"
            f")"
        )


class ConfigModel(BaseModel):
    """Top-level settings configuration model."""

    class Settings(BaseModel):
        mcp_servers: dict[str, McpServerConfig] = Field(
            ...,
            description="Dictionary of MCP server configurations"
        )

        llm_profiles: dict[str, LlmProfileConfig] = Field(
            ...,
            description="Dictionary of LLM profile configurations"
        )

        @property
        def mcp_server(self) -> dict[str, McpServerConfig]:
            return self.mcp_servers

    settings: Settings = Field(..., description="Top-level settings")

    def __repr__(self) -> str:
        return f"ConfigModel(settings={self.settings})"
