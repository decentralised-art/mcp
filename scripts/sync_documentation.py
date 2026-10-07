"""Refresh bundled platform documentation from its single published source."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date
from pathlib import Path

import requests


SLUGS = ("tutorial", "mcp", "sdk", "api-reference", "about", "roadmap")
DESTINATION = Path(__file__).resolve().parents[1] / "src/decentralised_art_mcp/resources/core/docs"
SOURCE_URL = "https://decentralised.art/llms-full.txt"


def snapshot_pages(text: str, retrieved_at: str) -> dict[str, str]:
    date.fromisoformat(retrieved_at)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    parts = text.split("\n\n---\n\n")
    pages = {}
    for part in parts:
        match = re.search(r"\nSource: https://decentralised\.art/([a-z0-9-]+)\s*$", part)
        if not match:
            raise ValueError("Unexpected platform page source; bundled documentation was not changed.")
        slug = match.group(1)
        # New platform pages remain in the complete snapshot even before they
        # receive their own topic in this release's catalog.
        if slug not in SLUGS:
            continue
        if slug in pages:
            raise ValueError(f"Duplicate platform page {slug}; bundled documentation was not changed.")
        source = f"https://decentralised.art/{slug}"
        if slug == "tutorial":
            part = part[part.index("# Tutorial\n"):]
        pages[slug] = f"> Bundled platform snapshot. Retrieved {retrieved_at} from {source}.\n> Read core.getting-started for account onboarding in this MCP release.\n\n{part.strip()}\n"
    if set(pages) != set(SLUGS):
        raise ValueError("A required platform page is missing; review the bundled topic catalog before syncing.")
    return pages


def write_snapshot(content: bytes, retrieved_at: str, destination: Path = DESTINATION) -> None:
    pages = snapshot_pages(content.decode("utf-8"), retrieved_at)
    destination.mkdir(parents=True, exist_ok=True)
    # Keep the complete document verbatim. Provenance lives alongside it rather
    # than changing the downloaded document or replacing its introduction.
    (destination / "llms-full.txt").write_bytes(content)
    metadata = {"source": SOURCE_URL, "retrieved_at": retrieved_at, "sha256": hashlib.sha256(content).hexdigest()}
    (destination / "llms-full.metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    for slug, text in pages.items():
        (destination / f"{slug}.md").write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-file", type=Path, help="Use a previously downloaded llms-full.txt instead of fetching it")
    parser.add_argument("--retrieved-at", default=date.today().isoformat(), help="ISO retrieval date for snapshot provenance")
    args = parser.parse_args()
    if args.source_file:
        content = args.source_file.read_bytes()
    else:
        response = requests.get(SOURCE_URL, timeout=30)
        response.raise_for_status()
        content = response.content
    write_snapshot(content, args.retrieved_at)
    print(f"Refreshed the complete llms-full.txt and {len(SLUGS)} individual platform pages.")


if __name__ == "__main__":
    main()
