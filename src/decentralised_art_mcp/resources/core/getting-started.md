# decentralised.art: getting started

This guide ships with the MCP. Read it before creating operations. Use
`core.documentation` to read this guide or any bundled platform page without a
browser, network access or signing account. The same pages are MCP resources.
Before designing operations, read topic `llms-full` (resource
`core.docs.llms-full`) for the complete platform documentation, system concepts
and good practices. Follow `next_start_line` until null for a complete tool read;
the first page alone is not the whole document.

## Choose the account path

Reading the network, simulating drafts and executing published connectors need
no account. Creating drafts needs a signing identity, but it does **not** need
funds or gas. Publishing is a separate, owner-paid step.

For user-requested work under a **fresh identity**, do not demand an existing
private key from the user. Call:

```json
{"name":"core.create_account","arguments":{"account_id":"draft_owner"}}
```

The server generates a fresh Ethereum key on its own machine, retains it in
owner-only local storage, and returns only `account_id`, `address` and `created`.
Pass that `account_id` to draft creation, preflight and publication tools:

```json
{
  "name": "core.create_connector",
  "arguments": {
    "account_id": "draft_owner",
    "payload": {
      "name": "my_unique_selection",
      "dimensions": [{"composite":"pitch","transformations":[{"name":"add","args":[2]}]}]
    }
  }
}
```

Inspect referenced operations first, choose a globally unique operation name,
and then simulate the saved draft with `core.simulate_connector`.

Choose a stable account ID: start with a letter, use letters, digits and
underscores, and keep it at most 64 characters. Retry `core.create_account` with
the **same ID** after an interrupted call; it returns the same identity without
rotating its key. Reuse that ID for every operation owned by this identity.
The ID is local to this MCP server's account store, not a platform username.

For an **existing owner**, reuse its local account ID or configure its existing
key through the host's secret settings / `PRIVATE_KEY` environment variable.
Never request, print or paste a private key in chat. Do not use a fresh account
to publish someone else's draft: ownership remains with its original signer.
An explicit `account_id` selects that local identity even if `PRIVATE_KEY` is set;
do not pass both `account_id` and a `private_key` tool argument.

## Storage and account lifetime

`DECENTRALISED_ART_ACCOUNT_ROOT` can select a persistent absolute directory. Its
default is `~/.decentralised-art-mcp/accounts`, outside the installed package, so
upgrading the MCP does not discard keys. Store directories with permissions
0700 and key files with 0600; the server enforces ownership and these restrictions.
Local account generation currently requires a POSIX host (macOS/Linux). On
other platforms, configure an existing key through the host's secret settings.

Keys are stored locally in plaintext behind those filesystem permissions. Keep
the directory private, outside source control, and back it up locally if you
need to retain control of its operations. No tool returns or exports its keys.
Losing a key means losing control of its owner's drafts and publications. The
fresh identity has no automatic expiration: using it temporarily does not
remove its platform data or expire its Ethereum address. Account creation makes
no API call and does not create a website profile. Website profiles are created
separately on first Services API sign-in; draft tools authenticate to the Chain API.

## Publication

Fresh accounts start unfunded. Draft creation and simulation spend no gas.
To publish, fund the **same owner address** with Sepolia test ETH, prepare the
publication, review its fees and get the user's authorization before signing.
Specify `max_fee_per_gas`, `max_total_fee` and a persistent publication record.
Publish dependencies first, serially for each owner. Confirm a pending
transaction instead of broadcasting another. Read `core.primer` for the complete
publication and execution lifecycle.

## Documentation topics

`core.documentation` defaults to `getting-started`. Pass `topic` to select:

| Topic | MCP resource | Contents |
| --- | --- | --- |
| getting-started | core.getting-started | Current MCP account onboarding |
| primer | core.primer | Protocol concepts, lifecycle and provenance |
| llms-full | core.docs.llms-full | Complete unabridged platform documentation |
| tutorial | core.docs.tutorial | Platform tutorial |
| mcp | core.docs.mcp | Platform installation and configuration guide |
| sdk | core.docs.sdk | JavaScript and Python SDK guide |
| api-reference | core.docs.api-reference | Chain and services API reference |
| about | core.docs.about | Platform overview |
| roadmap | core.docs.roadmap | Platform roadmap |

Resource URIs use `decentralised-art://resource/` followed by the resource name.
Tools-only hosts can read the identical text through `core.documentation`.
Long documents return `next_start_line`; continue with that line and the same
topic. `max_lines` defaults to 200 and is capped at 300.

The complete `llms-full.txt` is bundled verbatim, including its introduction and
every page; its provenance and checksum are stored separately. Individual
platform pages are bundled snapshots with source URLs and retrieval dates.
They may describe an earlier MCP release; this getting-started guide describes
the account tools in the installed server. Use https://decentralised.art/llms.txt
for live documentation and refresh bundled snapshots when preparing a release.
