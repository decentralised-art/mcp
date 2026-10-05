"""Generate the MCP chain contracts from the pinned api-spec submodule."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
SPEC_ROOT = ROOT / "submodules" / "api-spec"
OUTPUT = ROOT / "src" / "decentralised_art_mcp" / "generated" / "api_contracts.json"
LEGACY_AUTH_CONTRACTS = ROOT / "scripts" / "compat" / "legacy_auth_contracts.json"
OPERATIONS = {
    "GET_version", "GET_nonce", "POST_auth", "GET_connector",
    "GET_transformation", "GET_condition", "POST_connector",
    "POST_transformation", "POST_condition", "POST_execute",
    "POST_simulate", "GET_formats", "GET_format", "GET_accountInfo",
    "GET_feed", "GET_feedStream", "POST_publishPrepare",
    "POST_publishSend", "POST_publishConfirm",
}


@lru_cache(maxsize=None)
def load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def resolve(node: Any, source: Path, trail: frozenset[tuple[Path, str]] = frozenset()) -> Any:
    if isinstance(node, list):
        return [resolve(item, source, trail) for item in node]
    if not isinstance(node, dict):
        return node
    if "$ref" not in node:
        return {key: resolve(value, source, trail) for key, value in node.items()}

    ref = node["$ref"]
    relative_path, _, pointer = ref.partition("#")
    target_path = (source.parent / relative_path).resolve() if relative_path else source
    if not target_path.is_relative_to(SPEC_ROOT.resolve()):
        raise ValueError(f"OpenAPI reference escapes api-spec: {ref}")
    identity = (target_path, pointer)
    if identity in trail:
        raise ValueError(f"Recursive OpenAPI reference: {ref}")
    target = load_yaml(target_path)
    if pointer:
        if not pointer.startswith("/"):
            raise ValueError(f"Invalid OpenAPI pointer: {ref}")
        for part in pointer[1:].split("/"):
            target = target[part.replace("~1", "/").replace("~0", "~")]
    resolved = resolve(target, target_path, trail | {identity})
    siblings = {key: value for key, value in node.items() if key != "$ref"}
    if siblings:
        if not isinstance(resolved, dict):
            raise ValueError(f"Cannot extend scalar OpenAPI reference: {ref}")
        resolved = {**resolved, **resolve(siblings, source, trail)}
    return resolved


def json_schema(content: dict[str, Any], source: Path) -> dict[str, Any] | None:
    body = content.get("application/json")
    if not body or "schema" not in body:
        return None
    return resolve(body["schema"], source)


def operation_contract(path: str, method: str, operation: dict[str, Any],
                       path_parameters: list[dict[str, Any]], source: Path,
                       default_security: list[dict[str, Any]]) -> dict[str, Any]:
    parameters = [*path_parameters, *operation.get("parameters", [])]
    query = [resolve(item, source) for item in parameters if item.get("in") == "query"]
    query_schema = {
        "type": "object",
        "properties": {item["name"]: item["schema"] for item in query},
        "required": [item["name"] for item in query if item.get("required")],
        "additionalProperties": False,
    }
    request_body = operation.get("requestBody", {})
    if "$ref" in request_body:
        request_body = resolve(request_body, source)
    responses = operation.get("responses", {})
    response_schemas = {
        str(status): json_schema(response.get("content", {}), source)
        for status, response in sorted(responses.items())
        if re.fullmatch(r"2\d\d", str(status)) and
        "application/json" in response.get("content", {})
    }
    return {
        "method": method.upper(),
        "path": path,
        "security": operation.get("security", default_security),
        "query_schema": query_schema,
        "request_schema": json_schema(request_body.get("content", {}), source),
        "response_schemas": response_schemas,
    }


def generate() -> str:
    chain = SPEC_ROOT / "apis" / "chain"
    if not chain.is_dir():
        raise SystemExit("Initialize the pinned spec: git submodule update --init submodules/api-spec")
    contracts: dict[str, Any] = {}
    for source in sorted(chain.glob("*/openapi.yaml")):
        document = load_yaml(source)
        for path, path_item in document.get("paths", {}).items():
            for method, operation in path_item.items():
                if method.lower() not in {"get", "post", "head"}:
                    continue
                operation_id = operation.get("operationId")
                if operation_id not in OPERATIONS:
                    continue
                if operation_id in contracts:
                    raise ValueError(f"Duplicate OpenAPI operation: {operation_id}")
                contracts[operation_id] = operation_contract(
                    path, method, operation, path_item.get("parameters", []), source,
                    document.get("security", []))
    missing = OPERATIONS - contracts.keys()
    if missing:
        raise ValueError(f"Missing OpenAPI operations: {', '.join(sorted(missing))}")
    legacy_auth = json.loads(LEGACY_AUTH_CONTRACTS.read_text(encoding="utf-8"))
    for operation_id, contract in legacy_auth["operations"].items():
        contracts[f"{operation_id}_legacy"] = contract
    spec_commit = subprocess.check_output(
        ["git", "-C", str(SPEC_ROOT), "rev-parse", "HEAD"], text=True).strip()
    return json.dumps({"spec_commit": spec_commit,
                      "compatibility_spec_commits": {"legacy_auth": legacy_auth["spec_commit"]},
                      "operations": contracts},
                      indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if the committed contract is stale")
    args = parser.parse_args()
    generated = generate()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != generated:
            raise SystemExit(f"{OUTPUT} is stale; run python scripts/generate_api_contracts.py")
        print(f"API contracts match api-spec {json.loads(generated)['spec_commit'][:7]}")
        return
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(generated, encoding="utf-8")
    print(f"Generated {OUTPUT} from api-spec {json.loads(generated)['spec_commit'][:7]}")


if __name__ == "__main__":
    main()
