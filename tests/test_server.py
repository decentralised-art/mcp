import unittest

from decentralised_art_mcp.server import SERVER_INSTRUCTIONS, build_registries
from decentralised_art_mcp.documentation import DOCUMENTS


class ServerTests(unittest.TestCase):
    def test_server_exposes_only_core_tools_and_resources(self):
        registry, resources = build_registries()
        tool_names = {item["full_name"] for item in registry.describe_tools()}
        self.assertTrue(tool_names)
        self.assertTrue(all(name.startswith("core.") for name in tool_names))
        self.assertIn("core.connector_exists", tool_names)
        self.assertIn("core.build_parent_connector", tool_names)
        self.assertIn("core.transformation_exists", tool_names)
        self.assertIn("core.condition_exists", tool_names)
        self.assertIn("core.get_account", tool_names)
        self.assertIn("core.get_feed_page", tool_names)
        self.assertIn("core.get_feed_stream_replay", tool_names)
        self.assertIn("core.get_nonce", tool_names)
        self.assertIn("core.create_account", tool_names)
        self.assertIn("core.documentation", tool_names)
        for name in (
            "create_connector", "create_transformation", "create_condition",
            "simulate_connector", "prepare_publication", "publish_entity",
            "confirm_publication", "execute_connector",
        ):
            self.assertIn(f"core.{name}", tool_names)
        for kind in ("connector", "transformation", "condition"):
            self.assertNotIn(f"core.deploy_{kind}", tool_names)
        resource_names = {item["name"] for item in resources.describe_resources()}
        self.assertIn("core.primer", resource_names)
        self.assertIn("core.getting-started", resource_names)
        self.assertEqual(len(resource_names), len(DOCUMENTS))
        self.assertIn("core.documentation", SERVER_INSTRUCTIONS)
        self.assertIn("core.create_account", SERVER_INSTRUCTIONS)
        for tool in registry.describe_tools():
            if "private_key" in tool["input_schema"]["properties"]:
                self.assertIn("account_id", tool["input_schema"]["properties"])


if __name__ == "__main__":
    unittest.main()
