import hashlib
import importlib.util
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from decentralised_art_mcp.documentation import DOC_ROOT
from decentralised_art_mcp.server import build_registries


SPEC = importlib.util.spec_from_file_location("sync_documentation", Path(__file__).resolve().parents[1] / "scripts/sync_documentation.py")
sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync)


class DocumentationSyncTests(unittest.TestCase):
    def fixture(self, *, extra_page=False):
        pages = [f"# {slug.title()}\n\nComplete {slug} page.\n\nSource: https://decentralised.art/{slug}" for slug in sync.SLUGS]
        pages[0] = pages[0].replace("# Tutorial", "# decentralised.art\n\n> System overview: opérations.\n\n# Tutorial", 1)
        if extra_page:
            pages.append("# New good practices\n\nNew guidance.\n\nSource: https://decentralised.art/good-practices")
        return ("\n\n---\n\n".join(pages) + "\n").encode("utf-8")

    def test_complete_document_is_preserved_verbatim_including_new_pages(self):
        # Parsing can normalize newlines for individual guides, but the complete
        # source must retain its original bytes and all future platform pages.
        content = self.fixture(extra_page=True).replace(b"\n", b"\r\n")
        with TemporaryDirectory() as directory:
            destination = Path(directory)
            sync.write_snapshot(content, "2026-10-07", destination)
            self.assertEqual((destination / "llms-full.txt").read_bytes(), content)
            metadata = json.loads((destination / "llms-full.metadata.json").read_text())
            self.assertEqual(metadata["sha256"], hashlib.sha256(content).hexdigest())
            self.assertEqual(metadata["source"], "https://decentralised.art/llms-full.txt")
            self.assertEqual(metadata["retrieved_at"], "2026-10-07")
            self.assertTrue(all((destination / f"{slug}.md").exists() for slug in sync.SLUGS))

    def test_invalid_source_does_not_replace_previous_snapshot(self):
        with TemporaryDirectory() as directory:
            destination = Path(directory)
            sync.write_snapshot(self.fixture(), "2026-10-07", destination)
            original = {path.name: path.read_bytes() for path in destination.iterdir()}
            with self.assertRaises(ValueError):
                sync.write_snapshot(b"# Incomplete documentation", "2026-10-07", destination)
            self.assertEqual({path.name: path.read_bytes() for path in destination.iterdir()}, original)

    def test_bundled_full_resource_and_all_tool_pages_match_verified_snapshot(self):
        raw = (DOC_ROOT / "docs/llms-full.txt").read_bytes()
        metadata = json.loads((DOC_ROOT / "docs/llms-full.metadata.json").read_text())
        self.assertEqual(hashlib.sha256(raw).hexdigest(), metadata["sha256"])
        tools, resources = build_registries()
        resource = resources.read("core.docs.llms-full")
        self.assertEqual(resource["mime_type"], "text/plain")
        self.assertEqual(resource["text"], raw.decode("utf-8"))
        lines = []
        start_line = 1
        while start_line is not None:
            result = tools.invoke("core.documentation", {"topic": "llms-full", "start_line": start_line, "max_lines": 300})
            self.assertTrue(result["ok"])
            # Preserve a blank final line at a page boundary; splitlines()
            # would drop it when reconstructing line-paginated tool output.
            lines.extend(result["data"]["text"].split("\n"))
            start_line = result["data"]["next_start_line"]
        self.assertEqual(lines, raw.decode("utf-8").splitlines())
