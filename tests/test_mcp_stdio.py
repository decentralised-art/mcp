import os
import sys
import unittest
from tempfile import TemporaryDirectory
from pathlib import Path

import anyio
import mcp.types as types
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


class MCPStdioTests(unittest.TestCase):
    def test_stdio_server_lifecycle(self):
        async def _run():
            env = dict(os.environ)
            existing_path = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = str(SRC) if not existing_path else str(SRC) + os.pathsep + existing_path
            server = StdioServerParameters(
                command=sys.executable,
                args=["-m", "decentralised_art_mcp.server", "stdio"],
                env=env,
                cwd=str(ROOT),
            )
            async with stdio_client(server) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    initialized = await session.initialize()
                    self.assertIn("core.documentation", initialized.instructions)
                    self.assertIn("core.create_account", initialized.instructions)
                    self.assertIn("core.docs.llms-full", initialized.instructions)

                    tools_page_1 = await session.list_tools()
                    tool_names_page_1 = {tool.name for tool in tools_page_1.tools}
                    self.assertIn("core.connector_exists", tool_names_page_1)
                    self.assertIn("core.documentation", tool_names_page_1)
                    self.assertIn("core.create_account", tool_names_page_1)
                    self.assertTrue(tools_page_1.nextCursor)

                    tools_page_2 = await session.list_tools(params=types.PaginatedRequestParams(cursor=tools_page_1.nextCursor))
                    tool_names_page_2 = {tool.name for tool in tools_page_2.tools}
                    self.assertTrue(tool_names_page_2)
                    self.assertNotEqual(tool_names_page_1, tool_names_page_2)
                    all_tool_names = tool_names_page_1 | tool_names_page_2
                    next_cursor = tools_page_2.nextCursor
                    while next_cursor:
                        page = await session.list_tools(params=types.PaginatedRequestParams(cursor=next_cursor))
                        all_tool_names.update(tool.name for tool in page.tools)
                        next_cursor = page.nextCursor
                    for name in (
                        "create_connector", "create_transformation", "create_condition",
                        "simulate_connector", "prepare_publication", "publish_entity",
                        "confirm_publication", "execute_connector",
                    ):
                        self.assertIn(f"core.{name}", all_tool_names)
                    self.assertTrue(all(name.startswith("core.") for name in all_tool_names))

                    resources_page_1 = await session.list_resources()
                    resource_uris_page_1 = {str(resource.uri) for resource in resources_page_1.resources}
                    self.assertIn("decentralised-art://resource/core.primer", resource_uris_page_1)
                    self.assertIn("decentralised-art://resource/core.getting-started", resource_uris_page_1)
                    self.assertIn("decentralised-art://resource/core.docs.llms-full", resource_uris_page_1)
                    self.assertIsNone(resources_page_1.nextCursor)

                    read_result = await session.read_resource("decentralised-art://resource/core.primer")
                    self.assertEqual(len(read_result.contents), 1)
                    self.assertIn("format-agnostic", read_result.contents[0].text)
                    self.assertEqual(str(read_result.contents[0].uri), "decentralised-art://resource/core.primer")
                    docs = await session.call_tool("core.documentation", {})
                    self.assertFalse(docs.isError)
                    self.assertIn("core.create_account", docs.structuredContent["data"]["text"])
                    if os.name == "posix":
                        account = await session.call_tool("core.create_account", {"account_id": "stdio_owner"})
                        again = await session.call_tool("core.create_account", {"account_id": "stdio_owner"})
                        self.assertFalse(account.isError)
                        self.assertTrue(account.structuredContent["data"]["created"])
                        self.assertEqual(account.structuredContent["data"]["address"], again.structuredContent["data"]["address"])
                        self.assertFalse(again.structuredContent["data"]["created"])
                        self.assertEqual(set(account.structuredContent["data"]), {"account_id", "address", "created"})

                    call_result = await session.call_tool("core.build_parent_connector", {"name": "piece", "child_names": ["a", "b"]})
                    self.assertFalse(call_result.isError)
                    self.assertEqual(call_result.structuredContent["data"]["name"], "piece")
                    self.assertEqual(len(call_result.structuredContent["data"]["dimensions"]), 2)

        with TemporaryDirectory() as account_directory:
            from unittest.mock import patch
            with patch.dict(os.environ, {"DECENTRALISED_ART_ACCOUNT_ROOT": account_directory, "PRIVATE_KEY": ""}):
                anyio.run(_run)


if __name__ == "__main__":
    unittest.main()
