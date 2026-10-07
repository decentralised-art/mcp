import unittest

from decentralised_art_mcp.resources import resource_uri
from decentralised_art_mcp.server import build_registries
from decentralised_art_mcp.documentation import DOCUMENTS


class ResourceTests(unittest.TestCase):
    def test_can_read_registered_resource(self):
        _, resources = build_registries()
        resource = resources.read("core.primer")
        self.assertEqual(resource["mime_type"], "text/markdown")
        self.assertIn("format-agnostic", resource["text"])
        self.assertEqual(resource["uri"], resource_uri("core.primer"))

    def test_bundled_documentation_is_readable_as_resources_and_tools(self):
        tools, resources = build_registries()
        for topic in DOCUMENTS:
            name = f"core.{topic}" if topic in {"getting-started", "primer"} else f"core.docs.{topic}"
            resource = resources.read(resource_uri(name))
            result = tools.invoke("core.documentation", {"topic": topic, "max_lines": 7})
            self.assertTrue(result["ok"])
            lines = resource["text"].splitlines()
            self.assertEqual(result["data"]["text"], "\n".join(lines[:7]))
            self.assertEqual(result["data"]["total_lines"], len(lines))
            self.assertEqual(result["data"]["next_start_line"], 8)
            continuation = tools.invoke("core.documentation", {"topic": topic, "start_line": 8, "max_lines": 300})
            self.assertEqual(continuation["data"]["text"], "\n".join(lines[7:307]))
            last = tools.invoke("core.documentation", {"topic": topic, "start_line": len(lines)})
            self.assertIsNone(last["data"]["next_start_line"])

    def test_only_core_resources_are_registered(self):
        _, resources = build_registries()
        self.assertEqual(len(resources.describe_resources()), len(DOCUMENTS))
        self.assertTrue(all(item["name"].startswith("core.") for item in resources.describe_resources()))

    def test_documentation_is_available_without_an_account(self):
        tools, _ = build_registries()
        result = tools.invoke("core.documentation", {})
        self.assertTrue(result["ok"])
        self.assertIn("core.create_account", result["data"]["text"])
        for params in ({"topic": "../../secret"}, {"start_line": 1000000}, {"max_lines": 301}):
            self.assertFalse(tools.invoke("core.documentation", params)["ok"])


if __name__ == "__main__":
    unittest.main()
