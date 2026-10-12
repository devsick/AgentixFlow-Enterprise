from typing import Any, Dict, List, Optional, Type

import httpx
from pydantic import Field, create_model
from langchain_core.tools import StructuredTool
from src.settings.config_store import config_store


class NextcloudMCPClient:
    """
    Client for the Nextcloud MCP server.

    Global allowlist:
        Defines the maximum permissions for all agents.

    Agent-specific allowlist:
        Further restricts the tools available to an agent.
    """

    def __init__(self, allowed_tools: List[str]):
        self.server_config = config_store.settings.mcp_server.get(
            "nextcloud-mcp"
        )

        if not self.server_config:
            raise ValueError(
                "Could not find 'nextcloud-mcp' configuration "
                "in config_store."
            )

        self.url = self.server_config.url
        self.allowed_tools = frozenset(allowed_tools)
        self.client = httpx.AsyncClient(base_url=self.url)

    async def _call_mcp_method(
        self,
        method: str,
        params: Dict[str, Any],
    ) -> Any:
        """Executes a JSON-RPC request against the MCP server."""

        # Enforce global permissions for every tool execution.
        if method == "tools/call":
            tool_name = params.get("name")

            if tool_name not in self.allowed_tools:
                raise PermissionError(
                    f"Tool '{tool_name}' is not globally allowed."
                )

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params,
        }

        try:
            response = await self.client.post("", json=payload)
            response.raise_for_status()
            result = response.json()

            if "error" in result:
                raise RuntimeError(f"MCP error: {result['error']}")

            return result.get("result")

        except Exception as exc:
            raise RuntimeError(
                f"Failed to call MCP method {method}: {exc}"
            ) from exc

    async def list_tools(self) -> List[Dict[str, Any]]:
        """Returns the tools advertised by the MCP server."""

        result = await self._call_mcp_method("tools/list", {})

        if isinstance(result, dict):
            result = result.get("tools", [])

        if not isinstance(result, list):
            raise RuntimeError(
                "Unexpected response from MCP tools/list."
            )

        return result

    @staticmethod
    def _build_args_schema(
        tool_name: str,
        input_schema: Optional[Dict[str, Any]],
    ) -> Type:
        """
        Creates a Pydantic input schema from an MCP JSON schema.

        Supports common JSON Schema primitive types and basic
        object/array arguments.
        """

        schema = input_schema or {}
        properties = schema.get("properties", {})
        required = set(schema.get("required", []))

        type_mapping = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
            "object": dict,
            "array": list,
        }

        fields = {}

        for field_name, definition in properties.items():
            json_type = definition.get("type", "string")
            python_type = type_mapping.get(json_type, Any)

            description = definition.get("description", "")

            if field_name in required:
                default = ...
            else:
                python_type = Optional[python_type]
                default = definition.get("default", None)

            fields[field_name] = (
                python_type,
                Field(default, description=description),
            )

        model_name = "".join(
            part.title() for part in tool_name.split("_")
        ) + "Input"

        return create_model(model_name, **fields)

    async def get_tools(
        self,
        allowed_names: List[str],
    ) -> List[StructuredTool]:
        """
        Returns only tools allowed globally and for the agent.
        """

        requested_tools = set(allowed_names)
        effective_tools = self.allowed_tools.intersection(
            requested_tools
        )

        all_tools = await self.list_tools()
        langchain_tools = []

        for tool_def in all_tools:
            name = tool_def.get("name")

            if name not in effective_tools:
                continue

            description = tool_def.get("description", "")
            input_schema = tool_def.get("inputSchema", {})

            args_schema = self._build_args_schema(
                name,
                input_schema,
            )

            async def tool_wrapper(
                tool_name=name,
                **kwargs,
            ):
                # Defense in depth.
                if tool_name not in effective_tools:
                    raise PermissionError(
                        f"Tool '{tool_name}' is not allowed "
                        "for this agent."
                    )

                return await self._call_mcp_method(
                    "tools/call",
                    {
                        "name": tool_name,
                        "arguments": kwargs,
                    },
                )

            langchain_tools.append(
                StructuredTool.from_function(
                    coroutine=tool_wrapper,
                    name=name,
                    description=description,
                    args_schema=args_schema,
                )
            )

        return langchain_tools

    async def close(self):
        """Closes the underlying HTTP client."""
        await self.client.aclose()
