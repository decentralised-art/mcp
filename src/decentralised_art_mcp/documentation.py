"""Bundled documentation shared by MCP resources and tool-only hosts."""
from __future__ import annotations

from pathlib import Path

from .errors import ValidationError


DOC_ROOT = Path(__file__).parent / "resources" / "core"
DOCUMENTS = {
    "getting-started": ("Getting started, fresh accounts and existing owners", "getting-started.md"),
    "primer": ("Protocol concepts and operation lifecycle", "primer.md"),
    "llms-full": ("Complete platform documentation: system concepts, tutorial and good practices", "docs/llms-full.txt"),
    "tutorial": ("Platform tutorial", "docs/tutorial.md"),
    "mcp": ("Platform MCP installation and configuration", "docs/mcp.md"),
    "sdk": ("Platform JavaScript and Python SDK guide", "docs/sdk.md"),
    "api-reference": ("Chain and services API reference", "docs/api-reference.md"),
    "about": ("About decentralised.art", "docs/about.md"),
    "roadmap": ("Platform roadmap", "docs/roadmap.md"),
}


def read_documentation(topic: str = "getting-started", *, start_line: int = 1, max_lines: int = 200) -> dict:
    if topic not in DOCUMENTS:
        raise ValidationError("Unknown documentation topic.", details={"topics": list(DOCUMENTS)})
    title, filename = DOCUMENTS[topic]
    lines = (DOC_ROOT / filename).read_text(encoding="utf-8").splitlines()
    if start_line < 1 or start_line > len(lines):
        raise ValidationError("start_line is outside this document.", details={"total_lines": len(lines)})
    end = min(start_line - 1 + max_lines, len(lines))
    return {
        "topic": topic, "title": title,
        "text": "\n".join(lines[start_line - 1:end]),
        "start_line": start_line, "total_lines": len(lines),
        "next_start_line": end + 1 if end < len(lines) else None,
        "topics": [{"topic": name, "title": item[0]} for name, item in DOCUMENTS.items()],
    }
