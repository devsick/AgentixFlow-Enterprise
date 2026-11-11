
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set


class MCPClientInterface(ABC):
    """
    Framework-independent interface for MCP clients.

    Provides a common API for:
    - Discovering available MCP tools.
    - Filtering tools using an optional allowlist.
    - Executing MCP tools.
    - Closing the MCP connection.

    Concrete MCP clients are responsible for implementing
    the transport-specific communication.
    """

    def __init__(
        self,
        allowed_tools: Optional[List[str]] = None,
    ):
        """
        Initialize the common MCP client configuration.

        Args:
            allowed_tools:
                None or ["*"] allows all tools.

                A list of tool names restricts discovery and execution
                to those tools.

                An empty list allows no tools.
        """

        self.allowed_tools: Optional[Set[str]] = (
            None
            if allowed_tools is None
            else frozenset(allowed_tools)
        )

        self._exit_stack = None
        self._session = None
        self._connected = False

    # ---------------------------------------------------------
    # Abstract transport implementation
    # ---------------------------------------------------------

    @abstractmethod
    async def _call_mcp_method(
        self,
        method: str,
        params: Dict[str, Any],
    ) -> Any:
        """
        Execute a low-level MCP protocol method.

        Concrete clients must implement this method.

        Supported methods:
            tools/list
            tools/call

        The implementation is responsible for establishing
        the connection when necessary.
        """
        raise NotImplementedError

    # ---------------------------------------------------------
    # Tool discovery
    # ---------------------------------------------------------

    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        Retrieve available tools from the MCP server.

        Applies the configured allowlist automatically.

        Returns:
            A list of MCP tool definitions containing
            name, description and inputSchema.
        """

        result = await self._call_mcp_method(
            method="tools/list",
            params={},
        )

        if isinstance(result, dict):
            tools = result.get("tools", [])
        else:
            raise TypeError(
                "Invalid MCP tools/list response. "
                "Expected a dictionary containing 'tools'."
            )

        if not isinstance(tools, list):
            raise TypeError(
                "Invalid MCP tools/list response. "
                "The 'tools' field must be a list."
            )

        normalized_tools = []

        for tool in tools:
            tool_data = self._normalize_tool_definition(tool)

            if not tool_data:
                continue

            tool_name = tool_data.get("name")

            if not tool_name:
                continue

            if self._is_tool_allowed(tool_name):
                normalized_tools.append(tool_data)

        return normalized_tools

    # ---------------------------------------------------------
    # Tool execution
    # ---------------------------------------------------------

    async def call_tool(
        self,
        name: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Execute an MCP tool directly.

        This method can be used by:
        - Deterministic graph nodes.
        - Dynamically generated StructuredTools.
        - Other agent frameworks.

        Args:
            name:
                Original MCP tool name.

            arguments:
                Arguments passed to the MCP server.

        Returns:
            The result returned by the concrete MCP client.
        """

        if not isinstance(name, str) or not name.strip():
            raise ValueError(
                "MCP tool name must be a non-empty string."
            )

        if not self._is_tool_allowed(name):
            raise PermissionError(
                f"MCP tool '{name}' is not allowed."
            )

        if arguments is None:
            arguments = {}

        if not isinstance(arguments, dict):
            raise TypeError(
                "MCP tool arguments must be a dictionary."
            )

        return await self._call_mcp_method(
            method="tools/call",
            params={
                "name": name,
                "arguments": arguments,
            },
        )

    # ---------------------------------------------------------
    # Allowlist
    # ---------------------------------------------------------

    def _is_tool_allowed(self, name: str) -> bool:
        """
        Check whether a tool is allowed.

        None or ["*"] means all tools are allowed.
        An empty set means no tools are allowed.
        """

        if self.allowed_tools is None:
            return True

        if "*" in self.allowed_tools:
            return True

        return name in self.allowed_tools

    # ---------------------------------------------------------
    # Tool definition normalization
    # ---------------------------------------------------------

    @staticmethod
    def _normalize_tool_definition(
        tool: Any,
    ) -> Optional[Dict[str, Any]]:
        """
        Normalize MCP tool definitions into dictionaries.

        Supports:
        - Dictionaries.
        - Pydantic models.
        - Objects exposing model_dump().
        """

        if isinstance(tool, dict):
            return tool

        if hasattr(tool, "model_dump"):
            result = tool.model_dump(
                by_alias=True,
                mode="json",
            )

            if isinstance(result, dict):
                return result

        if hasattr(tool, "dict"):
            result = tool.dict(
                by_alias=True,
            )

            if isinstance(result, dict):
                return result

        return None

    # ---------------------------------------------------------
    # Connection lifecycle
    # ---------------------------------------------------------

    async def close(self) -> None:
        """
        Close the MCP connection if an AsyncExitStack exists.

        Concrete clients can override this method if they
        require additional cleanup.
        """

        if self._exit_stack is not None:
            await self._exit_stack.aclose()

        self._exit_stack = None
        self._session = None
        self._connected = False
