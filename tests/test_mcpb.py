from __future__ import annotations

import json
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from decentralised_art_mcp.mcpb import build_bundle, build_manifest
from decentralised_art_mcp.documentation import DOC_ROOT


class McpbTests(TestCase):
    def test_manifest_uses_uv_runtime(self) -> None:
        manifest = build_manifest()
        self.assertEqual(manifest["manifest_version"], "0.4")
        self.assertEqual(manifest["server"]["type"], "uv")
        self.assertEqual(manifest["server"]["mcp_config"]["command"], "uv")
        self.assertIn("api_base", manifest["user_config"])
        self.assertIn("private_key", manifest["user_config"])
        self.assertIn("timeout", manifest["user_config"])
        self.assertIn("artifact_root", manifest["user_config"])
        self.assertIn("account_root", manifest["user_config"])
        self.assertTrue(any(tool["name"] == "core.build_parent_connector" for tool in manifest["tools"]))
        self.assertTrue(all(tool["name"].startswith("core.") for tool in manifest["tools"]))

    def test_build_bundle_writes_expected_files(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            bundle_path = build_bundle(Path(tmp_dir))
            self.assertTrue(bundle_path.exists())
            self.assertEqual(bundle_path.suffix, ".mcpb")
            with zipfile.ZipFile(bundle_path) as archive:
                names = set(archive.namelist())
                self.assertIn("manifest.json", names)
                self.assertIn("pyproject.toml", names)
                self.assertIn("README.md", names)
                self.assertIn("src/decentralised_art_mcp/server.py", names)
                self.assertIn("src/decentralised_art_mcp/lifecycle.py", names)
                self.assertFalse(any(name.startswith("src/decentralised_art_mcp/adapters/") for name in names))
                self.assertFalse(any(name.startswith("src/decentralised_art_mcp/resources/music/") for name in names))
                contract_path = "src/decentralised_art_mcp/generated/api_contracts.json"
                self.assertIn(contract_path, names)
                self.assertIn("POST_publishPrepare", archive.read(contract_path).decode("utf-8"))
                primer_path = "src/decentralised_art_mcp/resources/core/primer.md"
                self.assertIn(primer_path, names)
                self.assertIn("core.simulate_connector", archive.read(primer_path).decode("utf-8"))
                self.assertIn("core.create_account", archive.read("src/decentralised_art_mcp/resources/core/getting-started.md").decode("utf-8"))
                for topic in ("tutorial", "mcp", "sdk", "api-reference", "about", "roadmap"):
                    self.assertIn(f"src/decentralised_art_mcp/resources/core/docs/{topic}.md", names)
                full_path = "src/decentralised_art_mcp/resources/core/docs/llms-full.txt"
                self.assertEqual(archive.read(full_path), (DOC_ROOT / "docs/llms-full.txt").read_bytes())
                self.assertIn("src/decentralised_art_mcp/resources/core/docs/llms-full.metadata.json", names)
                manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
                self.assertEqual(manifest["name"], "decentralised-art-mcp")
                tool_names = {tool["name"] for tool in manifest["tools"]}
                self.assertIn("core.publish_entity", tool_names)
                self.assertIn("core.confirm_publication", tool_names)
                self.assertIn("core.documentation", tool_names)
                self.assertIn("core.create_account", tool_names)
                self.assertTrue(all(name.startswith("core.") for name in tool_names))
