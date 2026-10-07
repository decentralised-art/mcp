from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any, Dict, Tuple

import mcp.server.stdio
import mcp.types as types
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.lowlevel.server import ReadResourceContents
from mcp.server.models import InitializationOptions

from . import __version__
from .pagination import DEFAULT_RESOURCES_PAGE_SIZE, DEFAULT_TOOLS_PAGE_SIZE, paginate
from .registry import ToolRegistry
from .resources import ResourceRegistry
from .tools import core
from .documentation import DOC_ROOT, DOCUMENTS
from .models import ResourceSpec


SERVER_NAME = "decentralised-art-mcp"
SERVER_INSTRUCTIONS = (
    "decentralised.art MCP server exposing core protocol operations for local drafts, simulation, "
    "publication, onchain execution, and discovery. "
    "Read core.documentation (default topic getting-started) before creating operations; "
    "the same bundled guides are available as core.getting-started, core.primer and core.docs.* resources. "
    "Before designing operations, read topic llms-full or resource core.docs.llms-full for the complete "
    "platform documentation, system concepts and good practices. For paginated tool reads, follow "
    "next_start_line until null; a single page is not the whole document. "
    "Reading, simulation and execution need no account. For a user-requested fresh identity, "
    "core.create_account generates and retains a dedicated Ethereum key locally and returns only "
    "account_id and address; pass account_id to authenticated tools and reuse it for that owner's drafts. "
    "Do not require the user to supply an existing private key for a fresh identity. "
    "Never ask for or expose private keys in chat. Existing owners can configure PRIVATE_KEY locally. "
    "Account creation and drafts spend no gas; publication needs funded owner accounts and explicit fee limits."
)
TOOL_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "ok": {"type": "boolean"},
        "data": {"type": "object"},
        "error": {"type": "object"},
    },
    "required": ["ok"],
    "additionalProperties": True,
}


def build_registries() -> Tuple[ToolRegistry, ResourceRegistry]:
    tools = ToolRegistry()
    resources = ResourceRegistry()

    core.register(tools)

    for topic, (title, filename) in DOCUMENTS.items():
        name = f"core.{topic}" if topic in {"primer", "getting-started"} else f"core.docs.{topic}"
        resources.register(ResourceSpec(
            name=name, description=title,
            mime_type="text/plain" if filename.endswith(".txt") else "text/markdown",
            file_path=DOC_ROOT / filename,
        ))

    return tools, resources


def build_mcp_server(tools: ToolRegistry, resources: ResourceRegistry) -> Server:
    server: Server = Server(SERVER_NAME, version=__version__, instructions=SERVER_INSTRUCTIONS)

    @server.list_tools()
    async def _list_tools(request: types.ListToolsRequest) -> types.ListToolsResult:
        all_tools = [
            types.Tool(
                name=item["full_name"],
                title=item.get("name"),
                description=item["description"],
                inputSchema=item["input_schema"],
                outputSchema=TOOL_OUTPUT_SCHEMA,
            )
            for item in tools.describe_tools()
        ]
        cursor = request.params.cursor if request.params is not None else None
        page, next_cursor = paginate(all_tools, cursor, page_size=DEFAULT_TOOLS_PAGE_SIZE)
        return types.ListToolsResult(tools=page, nextCursor=next_cursor)

    @server.call_tool(validate_input=False)
    async def _call_tool(name: str, arguments: dict[str, Any] | None = None) -> types.CallToolResult:
        result = tools.invoke(name, dict(arguments or {}))
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))],
            structuredContent=result,
            isError=not bool(result.get("ok")),
        )

    @server.list_resources()
    async def _list_resources(request: types.ListResourcesRequest) -> types.ListResourcesResult:
        all_resources = [
            types.Resource(
                uri=item["uri"],
                name=item["name"],
                description=item["description"],
                mimeType=item["mime_type"],
            )
            for item in resources.describe_resources()
        ]
        cursor = request.params.cursor if request.params is not None else None
        page, next_cursor = paginate(all_resources, cursor, page_size=DEFAULT_RESOURCES_PAGE_SIZE)
        return types.ListResourcesResult(resources=page, nextCursor=next_cursor)

    @server.read_resource()
    async def _read_resource(uri: str) -> list[ReadResourceContents]:
        resource = resources.read(uri)
        return [ReadResourceContents(content=resource["text"], mime_type=resource["mime_type"])]

    return server


async def run_stdio_server() -> None:
    tools, resources = build_registries()
    server = build_mcp_server(tools, resources)
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name=SERVER_NAME,
                server_version=__version__,
                instructions=SERVER_INSTRUCTIONS,
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="decentralised.art core MCP server and CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("stdio")
    sub.add_parser("list-tools")
    sub.add_parser("list-resources")

    read_resource = sub.add_parser("read-resource")
    read_resource.add_argument("resource_name")

    invoke = sub.add_parser("invoke")
    invoke.add_argument("tool_name")
    invoke.add_argument("payload", help="JSON payload string")

    args = parser.parse_args()
    registry, resources = build_registries()

    if args.cmd == "stdio":
        asyncio.run(run_stdio_server())
        return
    if args.cmd == "list-tools":
        print(json.dumps(registry.describe_tools(), ensure_ascii=False, indent=2))
        return
    if args.cmd == "list-resources":
        print(json.dumps(resources.describe_resources(), ensure_ascii=False, indent=2))
        return
    if args.cmd == "read-resource":
        print(json.dumps(resources.read(args.resource_name), ensure_ascii=False, indent=2))
        return
    if args.cmd == "invoke":
        payload: Dict[str, Any] = json.loads(args.payload)
        result = registry.invoke(args.tool_name, payload)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    raise SystemExit(f"Unknown command: {args.cmd}")


if __name__ == "__main__":
    main()
