
import json
import re
from enum import Enum
from typing import (
    Any,
    Dict,
    List,
    Mapping,
    Optional,
    Type,
    Union,
)

from pydantic import BaseModel, ConfigDict, Field, create_model
from langchain_core.tools import StructuredTool


class MCPToolFactory:
    """
    Dynamically creates LangChain StructuredTools from MCP tool definitions.

    The factory:
    - Discovers tools through the MCP client interface.
    - Converts MCP JSON Schemas into Pydantic models.
    - Creates StructuredTool instances dynamically.
    - Routes execution directly to the corresponding MCP client.
    - Does not contain server-specific or tool-specific implementations.

    Expected MCP client interface:

        async def list_tools(self) -> List[Dict[str, Any]]

        async def call_tool(
            self,
            name: str,
            arguments: Optional[Dict[str, Any]] = None,
        ) -> Any
    """

    def __init__(self, prefix_tool_names: bool = True):
        self.prefix_tool_names = prefix_tool_names

    # ---------------------------------------------------------
    # Public API
    # ---------------------------------------------------------

    async def create_tools(
        self,
        clients: Mapping[str, Any],
    ) -> List[StructuredTool]:
        """
        Discover tools from multiple MCP clients and create
        a combined list of StructuredTools.

        Example:

            tools = await factory.create_tools({
                "anki": anki_client,
                "firecrawl": firecrawl_client,
                "nextcloud": nextcloud_client,
            })
        """

        structured_tools: List[StructuredTool] = []

        for client_alias, client in clients.items():
            mcp_tools = await client.list_tools()

            for mcp_tool in mcp_tools:
                remote_name = mcp_tool.get("name")

                if not remote_name:
                    continue

                input_schema = (
                    mcp_tool.get("inputSchema")
                    or mcp_tool.get("input_schema")
                    or {"type": "object", "properties": {}}
                )

                if not isinstance(input_schema, dict):
                    raise ValueError(
                        f"Invalid input schema for MCP tool '{remote_name}'."
                    )

                tool_name = self._build_tool_name(
                    client_alias=client_alias,
                    remote_name=remote_name,
                )

                args_schema = self._create_args_schema(
                    tool_name=tool_name,
                    schema=input_schema,
                )

                description = mcp_tool.get("description") or (
                    f"MCP tool '{remote_name}' from server '{client_alias}'."
                )

                description = (
                    f"{description}\n\n"
                    f"MCP server: {client_alias}\n"
                    f"Original MCP tool name: {remote_name}"
                )

                executor = self._create_executor(
                    client=client,
                    remote_name=remote_name,
                )

                structured_tool = StructuredTool.from_function(
                    coroutine=executor,
                    name=tool_name,
                    description=description,
                    args_schema=args_schema,
                    infer_schema=False,
                )

                structured_tools.append(structured_tool)

        return structured_tools

    # ---------------------------------------------------------
    # Tool naming
    # ---------------------------------------------------------

    def _build_tool_name(
        self,
        client_alias: str,
        remote_name: str,
    ) -> str:
        """
        Build a unique LangChain tool name.

        Prefixing avoids collisions when different MCP servers
        expose tools with identical names.
        """

        if self.prefix_tool_names:
            name = f"{client_alias}_{remote_name}"
        else:
            name = remote_name

        name = re.sub(r"[^a-zA-Z0-9_-]", "_", name)

        return name

    # ---------------------------------------------------------
    # MCP execution
    # ---------------------------------------------------------

    def _create_executor(
        self,
        client: Any,
        remote_name: str,
    ):
        """
        Create an asynchronous executor for one discovered MCP tool.

        This is generated automatically. No manual tool wrapper
        needs to be implemented.
        """

        async def execute(**arguments: Any) -> str:
            result = await client.call_tool(
                name=remote_name,
                arguments=arguments,
            )

            return self._normalize_result(result)

        return execute

    # ---------------------------------------------------------
    # MCP result normalization
    # ---------------------------------------------------------

    @staticmethod
    def _normalize_result(result: Any) -> str:
        """
        Convert MCP results into a representation suitable
        for LangChain tool messages.
        """

        if result is None:
            return ""

        if isinstance(result, str):
            return result

        # Support clients that return the complete MCP result.
        if hasattr(result, "isError") and result.isError:
            raise RuntimeError(
                f"MCP tool execution failed: {result}"
            )

        if hasattr(result, "content"):
            result = result.content

        if isinstance(result, str):
            return result

        if isinstance(result, list):
            text_parts = []

            for item in result:
                if isinstance(item, str):
                    text_parts.append(item)
                    continue

                text = getattr(item, "text", None)

                if text is not None:
                    text_parts.append(text)
                    continue

                if hasattr(item, "model_dump"):
                    text_parts.append(
                        json.dumps(
                            item.model_dump(mode="json"),
                            ensure_ascii=False,
                            default=str,
                        )
                    )
                    continue

                text_parts.append(str(item))

            return "\n".join(text_parts)

        if isinstance(result, dict):
            return json.dumps(
                result,
                ensure_ascii=False,
                default=str,
            )

        if hasattr(result, "model_dump"):
            return json.dumps(
                result.model_dump(mode="json"),
                ensure_ascii=False,
                default=str,
            )

        return str(result)

    # ---------------------------------------------------------
    # JSON Schema -> Pydantic
    # ---------------------------------------------------------

    def _create_args_schema(
        self,
        tool_name: str,
        schema: Dict[str, Any],
    ) -> Type[BaseModel]:
        """
        Convert an MCP JSON Schema into a dynamic Pydantic model.
        """

        model_name = self._to_class_name(tool_name)

        return self._schema_to_model(
            model_name=model_name,
            schema=schema,
            root_schema=schema,
            ref_stack=set(),
        )

    def _schema_to_model(
        self,
        model_name: str,
        schema: Dict[str, Any],
        root_schema: Dict[str, Any],
        ref_stack: set,
    ) -> Type[BaseModel]:
        properties = schema.get("properties", {})
        required = set(schema.get("required", []))

        fields = {}

        for field_name, field_schema in properties.items():
            if not isinstance(field_schema, dict):
                field_schema = {}

            annotation = self._schema_to_type(
                schema=field_schema,
                model_name=f"{model_name}_{field_name}",
                root_schema=root_schema,
                ref_stack=ref_stack,
            )

            default = field_schema.get("default", ...)

            if field_name not in required and default is ...:
                default = None

                if not self._allows_none(annotation):
                    annotation = Optional[annotation]

            field_kwargs = {}

            if "description" in field_schema:
                field_kwargs["description"] = field_schema["description"]

            if "title" in field_schema:
                field_kwargs["title"] = field_schema["title"]

            self._add_field_constraints(
                field_kwargs,
                field_schema,
            )

            fields[field_name] = (
                annotation,
                Field(default, **field_kwargs),
            )

        additional_properties = schema.get(
            "additionalProperties",
            True,
        )

        extra_behavior = (
            "forbid"
            if additional_properties is False
            else "allow"
        )

        config = ConfigDict(extra=extra_behavior)

        return create_model(
            self._to_class_name(model_name),
            __config__=config,
            **fields,
        )

    def _schema_to_type(
        self,
        schema: Dict[str, Any],
        model_name: str,
        root_schema: Dict[str, Any],
        ref_stack: set,
    ) -> Any:
        """
        Convert JSON Schema types recursively.

        Supports:
        - string, integer, number, boolean, null
        - objects and nested objects
        - arrays
        - enums and const
        - anyOf and oneOf
        - allOf for object schemas
        - nullable fields
        - local $ref references
        """

        if not isinstance(schema, dict):
            return Any

        # Resolve local JSON Schema references.
        if "$ref" in schema:
            ref = schema["$ref"]

            if ref in ref_stack:
                # Prevent infinite recursion for recursive schemas.
                return Dict[str, Any]

            resolved = self._resolve_ref(
                ref=ref,
                root_schema=root_schema,
            )

            if resolved is None:
                return Any

            return self._schema_to_type(
                schema=resolved,
                model_name=model_name,
                root_schema=root_schema,
                ref_stack=ref_stack | {ref},
            )

        # Const values.
        if "const" in schema:
            return self._literal_type([schema["const"]])

        # Enum values.
        if "enum" in schema:
            return self._enum_type(
                values=schema["enum"],
                model_name=model_name,
            )

        # anyOf / oneOf.
        for composition in ("anyOf", "oneOf"):
            if composition in schema:
                branches = schema[composition]

                branch_types = []

                for index, branch in enumerate(branches):
                    branch_type = self._schema_to_type(
                        schema=branch,
                        model_name=f"{model_name}_option_{index}",
                        root_schema=root_schema,
                        ref_stack=ref_stack,
                    )

                    if branch_type not in branch_types:
                        branch_types.append(branch_type)

                if type(None) in branch_types:
                    non_null = [
                        item for item in branch_types
                        if item is not type(None)
                    ]

                    if len(non_null) == 1:
                        return Optional[non_null[0]]

                if len(branch_types) == 1:
                    return branch_types[0]

                return Union[tuple(branch_types)]

        # allOf: merge object properties and required fields.
        if "allOf" in schema:
            merged = self._merge_all_of(
                schema=schema,
                root_schema=root_schema,
                ref_stack=ref_stack,
            )

            return self._schema_to_type(
                schema=merged,
                model_name=model_name,
                root_schema=root_schema,
                ref_stack=ref_stack,
            )

        schema_type = schema.get("type")

        # JSON Schema may specify multiple types.
        if isinstance(schema_type, list):
            types = []

            for item in schema_type:
                item_schema = dict(schema)
                item_schema["type"] = item

                converted = self._schema_to_type(
                    schema=item_schema,
                    model_name=model_name,
                    root_schema=root_schema,
                    ref_stack=ref_stack,
                )

                if converted not in types:
                    types.append(converted)

            if type(None) in types:
                non_null = [
                    item for item in types
                    if item is not type(None)
                ]

                if len(non_null) == 1:
                    return Optional[non_null[0]]

            return Union[tuple(types)]

        # Object.
        if schema_type == "object" or "properties" in schema:
            if not schema.get("properties"):
                return Dict[str, Any]

            return self._schema_to_model(
                model_name=model_name,
                schema=schema,
                root_schema=root_schema,
                ref_stack=ref_stack,
            )

        # Array.
        if schema_type == "array":
            item_schema = schema.get("items", {})

            item_type = self._schema_to_type(
                schema=item_schema,
                model_name=f"{model_name}_item",
                root_schema=root_schema,
                ref_stack=ref_stack,
            )

            return List[item_type]

        # Primitive types.
        primitive_types = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
            "null": type(None),
        }

        return primitive_types.get(schema_type, Any)

    # ---------------------------------------------------------
    # JSON Schema helpers
    # ---------------------------------------------------------

    @staticmethod
    def _resolve_ref(
        ref: str,
        root_schema: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Resolve local JSON Schema references such as:

            #/$defs/Address
            #/definitions/Person
        """

        if not ref.startswith("#/"):
            return None

        current: Any = root_schema

        path = ref[2:].split("/")

        for part in path:
            part = part.replace("~1", "/").replace("~0", "~")

            if not isinstance(current, dict):
                return None

            current = current.get(part)

            if current is None:
                return None

        return current if isinstance(current, dict) else None

    def _merge_all_of(
        self,
        schema: Dict[str, Any],
        root_schema: Dict[str, Any],
        ref_stack: set,
    ) -> Dict[str, Any]:
        """
        Merge common object-style allOf definitions.
        """

        merged = {
            key: value
            for key, value in schema.items()
            if key != "allOf"
        }

        properties = dict(merged.get("properties", {}))
        required = set(merged.get("required", []))

        for index, branch in enumerate(schema["allOf"]):
            if "$ref" in branch:
                branch = self._resolve_ref(
                    branch["$ref"],
                    root_schema,
                ) or {}

            if "allOf" in branch:
                branch = self._merge_all_of(
                    branch,
                    root_schema,
                    ref_stack,
                )

            properties.update(branch.get("properties", {}))
            required.update(branch.get("required", []))

        merged["properties"] = properties
        merged["required"] = list(required)
        merged["type"] = "object"

        return merged

    @staticmethod
    def _enum_type(
        values: List[Any],
        model_name: str,
    ) -> Any:
        """
        Build a Python Enum from JSON Schema enum values.
        """

        if not values:
            return Any

        members = {
            f"VALUE_{index}": value
            for index, value in enumerate(values)
        }

        return Enum(
            MCPToolFactory._to_class_name(model_name),
            members,
        )

    @staticmethod
    def _literal_type(values: List[Any]) -> Any:
        """
        Build a typing.Literal dynamically.
        """

        from typing import Literal

        if len(values) == 1:
            return Literal[values[0]]

        return Literal[tuple(values)]

    @staticmethod
    def _allows_none(annotation: Any) -> bool:
        """
        Check whether a type annotation already allows None.
        """

        from typing import get_args, get_origin, Union

        if annotation is type(None):
            return True

        origin = get_origin(annotation)

        return (
            origin is Union
            and type(None) in get_args(annotation)
        )

    @staticmethod
    def _add_field_constraints(
        field_kwargs: Dict[str, Any],
        schema: Dict[str, Any],
    ) -> None:
        """
        Transfer common JSON Schema constraints into Pydantic fields.
        """

        mappings = {
            "minimum": "ge",
            "maximum": "le",
            "exclusiveMinimum": "gt",
            "exclusiveMaximum": "lt",
            "minLength": "min_length",
            "maxLength": "max_length",
            "pattern": "pattern",
        }

        for json_key, pydantic_key in mappings.items():
            if json_key in schema:
                field_kwargs[pydantic_key] = schema[json_key]

        if "minItems" in schema:
            field_kwargs["min_length"] = schema["minItems"]

        if "maxItems" in schema:
            field_kwargs["max_length"] = schema["maxItems"]

    @staticmethod
    def _to_class_name(value: str) -> str:
        """
        Convert arbitrary names into valid Python class names.
        """

        parts = re.findall(r"[a-zA-Z0-9]+", value)

        name = "".join(
            part.capitalize()
            for part in parts
        )

        if not name:
            name = "MCPToolArguments"

        if name[0].isdigit():
            name = f"Tool{name}"

        return name
