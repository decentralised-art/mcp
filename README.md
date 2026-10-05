# mcp

This repository provides the decentralised.art MCP server and its `decentralised-art-mcp` CLI.
It exposes format-agnostic protocol operations under the `core.*` namespace.

Agents can read the full decentralised.art documentation in markdown, starting from
https://decentralised.art/llms.txt.

If you are a user of this repo, the important question is simple:

- install it
- run it as an MCP server
- register it in your MCP-capable host
- use it

## What users get

When the MCP server is running, an MCP host can use tools such as:

- `core.connector_exists`
- `core.get_connector`
- `core.get_transformation`
- `core.get_condition`
- `core.transformation_exists`
- `core.condition_exists`
- `core.get_feed_page`
- `core.get_feed_stream_replay`
- `core.list_formats`
- `core.get_format`
- `core.get_account`
- `core.get_nonce`
- `core.create_connector`
- `core.create_transformation`
- `core.create_condition`
- `core.simulate_connector`
- `core.prepare_publication`
- `core.publish_entity`
- `core.confirm_publication`
- `core.execute_connector`
- `core.ensure_preflight`
- `core.build_parent_connector`

It also exposes the MCP resource:

- `core.primer`

## Drafts, publication and execution

The chain client uses contracts generated from the pinned `api-spec` OpenAPI
source at `submodules/api-spec` (currently pinned to `a6d9127`).
Endpoint paths, authentication requirements, query and
create/publication request shapes, and execution/publication responses are
checked against those contracts. MCP tool schemas describe MCP inputs, not HTTP
requests. To update the API contract, update the submodule, run
`python scripts/generate_api_contracts.py`, and run `make test`; CI checks that
the committed generated file matches the pinned spec. The generated contract is
packaged with the MCP server, so installed clients do not need the submodule.

`core.create_*` creates local drafts. `core.simulate_connector` previews them
without login or gas and returns `{particles, execution_mode: "simulation"}`.
`core.execute_connector` requires published entities and returns
`{block_number, block_hash, runner, registry, particles, execution_mode: "chain"}` without
login or gas; the server makes a read-only call at its configured chain block.
Keep the full chain result when using its particles so the block, runner and registry
provenance is retained. Simulation returns only particles and has no chain provenance.
Transformation and condition detail responses use `args_count`;
Solidity source is no longer part of runtime details.

Chain login signs the EIP-4361 `message` returned by `/nonce/{address}` using
EIP-191, then submits `{address, nonce, signature}` to `/auth`. Deployments that
return only a decimal `nonce` use `Login nonce: <nonce>` and submit
`{address, message, signature}`. That compatibility contract is generated from
`api-spec` commit `c628d96`, frozen in `scripts/compat/legacy_auth_contracts.json`
so regeneration needs no historical Git objects.
The MCP's `core.get_nonce` returns the address and the challenge as issued;
`message` is present when the deployment supplies it.

Publication is explicit and owner-paid. First inspect `core.prepare_publication`,
then call `core.publish_entity` with `kind`, `name`, `max_fee_per_gas`,
`max_total_fee` (both limits in wei; total means gas limit times max fee), and a
unique `record_path` inside `DECENTRALISED_ART_ARTIFACT_ROOT`. `chain_id` defaults to Sepolia
(`11155111`). Dependencies must be published before their parents. No chain RPC
URL is required: the account signs locally and the server relays one transaction.
Publish serially for each owner and resolve pending transactions before preparing
the next entity: the registry publication nonce is shared by that owner. Separate
MCP sessions are not a safe way to parallelize one owner's publications.

The publication record is persisted before broadcast. On timeout or lost response,
reuse the same record to confirm the transaction; do not create another record to
retry sending. `core.confirm_publication` also checks an existing transaction by
name, content hash and transaction hash. `mined` is not finalized/indexed: a newly
mined connector may remain unavailable to chain execution until the safe block
advances. Retry execution without republishing or substituting simulation output.

## Quick Start

Preferred onboarding flow:

```bash
cd /path/to/mcp
make install
make smoke
make stdio
```

That gives users a one-command install path, a one-command verification path, and a one-command MCP server launch path.

If your target is Claude Desktop, build the installable bundle with:

```bash
make mcpb
```

That writes a `.mcpb` file into `dist/`.

Published GitHub releases also attach the built `.mcpb` artifact automatically.

If you want to activate the environment manually after install:

```bash
source .venv/bin/activate
```

## Install From Scratch

If someone cloned the repo and wants the shortest path:

```bash
git clone https://github.com/decentralised-art/mcp.git
cd mcp
make install
make smoke
make stdio
```

