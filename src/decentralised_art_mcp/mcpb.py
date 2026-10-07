from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from . import __version__
from .server import build_registries


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = ROOT_DIR / "dist"
BUNDLE_NAME = "decentralised-art-mcp"
MANIFEST_VERSION = "0.4"


def _repo_path(relative_path: str) -> Path:
    return ROOT_DIR / relative_path


def build_manifest() -> dict:
    tools, _ = build_registries()
    return {
        "manifest_version": MANIFEST_VERSION,
        "name": BUNDLE_NAME,
        "display_name": "decentralised.art MCP",
        "version": __version__,
        "description": "Core MCP server for decentralised.art.",
        "long_description": "Core decentralised.art operations for local drafts, simulation, network publication, onchain execution, and discovery.",
        "author": {
            "name": "decentralised.art maintainers",
        },
        "server": {
            "type": "uv",
            "entry_point": "src/decentralised_art_mcp/server.py",
            "mcp_config": {
                "command": "uv",
                "args": [
                    "run",
                    "--directory",
                    "${__dirname}",
                    "decentralised-art-mcp",
                    "stdio",
                ],
                "env": {
                    "API_BASE": "${user_config.api_base}",
                    "PRIVATE_KEY": "${user_config.private_key}",
                    "DECENTRALISED_ART_TIMEOUT": "${user_config.timeout}",
                    "DECENTRALISED_ART_ARTIFACT_ROOT": "${user_config.artifact_root}",
                    "DECENTRALISED_ART_ACCOUNT_ROOT": "${user_config.account_root}",
                },
            },
        },
        "tools": [
            {
                "name": item["full_name"],
                "description": item["description"],
            }
            for item in tools.describe_tools()
        ],
        "keywords": [
            "decentralised-art",
            "mcp",
            "decentralised.art",
            "format-agnostic",
        ],
        "compatibility": {
            "claude_desktop": ">=1.0.0",
            "platforms": ["darwin", "win32", "linux"],
            "runtimes": {
                "python": ">=3.10",
            },
        },
        "user_config": {
            "api_base": {
                "type": "string",
                "title": "decentralised.art API Base URL",
                "description": "Base URL for the decentralised.art API.",
                "default": "https://api.decentralised.art/chain",
                "required": True,
            },
            "private_key": {
                "type": "string",
                "title": "Private Key",
                "description": "Optional existing-owner Ethereum key. Leave empty to let the agent create a fresh local identity with core.create_account; never provide a key in chat.",
                "sensitive": True,
                "required": False,
                "default": "",
            },
            "timeout": {
                "type": "number",
                "title": "API Timeout (seconds)",
                "description": "HTTP timeout used for decentralised.art API requests.",
                "default": 15,
                "min": 1,
                "max": 120,
                "required": True,
            },
            "artifact_root": {
                "type": "string",
                "title": "Artifact Root",
                "description": "Directory for persistent publication transaction records.",
                "default": "decentralised-art-mcp-artifacts",
                "required": True,
            },
            "account_root": {
                "type": "string",
                "title": "Local Account Storage",
                "description": "Optional persistent absolute directory for generated signing keys (owner-only). Empty uses ~/.decentralised-art-mcp/accounts. Fresh-account generation requires macOS/Linux.",
                "default": "",
                "required": False,
            },
        },
    }


def _copytree(src: Path, dest: Path) -> None:
    shutil.copytree(
        src,
        dest,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )


def _write_bundle_tree(bundle_root: Path) -> None:
    bundle_root.mkdir(parents=True, exist_ok=True)
    shutil.copy2(_repo_path("pyproject.toml"), bundle_root / "pyproject.toml")
    shutil.copy2(_repo_path("README.md"), bundle_root / "README.md")
    _copytree(_repo_path("src"), bundle_root / "src")
    (bundle_root / "manifest.json").write_text(
        json.dumps(build_manifest(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def build_bundle(output_dir: Path = DEFAULT_OUTPUT_DIR) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    staging_dir = output_dir / f"{BUNDLE_NAME}-bundle"
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    _write_bundle_tree(staging_dir)

    bundle_path = output_dir / f"{BUNDLE_NAME}-{__version__}.mcpb"
    if bundle_path.exists():
        bundle_path.unlink()

    with ZipFile(bundle_path, "w", compression=ZIP_DEFLATED) as archive:
        for path in sorted(staging_dir.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(staging_dir).as_posix())

    shutil.rmtree(staging_dir)
    return bundle_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a Claude Desktop .mcpb bundle for decentralised.art")
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory where the built .mcpb artifact should be written.",
    )
    args = parser.parse_args()
    print(build_bundle(Path(args.output_dir).resolve()))


if __name__ == "__main__":
    main()
