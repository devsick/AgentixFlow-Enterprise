from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from src.settings.config_store import config_store
from src.tools.mcp_client_interface import MCPClientInterface


class AnkiMCPClient(MCPClientInterface):
    """
    MCP Client for Anki via Streamable HTTP.

    The client keeps its MCP session open during its lifetime.
    Handshake, session ID, protocol headers, and transport are managed 
    by the official MCP Python SDK.
    """

    def __init__(self, allowed_tools: Optional[List[str]] = None):
        super().__init__(allowed_tools=allowed_tools)

        self.server_config = config_store.mcp_server.get("anki-mcp")

        if not self.server_config:
            raise ValueError(
                "Could not find 'anki-mcp' configuration in config_store."
            )

        self.url = self.server_config.url.rstrip("/")
        

    async def _ensure_connected(self) -> None:
        """Opens the transport and initializes the MCP session once."""

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

            # MCP-Handshake; the SDK manages the protocol initialization.
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
        Compatibility method for the previous client setup.

        Supports tools/list and tools/call. The MCP communication itself
        occurs via ClientSession and not through custom-built HTTP POSTs.
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
            result = await self._session.call_tool(
                name=params["name"],
                arguments=params.get("arguments", {})
            )
            return result.content

        raise NotImplementedError(f"Method {method} not implemented.")

    async def close(self) -> None:
        """Closes the session and the ExitStack cleanly."""
        if self._exit_stack:
            await self._exit_stack.aclose()
            self._exit_stack = None
            self._session = None
            self._connected = False
            print("[MCP] Connection closed.", flush=True)