## Install In Codex

If your goal is to make this MCP server available to Codex, do this:

1. Install the repo-local environment:

```bash
cd /path/to/mcp
make install
make smoke
```

2. Add this to `~/.codex/config.toml`:

```toml
[mcp_servers.decentralised-art]
command = "/path/to/mcp/.venv/bin/python"
args = ["-m", "decentralised_art_mcp.server", "stdio"]

[mcp_servers.decentralised-art.env]
PYTHONPATH = "/path/to/mcp/src"
API_BASE = "https://api.decentralised.art/chain"
PRIVATE_KEY = "<optional>"
DECENTRALISED_ART_TIMEOUT = "15"
DECENTRALISED_ART_ARTIFACT_ROOT = "/path/to/mcp/decentralised-art-mcp-artifacts"
```

Notes:
- replace `/path/to/mcp` with the real absolute path where you cloned this repo
- if you want authenticated decentralised.art actions, set `PRIVATE_KEY`
- reads, simulation, and onchain execution work without `PRIVATE_KEY`

3. Restart Codex or start a fresh Codex session.

4. Verify that Codex sees the server:

```bash
codex mcp list
```

5. In the new session, ask Codex to use it explicitly. For example:

- `Use the decentralised.art MCP to list formats`
- `Use the decentralised.art MCP to read core.primer`

Important:
- a newly registered MCP server usually will not appear inside an already-running session
- the reliable path is: add config, restart Codex, open a new session

## MCP Host Configuration

The safest way to register this MCP server in any MCP host is to point the host at the project-local venv Python.

Command:

```bash
/path/to/mcp/.venv/bin/python
```

Args:

```bash
-m decentralised_art_mcp.server stdio
```

Working directory:

```bash
/path/to/mcp
```

Environment:

```bash
PYTHONPATH=/path/to/mcp/src
API_BASE=https://api.decentralised.art/chain
PRIVATE_KEY=<your-private-key-if-you-want-authenticated-decentralised.art-actions>
DECENTRALISED_ART_TIMEOUT=15
DECENTRALISED_ART_ARTIFACT_ROOT=/path/to/mcp/decentralised-art-mcp-artifacts
```

## Example MCP Config Snippet

Use this as a generic starting point for an MCP-capable host that accepts JSON server definitions:

```json
{
  "decentralised-art": {
    "command": "/path/to/mcp/.venv/bin/python",
    "args": ["-m", "decentralised_art_mcp.server", "stdio"],
    "cwd": "/path/to/mcp",
    "env": {
      "PYTHONPATH": "/path/to/mcp/src",
      "API_BASE": "https://api.decentralised.art/chain",
      "PRIVATE_KEY": "<optional>",
      "DECENTRALISED_ART_TIMEOUT": "15",
      "DECENTRALISED_ART_ARTIFACT_ROOT": "/path/to/mcp/decentralised-art-mcp-artifacts"
    }
  }
}
```

If your host supports MCP registration but uses a different config format, keep the same values and translate only the wrapper syntax.

After you register the server in any MCP host, restart that host or start a fresh session before testing tool access.

## Host-Specific MCP Config Examples

These are the concrete MCP clients I expect most people to use first:

- Codex
- VS Code
- Cursor
- Claude Code
- MCP Inspector

Replace `/path/to/mcp` below with the directory where you cloned this repo.

### Codex CLI / Codex app

OpenAI documents Codex MCP configuration in `~/.codex/config.toml`. For this server, add:

```toml
[mcp_servers.decentralised-art]
command = "/path/to/mcp/.venv/bin/python"
args = ["-m", "decentralised_art_mcp.server", "stdio"]

[mcp_servers.decentralised-art.env]
PYTHONPATH = "/path/to/mcp/src"
API_BASE = "https://api.decentralised.art/chain"
PRIVATE_KEY = "<optional>"
DECENTRALISED_ART_TIMEOUT = "15"
DECENTRALISED_ART_ARTIFACT_ROOT = "/path/to/mcp/decentralised-art-mcp-artifacts"
```

Codex CLI and the Codex app share this configuration.

### VS Code MCP config

VS Code reads either workspace `.vscode/mcp.json` or user-profile MCP configuration. A workspace config for this server looks like:

```json
{
  "servers": {
    "decentralised-art": {
      "type": "stdio",
      "command": "/path/to/mcp/.venv/bin/python",
      "args": ["-m", "decentralised_art_mcp.server", "stdio"],
      "env": {
        "PYTHONPATH": "/path/to/mcp/src",
        "API_BASE": "https://api.decentralised.art/chain",
        "PRIVATE_KEY": "<optional>",
        "DECENTRALISED_ART_TIMEOUT": "15",
        "DECENTRALISED_ART_ARTIFACT_ROOT": "/path/to/mcp/decentralised-art-mcp-artifacts"
      }
    }
  }
}
```

