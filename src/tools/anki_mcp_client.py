
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional

from httpx2 import AsyncClient
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from src.settings.config_store import config_store
from src.tools.mcp_client_interface import MCPClientInterface


class AnkiMCPClient(MCPClientInterface):
    """
    MCP Client for Anki via Streamable HTTP.

    The HTTP client carries the configured authorization headers.
    The MCP SDK manages the handshake and session lifecycle.
    """

    def __init__(self, allowed_tools: Optional[List[str]] = None):
        super().__init__(allowed_tools=allowed_tools)

        self.server_config = config_store.mcp_server.get("anki-mcp")

        if not self.server_config:
            raise ValueError(
                "Could not find 'anki-mcp' configuration in config_store."
            )

        self.server_type = self.server_config.get("type", "http")

        if self.server_type != "http":
            raise ValueError(
                f"Unsupported Anki MCP transport type: {self.server_type}"
            )

        self.url = self.server_config.url.rstrip("/")

        self.headers = dict(
            self.server_config.get("headers") or {}
        )

        if not self.url.startswith("http://"):
            raise ValueError(
                f"Anki MCP requires an internal HTTP URL: {self.url}"
            )

        if not self.headers.get("Authorization"):
            raise ValueError(
                "Missing Authorization header in Anki MCP configuration."
            )

    async def _ensure_connected(self) -> None:
        """Open the HTTP transport and initialize the MCP session."""

        if self._connected and self._session is not None:
            return

        stack = AsyncExitStack()

        try:
            await stack.__aenter__()

            # HTTP client with configured Bearer authorization.
            http_client = await stack.enter_async_context(
                AsyncClient(
                    headers=self.headers,
                    timeout=30.0,
                )
            )

            # Pass the authenticated HTTP client to the MCP transport.
            read_stream, write_stream = await stack.enter_async_context(
                streamable_http_client(
                    self.url,
                    http_client=http_client,
                )
            )

            session = ClientSession(read_stream, write_stream)

            await stack.enter_async_context(session)

            # Initialize MCP handshake.
            await session.initialize()

            self._exit_stack = stack
            self._session = session
            self._connected = True

            print(
                f"[ANKI MCP] Connected successfully: {self.url}",
                flush=True,
            )

        except BaseException as e:
            print(
                f"[ANKI MCP] Connection failed: {type(e).__name__}: {e}",
                flush=True,
            )

            if hasattr(e, "code"):
                print(
                    f"[ANKI MCP] Error code: {e.code}",
                    flush=True,
                )

            if hasattr(e, "data"):
                print(
                    f"[ANKI MCP] Error data: {e.data}",
                    flush=True,
                )

            try:
                await stack.aclose()
            except BaseException as close_error:
                print(
                    f"[ANKI MCP] Cleanup error: {close_error}",
                    flush=True,
                )

            self._exit_stack = None
            self._session = None
            self._connected = False

            raise

    async def _call_mcp_method(
        self,
        method: str,
        params: Dict[str, Any],
    ) -> Any:
        """Execute MCP protocol methods."""

        await self._ensure_connected()

        if self._session is None:
            raise RuntimeError("MCP session was not initialized.")

        if method == "tools/list":
            result = await self._session.list_tools()

            return {
                "tools": [
                    tool.model_dump(
                        by_alias=True,
                        mode="json",
                    )
                    for tool in result.tools
                ]
            }

        if method == "tools/call":
            result = await self._session.call_tool(
                name=params["name"],
                arguments=params.get("arguments", {}),
            )

            return result.content

        raise NotImplementedError(
            f"Method {method} not implemented."
        )

    async def close(self) -> None:
        """Close the MCP session and HTTP transport."""

        if self._exit_stack is not None:
            await self._exit_stack.aclose()

        self._exit_stack = None
        self._session = None
        self._connected = False

        print(
            "[ANKI MCP] Connection closed.",
            flush=True,
        )
