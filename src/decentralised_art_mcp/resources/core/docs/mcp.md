> Bundled platform snapshot. Retrieved 2026-10-07 from https://decentralised.art/mcp.
> Read core.getting-started for account onboarding in this MCP release.

# MCP

Connect your AI agent to decentralised.art. The MCP server gives Claude, Codex, Cursor and other MCP hosts tools to explore the network, create and simulate operations, publish them on chain and execute connectors.

## Overview

The **decentralised.art MCP server** connects AI agents to the network through the [Model Context Protocol](https://modelcontextprotocol.io/). Add it to an MCP host such as Claude Code, Claude Desktop, Codex, Cursor or VS Code, and your agent can work with the network directly:

-   find and read connectors, transformations, conditions, formats, accounts and new events;
-   create its own operations as drafts and simulate them for free;
-   publish them on chain from your account, within fee limits you set;
-   execute published connectors and keep verifiable results.

The server runs on your computer and talks to the public chain API at `https://api.decentralised.art/chain`. Your agent does not need to run inside this website: it works from any environment that can start the server. Reading, simulating and executing need no account; creating and publishing need a private key that stays on your machine.

The server's tools are format-agnostic: they handle values and structure, not what the values mean. Interpreting results as notes, images or motion is up to the agent and the Worlds it feeds. If you are writing code rather than working with an agent, use the [SDK](https://decentralised.art/sdk); both reach the same API.

Your agent can also read this documentation directly: [llms.txt](https://decentralised.art/llms.txt) lists every docs page in markdown (add `.md` to a page's address, as in [/mcp.md](https://decentralised.art/mcp.md)), and [llms-full.txt](https://decentralised.art/llms-full.txt) contains all of it in one file.

## Installation

The server is installed from source. You need **Python 3.10 or later** and `git`; `make` is used on macOS and Linux. The setup creates a private virtual environment inside the folder, so nothing is installed system-wide.

macOS / Linux:

```bash
git clone https://github.com/decentralised-art/mcp.git
cd mcp
make install   # creates .venv and installs the server
make smoke     # runs the test suite and a local tool call
```

Windows:

```bash
git clone https://github.com/decentralised-art/mcp.git
cd mcp
py scripts\bootstrap_venv.py
.venv\Scripts\python -m unittest discover -s tests
```

Keep the folder where it is: your MCP host starts the server from it. The examples below use `/path/to/mcp` for that folder; replace it with the full path on your machine.

## Connect your agent

Register the server with your host. Every host needs the same three things: the Python inside the folder's virtual environment, the arguments `-m decentralised_art_mcp.server stdio`, and the environment variables from [Configuration](https://decentralised.art/mcp#configuration).

Claude Code:

```bash
claude mcp add --transport stdio --scope user \
  --env API_BASE=https://api.decentralised.art/chain \
  --env DECENTRALISED_ART_ARTIFACT_ROOT=/path/to/mcp/decentralised-art-mcp-artifacts \
  --env PRIVATE_KEY=0xYourTestnetKey \
  decentralised-art -- /path/to/mcp/.venv/bin/python -m decentralised_art_mcp.server stdio

claude mcp list   # "decentralised-art" should be listed as connected
```

Claude Desktop:

```bash
# Requires uv (https://docs.astral.sh/uv/) on the machine running Claude Desktop.
cd /path/to/mcp
make mcpb   # writes dist/decentralised-art-mcp-<version>.mcpb

# Then double-click the .mcpb file, drag it into Claude Desktop, or install it from
# Claude Desktop's extension settings. It asks for the API base URL, an optional
# private key, the timeout and the artifact folder.
```

Codex:

```toml
# ~/.codex/config.toml
[mcp_servers.decentralised-art]
command = "/path/to/mcp/.venv/bin/python"
args = ["-m", "decentralised_art_mcp.server", "stdio"]

[mcp_servers.decentralised-art.env]
API_BASE = "https://api.decentralised.art/chain"
DECENTRALISED_ART_TIMEOUT = "15"
DECENTRALISED_ART_ARTIFACT_ROOT = "/path/to/mcp/decentralised-art-mcp-artifacts"
PRIVATE_KEY = "0xYourTestnetKey"   # optional
```

Cursor:

```json
{
  "mcpServers": {
    "decentralised-art": {
      "type": "stdio",
      "command": "/path/to/mcp/.venv/bin/python",
      "args": ["-m", "decentralised_art_mcp.server", "stdio"],
      "env": {
        "API_BASE": "https://api.decentralised.art/chain",
        "DECENTRALISED_ART_TIMEOUT": "15",
        "DECENTRALISED_ART_ARTIFACT_ROOT": "/path/to/mcp/decentralised-art-mcp-artifacts"
      }
    }
  }
}
```

VS Code:

```json
{
  "servers": {
    "decentralised-art": {
      "type": "stdio",
      "command": "/path/to/mcp/.venv/bin/python",
      "args": ["-m", "decentralised_art_mcp.server", "stdio"],
      "env": {
        "API_BASE": "https://api.decentralised.art/chain",
        "DECENTRALISED_ART_TIMEOUT": "15",
        "DECENTRALISED_ART_ARTIFACT_ROOT": "/path/to/mcp/decentralised-art-mcp-artifacts"
      }
    }
  }
}
```

Other hosts:

```json
{
  "command": "/path/to/mcp/.venv/bin/python",
  "args": ["-m", "decentralised_art_mcp.server", "stdio"],
  "cwd": "/path/to/mcp",
  "env": {
    "API_BASE": "https://api.decentralised.art/chain",
    "DECENTRALISED_ART_TIMEOUT": "15",
    "DECENTRALISED_ART_ARTIFACT_ROOT": "/path/to/mcp/decentralised-art-mcp-artifacts",
    "PRIVATE_KEY": "<optional>"
  }
}
```

Restart the host, or open a new session, after adding the server; hosts usually load MCP servers only at start-up. `PRIVATE_KEY` is optional: leave it out to use the server for reading, simulating and executing only.

### Sharing a project configuration

Claude Code can read servers from a `.mcp.json` file committed with a project. Never put a key in that file; reference an environment variable instead:

.mcp.json:

```json
{
  "mcpServers": {
    "decentralised-art": {
      "command": "/path/to/mcp/.venv/bin/python",
      "args": ["-m", "decentralised_art_mcp.server", "stdio"],
      "env": {
        "API_BASE": "https://api.decentralised.art/chain",
        "DECENTRALISED_ART_ARTIFACT_ROOT": "/path/to/mcp/decentralised-art-mcp-artifacts",
        "PRIVATE_KEY": "${PRIVATE_KEY}"
      }
    }
  }
}
```

## Check the connection

Ask your agent something that needs the network, for example:

-   *“Use the decentralised.art MCP to list the formats on the network.”*
-   *“Read the core.primer resource and summarise how execution works.”*

If the tools do not appear, check that the path to `.venv/bin/python` is absolute and that you restarted the host. To test the server on its own, open it in the [MCP Inspector](https://modelcontextprotocol.io/docs/tools/inspector):

Terminal:

```bash
npx @modelcontextprotocol/inspector \
  /path/to/mcp/.venv/bin/python -m decentralised_art_mcp.server stdio
```

## Working with your agent

A good session builds on what others have published rather than starting from nothing. The agent should show you what exists, explain it, and agree with you before it spends anything. A typical path:

1.  **Discover.** Browse the feed, formats and accounts; read the operations that look useful.
2.  **Understand.** Read connector graphs and run published connectors with `core.execute_connector` to see what they produce.
3.  **Compose.** Create your own transformations, conditions and connectors as drafts, reusing published ones by name.
4.  **Try.** Run the drafts with `core.simulate_connector`. This is free.
5.  **Publish.** When you are happy, publish dependencies first, then the connector that uses them, with explicit fee limits.
6.  **Run on chain.** Execute the published connector and keep the whole result, with its block, runner and registry, as the reference for what the network produced.

Drafts, simulation and publication follow the same rules as everywhere on the platform; see [SDK → Core concepts](https://decentralised.art/sdk) for transformations, conditions, dimensions and running instances.

## Example prompts

| You ask | The agent uses |
| --- | --- |
| “What has been published on decentralised.art recently? Explain each connector.” | `core.get_feed_page`, `core.get_connector` |
| “Run the pitch connector for 16 steps on chain and show me the values with the block.” | `core.execute_connector` |
| “Create a transformation shift\_up that adds its first argument, then a connector that uses add and shift\_up, and simulate 16 steps.” | `core.create_transformation`, `core.create_connector`, `core.simulate_connector` |
| “What would publishing shift\_up cost?” | `core.prepare_publication` |
| “Publish shift\_up with at most 50 gwei per gas and 0.005 ETH in total, recorded in publications/shift\_up.json.” | `core.publish_entity` |
| “Which connectors share pitch's format?” | `core.get_connector`, `core.get_format` |

## Configuration

The server reads these environment variables when it starts:

| Variable | Default | Description |
| --- | --- | --- |
| `API_BASE` | `https://api.decentralised.art/chain` | The chain API to use. |
| `PRIVATE_KEY` | none | Ethereum key for logging in, creating drafts and publishing. Not needed for reading, simulating or executing. |
| `DECENTRALISED_ART_TIMEOUT` | `15` | Seconds per API request, between 0.1 and 120. |
| `DECENTRALISED_ART_ARTIFACT_ROOT` | `decentralised-art-mcp-artifacts` | Folder for publication records. Use an absolute path; a relative one depends on where the host starts the server. |

Tools that call the API also accept `api_base` and `timeout` arguments to override these for a single call, and authenticated tools accept `private_key`. Prefer the environment variable for keys, so they never appear in the conversation.

The server logs in to the chain API by signing the issued sign-in message with your key. That login is separate from signing in to this website.

## Publishing safely

`core.publish_entity` is the only tool that spends anything. It publishes one draft under your address and pays the gas from your account. It is built so that an agent cannot overspend or publish twice by accident:

-   **Fee limits are required.** `max_fee_per_gas` caps the price per unit of gas and `max_total_fee` caps the whole transaction (gas limit × max fee), both in wei. The tool refuses to sign anything above them.
-   **Every publication has a record.** `record_path` is a file inside `DECENTRALISED_ART_ARTIFACT_ROOT`. The transaction is written to it before it is sent. Calling the tool again with the same record only confirms that transaction; it never sends another.
-   **Only zero-value transactions to the expected chain.** The tool checks the owner, the chain (`chain_id`, Sepolia `11155111` by default) and that no value is transferred before it signs.
-   **Your key never leaves your machine.** The transaction is signed locally and the API relays it; no RPC endpoint of your own is needed.

Tool call:

```json
{
  "name": "core.publish_entity",
  "arguments": {
    "kind": "transformation",
    "name": "shift_up",
    "max_fee_per_gas": 50000000000,
    "max_total_fee": 5000000000000000,
    "record_path": "publications/shift_up.json"
  }
}
```

For reference: 50 gwei is `50000000000` wei and 0.005 ETH is `5000000000000000` wei.

### Rules for agents

-   **Inspect first.** Use `core.prepare_publication` to see the fees, and confirm them with the person before publishing.
-   **Dependencies first.** Transformations, conditions and child connectors must be published before the connector that uses them. Otherwise the call fails and lists them under `missing` or `mismatched`.
-   **One publication at a time per owner.** Publications from one address share a nonce, so separate sessions must not publish for the same key in parallel.
-   **Pending is not failure.** If a publication is still pending or its outcome is unknown, the tool returns `publication_pending` with the transaction hash. Confirm it with the same record, or with `core.confirm_publication`, before doing anything else.
-   **Mined is not instantly executable.** Execution reads the chain at a safe block, so a freshly mined connector can take a short while to become available. Retry the execution; do not republish, and never present a simulation as an on-chain result.

## Results and errors

Every tool returns the same envelope, as structured content and as JSON text. A successful call carries `data`:

Tool call:

```json
{
  "name": "core.execute_connector",
  "arguments": { "connector_name": "pitch", "particles_count": 4 }
}
```

Result:

```json
{
  "ok": true,
  "data": {
    "block_number": 11825265,
    "block_hash": "0xfa8ee7fe85e17439d69d98aef0418556a9d9a0d5794d5568fd32de300853acc5",
    "runner": "0xe0e70f522b64a6c8d2301697cd7133be33eae77f",
    "registry": "0x7648cc2a6db6152a60615ebbba4b9e1f900e26fa",
    "particles": [{ "path": "/pitch:0", "data": [0, 1, 2, 3] }],
    "execution_mode": "chain"
  }
}
```

A failed call is marked as an error and carries `error` instead:

Error:

```json
{
  "ok": false,
  "error": {
    "code": "validation_error",
    "message": "params.particles_count is required",
    "details": { "path": "params.particles_count", "required": true }
  }
}
```

| Code | Meaning |
| --- | --- |
| `validation_error` | Invalid or missing arguments, or a fee or chain check refused to sign. |
| `auth_configuration_error` | The tool needs a key and none, or an invalid one, is configured. |
| `http_error` | The API rejected the request. `details.status_code` holds the status, and publication conflicts list `missing` and `mismatched` dependencies. |
| `publication_pending` | A publication is pending or its outcome is unknown. `details` holds the transaction to confirm. |
| `tool_not_found`, `resource_not_found` | Unknown tool or resource name. |
| `internal_tool_error` | Unexpected failure inside the server. |

## Keys and security

-   Use a **dedicated key** for your agent, funded only with what it should be able to spend. During testing, publications use Sepolia test ETH.
-   Give the key to the server through `PRIVATE_KEY` or the host's secret settings, not in a prompt. Keep it out of files you commit or share.
-   Leave the key out entirely if the agent only needs to explore, simulate and execute.
-   The server never sends your key anywhere. It signs the sign-in message and publication transactions locally.

## Tools

All tools live in the `core` namespace. Every tool that calls the API also accepts `api_base` and `timeout`; tools marked **Login** accept `private_key` and need a key from it or from the environment.

### Discover and read

| Tool and arguments | Description |
| --- | --- |
| `core.get_connector` name | A connector's definition, owner, address and format hash. |
| `core.get_transformation` name | Name, args\_count, owner and address. |
| `core.get_condition` name | Name, args\_count, owner and address. |
| `core.connector_exists` name | Whether a connector exists. |
| `core.transformation_exists` name | Whether a transformation exists. |
| `core.condition_exists` name | Whether a condition exists. |
| `core.list_formats` limit, after | Format hashes known to the network. |
| `core.get_format` format\_hash, limit, after | Connectors and scalar labels that share one format. |
| `core.get_account` address, limit, after\_connectors, after\_transformations, after\_conditions | What an address has published. |
| `core.get_feed_page` limit, before, type, include\_unfinalized | Newest-first page of chain events. |
| `core.get_feed_stream_replay` since\_seq, limit | A bounded replay of the live event stream, for catching up. |
| `core.get_nonce` address | The login nonce and sign-in message for an address. |

### Create drafts

| Tool and arguments | Description |
| --- | --- |
| `core.create_transformation` payload | Login Create a transformation draft: name and Solidity body. No gas. |
| `core.create_condition` payload | Login Create a condition draft: name and Solidity body. No gas. |
| `core.create_connector` payload | Login Create a connector draft from dimensions, an optional condition and running instances. No gas. |
| `core.build_parent_connector` name, child\_names | Build (but not create) a connector payload with one dimension per child connector. |

### Run

| Tool and arguments | Description |
| --- | --- |
| `core.simulate_connector` connector\_name, particles\_count, dynamic\_ri | Run drafts in the server's local EVM. Returns particles with execution\_mode "simulation". |
| `core.execute_connector` connector\_name, particles\_count, dynamic\_ri | Run a published connector on chain at a pinned block. Returns particles with block\_number, block\_hash, runner, registry and execution\_mode "chain". |

### Publish

| Tool and arguments | Description |
| --- | --- |
| `core.prepare_publication` kind, name | Login Show the transaction and fees a publication would need. Signs and sends nothing. |
| `core.publish_entity` kind, name, max\_fee\_per\_gas, max\_total\_fee, record\_path, chain\_id, max\_confirm\_attempts | Login Sign locally, relay once and confirm. Spends the owner's gas. See Publishing safely. |
| `core.confirm_publication` kind, name, content\_hash, tx\_hash | Login Check the receipt of a publication already sent. Never sends another. |

### Helpers

| Tool and arguments | Description |
| --- | --- |
| `core.ensure_preflight` required\_connectors, preferred\_transformation\_pairs | Login Log in, check that the given connectors exist, and pick an available add/subtract transformation pair. |
| `core.resolve_transformation_pair` pairs | Pick the first add/subtract transformation pair that exists on the network. |

Draft payloads use the same fields as the API: see [SDK → Creating operations](https://decentralised.art/sdk). Running-instance overrides (`dynamic_ri`) and step counts (1–65536) work as described in [SDK → Executing on chain](https://decentralised.art/sdk).

## Resources

| Resource | Description |
| --- | --- |
| `core.primer` `decentralised-art://resource/core.primer` | A short primer for agents: connectors, dimensions, running instances, the draft → simulate → publish → execute lifecycle, and the publication rules above. Ask your agent to read it at the start of a session. |

## Command line

The same tools can be called without an MCP host, which is useful for scripts and for checking a setup:

Terminal:

```bash
cd /path/to/mcp
source .venv/bin/activate

decentralised-art-mcp list-tools                         # every tool with its input schema
decentralised-art-mcp list-resources
decentralised-art-mcp read-resource core.primer
decentralised-art-mcp invoke core.get_connector '{"name": "pitch"}'
decentralised-art-mcp invoke core.execute_connector '{"connector_name": "pitch", "particles_count": 4}'
```

The repository's `make` targets wrap the common tasks: `make install`, `make smoke`, `make test`, `make stdio` (run the server), `make mcpb` (Claude Desktop bundle), `make list-tools` and `make list-resources`.

## Versions and source

-   Source and issues: [github.com/decentralised-art/mcp](https://github.com/decentralised-art/mcp). Update with `git pull` followed by `make install`, then restart your host. When upgrading from a version before 0.2.0, follow the upgrade notes in the README: some names changed.
-   Requests and responses are checked against the OpenAPI contracts in [api-spec](https://github.com/decentralised-art/api-spec), packaged with the server.
-   Related: the [SDK](https://decentralised.art/sdk) for code, the [API reference](https://decentralised.art/api-reference) for endpoints, and [API status](https://decentralised.art/api-status) for the live services.

Source: https://decentralised.art/mcp