### Cursor

Cursor supports project `.cursor/mcp.json` and global `~/.cursor/mcp.json`. For a stdio server, the official docs require `type: "stdio"`. Use:

```json
{
  "mcpServers": {
    "decentralised-art": {
      "type": "stdio",
      "command": "/path/to/mcp/.venv/bin/python",
      "args": ["-m", "decentralised_art_mcp.server", "stdio"],
      "env": {
        "PYTHONPATH": "/path/to/mcp/src",
        "API_BASE": "https://api.decentralised.art/chain",
        "PRIVATE_KEY": "<optional>",
        "DECENTRALISED_ART_TIMEOUT": "15",
        "DECENTRALISED_ART_ARTIFACT_ROOT": "/path/to/mcp/decentralised-art-mcp-artifacts"
      }
    }
  }
}
```

### Claude Code

Claude Code supports project-scoped `.mcp.json` files and a `claude mcp add` workflow. If you want a checked-in project config, create `.mcp.json` at the repo root:

```json
{
  "mcpServers": {
    "decentralised-art": {
      "command": "/path/to/mcp/.venv/bin/python",
      "args": ["-m", "decentralised_art_mcp.server", "stdio"],
      "env": {
        "PYTHONPATH": "/path/to/mcp/src",
        "API_BASE": "https://api.decentralised.art/chain",
        "PRIVATE_KEY": "<optional>",
        "DECENTRALISED_ART_TIMEOUT": "15",
        "DECENTRALISED_ART_ARTIFACT_ROOT": "/path/to/mcp/decentralised-art-mcp-artifacts"
      }
    }
  }
}
```

CLI alternative:

```bash
claude mcp add --transport stdio --scope project \
  --env PYTHONPATH=/path/to/mcp/src \
  --env API_BASE=https://api.decentralised.art/chain \
  --env DECENTRALISED_ART_TIMEOUT=15 \
  --env DECENTRALISED_ART_ARTIFACT_ROOT=/path/to/mcp/decentralised-art-mcp-artifacts \
  decentralised-art -- /path/to/mcp/.venv/bin/python -m decentralised_art_mcp.server stdio
```

### Claude Desktop

Claude Desktop now supports local MCP extensions as MCP Bundles (`.mcpb`). This repo includes a direct bundle path.

Build the bundle:

```bash
cd /path/to/mcp
make install
make mcpb
```

That produces a file like:

```bash
dist/decentralised-art-mcp-<version>.mcpb
```

The same bundle is also uploaded automatically to the corresponding GitHub release asset when a release is published.

Install it in Claude Desktop using any of these:

1. double-click the `.mcpb` file
2. drag the `.mcpb` file into Claude Desktop
3. use `Developer -> Extensions -> Install Extension`

After installation, Claude Desktop will prompt for the bundle's user config:

- `api_base`
- `private_key`
- `timeout`
- `artifact_root`

Implementation notes:
- the bundle is built as a `manifest_version: "0.4"` MCPB
- it uses the `uv` runtime path instead of bundling a whole Python virtual environment
- this keeps the artifact small and avoids the portability problems of shipping Python site-packages directly

### MCP Inspector

The official MCP Inspector docs show launching a local Python server through a command runner. For this repo, a direct invocation looks like:

```bash
npx @modelcontextprotocol/inspector \
  /path/to/mcp/.venv/bin/python \
  -m decentralised_art_mcp.server stdio
```

If you want the server to inherit the repo-local environment cleanly, run it with:

```bash
PYTHONPATH=/path/to/mcp/src \
API_BASE=https://api.decentralised.art/chain \
DECENTRALISED_ART_TIMEOUT=15 \
DECENTRALISED_ART_ARTIFACT_ROOT=/path/to/mcp/decentralised-art-mcp-artifacts \
npx @modelcontextprotocol/inspector \
  /path/to/mcp/.venv/bin/python \
  -m decentralised_art_mcp.server stdio
```

## Environment Variables

These are the main runtime settings:

- `API_BASE`
  - default: `https://api.decentralised.art/chain`
- `PRIVATE_KEY`
  - optional for reads, simulation, and chain execution
  - required for authenticated draft creation and publication
  - signs the chain API nonce flow (`GET /chain/nonce/{address}` then `POST /chain/auth`)
- this chain token is separate from the app/services SIWE session used by `services-backend`
- `DECENTRALISED_ART_TIMEOUT`
  - request timeout in seconds
