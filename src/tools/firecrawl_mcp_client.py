from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from src.settings.config_store import config_store


class FirecrawlMCPClient:
    """
    MCP-Client für Firecrawl über Streamable HTTP.

    Der Client hält seine MCP-Session während seiner Lebensdauer offen.
    Handshake, Session-ID, Protokollheader und Transport werden vom
    offiziellen MCP-Python-SDK verwaltet.
    """

    def __init__(self, allowed_tools: List[str]):
        self.server_config = config_store.mcp_server.get("firecrawl")

        if not self.server_config:
            raise ValueError(
                "Could not find 'firecrawl' configuration in config_store."
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
        
        # Placeholder for other methods (tools/call, etc.)
        raise NotImplementedError(f"Method {method} not implemented.")

    async def close(self) -> None:
        """Schließt die Session und den ExitStack sauber."""
        if self._exit_stack:
            await self._exit_stack.aclose()
            self._exit_stack = None
            self._session = None
            self._connected = False
            print("[MCP] Connection closed.", flush=True)
