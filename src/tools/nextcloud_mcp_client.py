from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional, Type

from pydantic import Field, create_model
from langchain_core.tools import StructuredTool

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from src.settings.config_store import config_store


class NextcloudMCPClient:
    """
    MCP Client for Nextcloud via Streamable HTTP.

    The client keeps its MCP session open during its lifetime.
    Handshake, session ID, protocol headers, and transport are managed 
    by the official MCP Python SDK.
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