- `DECENTRALISED_ART_ARTIFACT_ROOT`
  - directory for persistent publication transaction records
  - default: `decentralised-art-mcp-artifacts`

### Upgrading from the dcn-mcp names

Version 0.2.0 renamed everything that still used the old `dcn` naming:

| Before | Now |
|---|---|
| package and command `dcn-mcp` | `decentralised-art-mcp` |
| module `dcn_mcp.server` | `decentralised_art_mcp.server` |
| `DCN_TIMEOUT` | `DECENTRALISED_ART_TIMEOUT` |
| `DCN_ARTIFACT_ROOT` | `DECENTRALISED_ART_ARTIFACT_ROOT` |
| default folder `dcn-mcp-artifacts` | `decentralised-art-mcp-artifacts` |
| resource `core.dcn_core_primer` | `core.primer` |

After pulling, run `make install` again and update your host configuration to the new module
name. The old `DCN_TIMEOUT` and `DCN_ARTIFACT_ROOT` settings are still read when the new ones
are unset, and an existing `dcn-mcp-artifacts` folder keeps being used when no new folder
exists, so pending publication records are never lost.

## Verify That It Actually Works

There are three levels of verification.

### A. Unit and transport tests

```bash
cd /path/to/mcp
source .venv/bin/activate
python -m unittest discover -s tests -v
```

Important test coverage includes:

- registry and schema validation
- core resource exposure
- fake-client integration for core tools
- real MCP stdio lifecycle smoke test

### B. Local CLI inspection

```bash
cd /path/to/mcp
source .venv/bin/activate
python -m decentralised_art_mcp.server list-tools
python -m decentralised_art_mcp.server list-resources
python -m decentralised_art_mcp.server invoke core.build_parent_connector '{"name":"piece","child_names":["a","b"]}'
```

### C. Real MCP host integration

Register the server in your MCP host and confirm that the host can:

- list tools
- list resources
- read `core.primer`
- call `core.build_parent_connector`

## Make Targets

The preferred user interface is now `make`:

### `make install`

Creates or updates `.venv` and installs `decentralised-art-mcp` in editable mode.

### `make smoke`

Runs the repo smoke test.

### `make test`

Runs the full test suite.

### `make stdio`

Runs the real MCP stdio server from the local environment.

### `make mcpb`

Builds a Claude Desktop `.mcpb` bundle in `dist/`.

### `make list-tools`

Lists local tool metadata.

### `make list-resources`

Lists local resource metadata.

### `make read-core-primer`

Reads the core primer resource.

### `make invoke-example`

Runs one sample tool invocation locally.

## Helper Scripts

These still exist underneath the Makefile:

### `./scripts/bootstrap_venv.sh`

Creates `.venv`, upgrades `pip`, and installs `decentralised-art-mcp` in editable mode.

### `./scripts/run_stdio.sh`

Runs the real MCP stdio server from the local environment.

### `./scripts/build_mcpb.sh`

Builds a Claude Desktop `.mcpb` bundle in `dist/`.

### `./scripts/smoke_test.sh`

Runs the repo test suite and local MCP checks.

## CLI Commands

Run as a real MCP stdio server:

```bash
python -m decentralised_art_mcp.server stdio
```

List tools:

```bash
python -m decentralised_art_mcp.server list-tools
```

List resources:

```bash
python -m decentralised_art_mcp.server list-resources
```

Read a resource:

```bash
python -m decentralised_art_mcp.server read-resource core.primer
```

Invoke a tool:

```bash
python -m decentralised_art_mcp.server invoke core.connector_exists '{"name":"pitch"}'
```

Tool invocation returns a structured envelope:

```json
{"ok": true, "data": {...}}
```

or

```json
{ "ok": false, "error": { "code": "validation_error", "message": "..." } }
```

## Architecture

The HTTP client implements the decentralised.art protocol using contracts
generated from `api-spec`. The MCP server exposes those operations as `core.*` tools and a
core primer resource. Format-specific interpretation and general file-writing
belong in separate plugins.

## Architecture Boundary

- The official server exposes only `core.*` tools and the core primer resource.
- Generic structural helpers such as parent connector building remain in `core`.

## Pagination

The MCP transport supports paginated:

- `tools/list`
- `resources/list`

Pagination is implemented with opaque numeric cursors managed by the server.

## Notes For Maintainers

- Use the project-local `.venv` for work on this repository.
- Do not rely on the shared interpreter for long-term use.
- The current server uses the official MCP Python SDK low-level server so that exact JSON Schemas stay under our control.
