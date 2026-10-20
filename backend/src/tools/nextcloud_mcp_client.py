
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional, Type

from pydantic import Field, create_model
from langchain_core.tools import StructuredTool

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from src.settings.config_store import config_store


class NextcloudMCPClient:
    """
    MCP-Client für Nextcloud über Streamable HTTP.

    Der Client hält seine MCP-Session während seiner Lebensdauer offen.
    Handshake, Session-ID, Protokollheader und Transport werden vom
    offiziellen MCP-Python-SDK verwaltet.
    """

    def __init__(self, allowed_tools: List[str]):
        self.server_config = config_store.mcp_server.get("nextcloud-mcp")

        if not self.server_config:
            raise ValueError(
                "Could not find 'nextcloud-mcp' configuration in config_store."
            )

        self.url = self.server_config.url.rstrip("/")
        self.allowed_tools = frozenset(allowed_tools)

        self._exit_stack: Optional[AsyncExitStack] = None
        self._session: Optional[ClientSession] = None
        self._connected = False

    async def _ensure_connected(self) -> None:
        """Öffnet den Transport und initialisiert die MCP-Session einmalig."""

        if self._connected and self._session is not None:
            return

        stack = AsyncExitStack()

        try:
            await stack.__aenter__()

            read_stream, write_stream = await stack.enter_async_context(
                streamable_http_client(self.url)
            )

            session = ClientSession(read_stream, write_stream)
            await stack.enter_async_context(session)

            # MCP-Handshake; das SDK verwaltet die Protokollinitialisierung.
            await session.initialize()

            self._exit_stack = stack
            self._session = session
            self._connected = True

            print(
                f"[MCP] Connected to {self.url}",
                flush=True,
            )

        except Exception:
            await stack.aclose()
            self._exit_stack = None
            self._session = None
            self._connected = False
            raise

    async def _call_mcp_method(
        self,
        method: str,
        params: Dict[str, Any],
    ) -> Any:
        """
        Kompatibilitätsmethode für den bisherigen Client-Aufbau.

        Unterstützt tools/list und tools/call. Die MCP-Kommunikation selbst
        erfolgt über ClientSession und nicht über selbst gebaute HTTP-POSTs.
        """

        await self._ensure_connected()

        if self._session is None:
            raise RuntimeError("MCP session was not initialized.")

        if method == "tools/list":
            result = await self._session.list_tools()

            return {
                "tools": [
                    tool.model_dump(by_alias=True, mode="json")
                    for tool in result.tools
                ]
            }

        if method == "tools/call":
            tool_name = params.get("name")

            if not isinstance(tool_name, str):
                raise ValueError("Missing MCP tool name.")

            if tool_name not in self.allowed_tools:
                raise PermissionError(
                    f"MCP tool '{tool_name}' is not allowed."
                )

            arguments = params.get("arguments") or {}

            result = await self._session.call_tool(
                tool_name,
                arguments=arguments,
            )

            return result.model_dump(by_alias=True, mode="json")

        raise NotImplementedError(
            f"Unsupported MCP method: {method}"
        )

    async def list_tools(self) -> List[Dict[str, Any]]:
        """Liefert die vom MCP-Server veröffentlichten Tools."""

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
        input_schema: Dict[str, Any],
    ) -> Type:
        """Erzeugt ein Pydantic-Argumentschema aus dem MCP-JSON-Schema."""

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

        model_name = (
            "".join(part.title() for part in tool_name.split("_"))
            + "Input"
        )

        return create_model(model_name, **fields)

    async def get_tools(
        self,
        allowed_names: List[str],
    ) -> List[StructuredTool]:
        """
        Erstellt LangChain-Tools aus den erlaubten MCP-Tools.

        Es gelten beide Filter:
        - allowed_tools aus dem Konstruktor
        - allowed_names aus dem aktuellen Aufruf
        """

        requested_tools = set(allowed_names)
        effective_tools = self.allowed_tools.intersection(requested_tools)

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
                **kwargs: Any,
            ) -> Any:
                if tool_name not in effective_tools:
                    raise PermissionError(
                        f"MCP tool '{tool_name}' is not allowed."
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

    async def close(self) -> None:
        """Schließt die MCP-Session und den zugehörigen Transport."""

        if self._exit_stack is not None:
            await self._exit_stack.aclose()

        self._exit_stack = None
        self._session = None
        self._connected = False
