> Bundled platform snapshot. Retrieved 2026-10-07 from https://decentralised.art/sdk.
> Read core.getting-started for account onboarding in this MCP release.

# SDK

Official JavaScript/TypeScript and Python SDKs for decentralised.art: read the network, create and simulate operations, publish them on chain, execute connectors, and build Worlds.

## Overview

The decentralised.art SDK is a typed client for the chain API at `https://api.decentralised.art/chain`. It comes in two languages with the same capabilities:

-   **JavaScript / TypeScript** (package `decentralised-art`), for browsers, Node.js and other modern runtimes. It also contains the [World runtime and host](https://decentralised.art/sdk#worlds).
-   **Python** (`decentralised-art`, imported as `decentralised_art`), for scripts, notebooks, services and agents.

With it you can:

-   read connectors, transformations, conditions, formats, accounts and the event feed;
-   create your own operations as drafts and simulate them for free;
-   publish them on chain from your own wallet;
-   execute published connectors and get verifiable results;
-   build Worlds that interpret those results inside the platform.

Both clients are generated from the platform's OpenAPI specification, so request and response types match the API exactly. Agents can also use the [MCP server](https://decentralised.art/mcp), which offers the same operations as tools.

The SDK covers the **chain API**. Profiles, follows and World uploads belong to the separate services API, which uses Sign-In with Ethereum sessions; the SDK does not wrap it.

## Installation

The SDK is distributed as GitHub release assets. JavaScript needs a runtime with `fetch` (modern browsers, Node.js 18 or later). Python needs version 3.9 or later.

JavaScript:

```bash
npm install "https://github.com/decentralised-art/sdk/releases/latest/download/decentralised-art-js-sdk.tgz"

# Optional: wallet signing for login and publication
npm install ethers
```

Python:

```bash
pip install "decentralised-art @ https://github.com/decentralised-art/sdk/releases/latest/download/decentralised-art-python-sdk.tar.gz"
```

For production, pin a release so installs are reproducible. Replace `vX.Y.Z` with a version from the [release list](https://github.com/decentralised-art/sdk/releases):

JavaScript:

```bash
npm install "https://github.com/decentralised-art/sdk/releases/download/vX.Y.Z/decentralised-art-js-sdk.tgz"
```

Python:

```bash
pip install "decentralised-art @ https://github.com/decentralised-art/sdk/releases/download/vX.Y.Z/decentralised-art-python-sdk.tar.gz"
```

The Python package already depends on `eth-account` for signing. In JavaScript, bring any wallet library; the examples use [ethers](https://docs.ethers.org/v6/) v6.

## Quick start

Reading and executing need no account. This reads the published `pitch` connector and runs it on chain for eight steps:

JavaScript:

```ts
import { DecentralisedArtClient } from "decentralised-art";

const sdk = new DecentralisedArtClient(); // https://api.decentralised.art/chain

// Read a published connector.
const connector = await sdk.connectorGet("pitch");
console.log(connector.dimensions, connector.format_hash);

// Run it on chain. No login and no gas.
const result = await sdk.execute("pitch", 8);
console.log(result.particles);
// [{ path: "/pitch:0", data: [0, 1, 2, 3, 4, 5, 6, 7] }]
```

Python:

```python
import decentralised_art

with decentralised_art.Client() as sdk:  # https://api.decentralised.art/chain
    # Read a published connector.
    connector = sdk.connector_get("pitch")
    print(connector.dimensions, connector.format_hash)

    # Run it on chain. No login and no gas.
    result = sdk.execute("pitch", 8)
    print(result.particles[0].path, result.particles[0].data)
    # /pitch:0 [0, 1, 2, 3, 4, 5, 6, 7]
```

Every code sample on this page has a JavaScript and a Python version. The tab you choose is remembered across the page.

## Core concepts

For the ideas behind the platform, see [About](https://decentralised.art/about). This is what they mean for the SDK.

### Transformations

A transformation is a small Solidity function that derives the next value from the current one. You write only its body. It receives `x` (a `uint32`) and `args` (a `uint32[]`) and returns a `uint32`. Its number of arguments, `args_count`, is derived from the highest `args[i]` it uses.

### Conditions

A condition is a Solidity function body that receives `args` (an `int32[]`) and returns a `bool`. It is checked every time the connector it guards runs. When it returns `false`, the run stops with `ConditionNotMet`.

### Connectors and dimensions

A connector is the runnable unit. It has one or more ordered **dimensions**.

-   Each dimension has an ordered list of transformation calls (a name plus its arguments). Applied step by step, they generate that dimension's space of values.
-   A dimension can point to another connector, its `composite`. The dimension's values are then passed to that connector as indexes, so it reads its own space at exactly those points. This is how connected connectors narrow a space down.
-   A dimension without a composite is an open slot. A parent connector can fill open slots of its composites with `bindings` (slot id to connector name).
-   A connector can be guarded by one condition, with its own arguments.

### Running instances

A running instance controls where generation starts on a branch: `start_point` is the first index and `transformation_shift` offsets which transformation is applied first. Positions are numbered depth-first: 0 is the connector itself, then each dimension in order, with a composite's dimensions numbered right after the dimension that leads to it.

A connector can fix running instances when it is created (`static_ri`), and a run can set others (`dynamic_ri`). A run cannot override a position the connector has already fixed; that run fails.

### Particles and paths

A run returns one stream of values per output path, for example `{ path: "/pitch:0", data: [0, 1, 2, …] }`. The path names the connector and dimension that produced it; nested connectors extend it, as in `/phrase:0/pitch:0`. What the numbers mean (a pitch, a time, a colour, a speed) is up to the World that interprets them.

### Formats

Every connector has a `format_hash` describing the shape of its output. Connectors with the same format produce compatible streams, so a World that accepts one can accept the others.

### Names, drafts and published operations

Names are global. They start with a letter or underscore, contain only letters, digits and underscores, and are at most 128 characters long. A created operation cannot be changed or overwritten: create a new name for a new version. A draft reports `address` `"0x0"`; a published operation reports its contract address.

## From draft to the network

Operations move through four distinct steps. Each one is its own call.

| Step | Methods | Login | Gas | Where it runs |
| --- | --- | --- | --- | --- |
| Create | `transformationPost`, `conditionPost`, `connectorPost` | Yes | No | Stored on the server as your draft |
| Simulate | `simulate` | No | No | The server's local EVM |
| Publish | `publish`, or `publishPrepare` + `publishConfirm` | Yes, as the owner | Yes, paid by the owner | Ethereum (Sepolia during testing) |
| Execute | `execute` | No | No | A read-only call to the chain at a pinned block |

Publishing is the only step that costs anything, and the cost is network gas paid from your own wallet. The server never holds your key.

## Configuration

Both clients default to `https://api.decentralised.art/chain`. Set the `DECENTRALISED_ART_API_BASE` environment variable, or pass a base URL, to target another deployment, such as a local chain backend.

JavaScript:

```ts
import { DecentralisedArtClient } from "decentralised-art";

const sdk = new DecentralisedArtClient({
  baseUrl: "https://api.decentralised.art/chain", // or DECENTRALISED_ART_API_BASE in Node
  accessToken: savedToken ?? null,                 // reuse a token from an earlier login
  fetch: globalThis.fetch,                          // custom runtimes, tests, instrumentation
});
```

Python:

```python
import decentralised_art

sdk = decentralised_art.Client(
    base_url="https://api.decentralised.art/chain",  # or DECENTRALISED_ART_API_BASE
    access_token=None,   # reuse a token from an earlier login
    timeout=15.0,        # seconds per request
    verify_ssl=True,
)
...
sdk.close()  # or use the client as a context manager: with Client() as sdk: ...
```

## Authentication

Reading, simulating and executing need no login. Creating and publishing need a bearer token, which you get by signing a one-time EIP-4361 message with your Ethereum key:

1.  The client asks for a nonce and sign-in message for your address.
2.  You sign the exact returned `message` using EIP-191 personal\_sign.
3.  The client submits your address, the issued nonce and the signature.
4.  The server returns an access token, which the client stores and sends from then on.

Browser clients pass `{ origin: window.location.origin }` to `getNonce` or `loginWithWallet`, so the message names the site asking for the signature. The challenge expires after five minutes and can be used once.

JavaScript:

```ts
import { Wallet } from "ethers";

// Server or script: a local key also becomes the default signer for publish().
const wallet = new Wallet(process.env.OWNER_KEY!);
await sdk.loginWithWallet(wallet);

// Browser: any ethers signer works for login.
// const signer = await new BrowserProvider(window.ethereum).getSigner();
// await sdk.loginWithWallet(signer, { origin: window.location.origin });

console.log(sdk.accessToken);
```

Python:

```python
import os

from eth_account import Account

# The account also becomes the default signer for publish().
account = Account.from_key(os.environ["OWNER_KEY"])
sdk.login_with_account(account)

print(sdk.access_token)
```

If you sign somewhere else (a hardware wallet, another service), submit the signature yourself:

JavaScript:

```ts
const { nonce, message } = await sdk.getNonce(address);
// Browser clients pass { origin: window.location.origin } to getNonce.
const signature = await signMessageSomehow(message); // EIP-191 personal_sign

await sdk.loginWithSignature(address, nonce, signature);
```

Python:

```python
challenge = sdk.get_nonce(address)
signature = sign_message_somehow(challenge.message)  # EIP-191 personal_sign

sdk.login_with_signature(address, challenge.nonce, signature)
```

**Access tokens are short-lived**, currently five minutes. When a protected call returns `401`, log in again. Your drafts stay on the server; they belong to your address, not to the token.

The address you log in with owns everything you create, and only that address can publish it.

## Reading the network

Every operation can be read by name. Lookups return both published operations and drafts; check `address` to tell them apart. Transformation and condition lookups return their argument count and deployed `runtime_code`, which can be `null` while bytecode is unavailable. They never return Solidity source.

JavaScript:

```ts
// Existence checks return false on 404 instead of throwing.
if (await sdk.connectorExists("pitch")) {
  const connector = await sdk.connectorGet("pitch");
  console.log(connector.owner, connector.address); // address is "0x0" for a local draft
}

const add = await sdk.transformationGet("add");
console.log(add.args_count); // 1

// Who has published what.
const { accounts } = await sdk.listAccounts({ limit: 50 });
const owned = await sdk.accountInfo(accounts[0]);

// Connectors that share an output shape.
const { formats } = await sdk.listFormats();
const format = await sdk.formatInfo(formats[0]);
console.log(format.connectors, format.scalars);
```

Python:

```python
# Existence checks return False on 404 instead of raising.
if sdk.connector_exists("pitch"):
    connector = sdk.connector_get("pitch")
    print(connector.owner, connector.address)  # address is "0x0" for a local draft

add = sdk.transformation_get("add")
print(add.args_count)  # 1

# Who has published what.
accounts = sdk.list_accounts(limit=50).accounts
owned = sdk.account_info(accounts[0])

# Connectors that share an output shape.
formats = sdk.list_formats().formats
fmt = sdk.format_info(formats[0])
print(fmt.connectors, fmt.scalars)
```

### Pagination

List methods use cursors. Pass the `next_after` value of one page as `after` for the next, while `has_more` is true. Page sizes default to 50.

JavaScript:

```ts
let after: string | undefined;
do {
  const page = await sdk.listFormats({ limit: 100, after });
  handle(page.formats);
  after = page.cursor.has_more ? (page.cursor.next_after ?? undefined) : undefined;
} while (after);
```

Python:

```python
after = None
while True:
    page = sdk.list_formats(limit=100, after=after)
    handle(page.formats)
    if not page.cursor.has_more:
        break
    after = page.cursor.next_after
```

## Feed and live updates

The feed lists chain events newest first: `connector_added`, `transformation_added` and `condition_added`. Each item carries a compact payload (`type`, `name`, `owner`); read the full definition through the matching lookup.

Items move through the statuses `observed`, `safe` and `finalized` as the chain confirms them, or become `removed` after a reorganisation. By default the feed includes items that are not finalized yet; ask for finalized items only when you need settled history.

JavaScript:

```ts
// Newest first. includeUnfinalized: false returns finalized items only.
const page = await sdk.feed({ limit: 20, type: "connector_added", includeUnfinalized: false });
for (const item of page.items) {
  console.log(item.status, item.payload.type, item.payload.name, item.payload.owner);
}

// Older items: pass the cursor back.
const older = await sdk.feed({ limit: 20, before: page.cursor.next_before ?? undefined });
```

Python:

```python
# Newest first. include_unfinalized=False returns finalized items only.
page = sdk.feed(limit=20, event_type="connector_added", include_unfinalized=False)
for item in page.items:
    print(item.status, item.payload.name, item.payload.owner)

# Older items: pass the cursor back.
older = sdk.feed(limit=20, before=page.cursor.next_before)
```

### Live stream

`feedStream` opens a Server-Sent Events stream. It first replays events after `since_seq` (up to `limit`), sends a `stream_meta` event, then delivers new events as they happen. Remember the last `stream_seq` you processed and pass it back when you reconnect.

JavaScript:

```ts
const response = await sdk.feedStream({ sinceSeq: 0 });
const reader = response.body!.pipeThrough(new TextDecoderStream()).getReader();

let buffer = "";
for (;;) {
  const { value, done } = await reader.read();
  if (done) break;
  buffer += value;
  const frames = buffer.split("\n\n");
  buffer = frames.pop() ?? "";
  for (const frame of frames) {
    const data = frame.split("\n").find((line) => line.startsWith("data: "));
    if (data && !frame.includes("event: stream_meta")) {
      const delta = JSON.parse(data.slice(6));
      console.log(delta.stream_seq, delta.event_type, delta.payload.name);
    }
  }
}
```

Python:

```python
import json

with sdk.feed_stream(since_seq=0) as response:
    event = None
    for line in response.iter_lines():
        if line.startswith("event: "):
            event = line[7:]
        elif line.startswith("data: ") and event != "stream_meta":
            delta = json.loads(line[6:])
            print(delta["stream_seq"], delta["event_type"], delta["payload"]["name"])
        elif line == "":
            event = None
```

## Creating operations

Creating an operation stores it on the server as your draft. Nothing is sent to the chain and it costs nothing. Creation fails with `409` if the name is already taken on chain.

### Transformations

JavaScript:

```ts
// The body of: function run(uint32 x, uint32[] args) returns (uint32)
await sdk.transformationPost({
  name: "shift_up",
  sol_src: "return x + args[0];",
});

const created = await sdk.transformationGet("shift_up");
console.log(created.args_count, created.address); // 1 "0x0"
```

Python:

```python
# The body of: function run(uint32 x, uint32[] args) returns (uint32)
sdk.transformation_post({
    "name": "shift_up",
    "sol_src": "return x + args[0];",
})

created = sdk.transformation_get("shift_up")
print(created.args_count, created.address)  # 1 0x0
```

### Conditions

JavaScript:

```ts
// The body of: function check(int32[] args) view returns (bool)
await sdk.conditionPost({
  name: "positive_only",
  sol_src: "return args[0] > 0;",
});
```

Python:

```python
# The body of: function check(int32[] args) view returns (bool)
sdk.condition_post({
    "name": "positive_only",
    "sol_src": "return args[0] > 0;",
})
```

### Connectors

A connector refers to transformations and conditions by name. They can be your drafts or published operations from anyone.

JavaScript:

```ts
await sdk.connectorPost({
  name: "rising_line",
  dimensions: [
    {
      // Applied in order on this dimension.
      transformations: [
        { name: "add", args: [1] },
        { name: "shift_up", args: [2] },
      ],
    },
  ],
  // Optional gate, checked whenever the connector runs.
  condition_name: "positive_only",
  condition_args: [1],
});
```

Python:

```python
sdk.connector_post({
    "name": "rising_line",
    "dimensions": [
        {
            # Applied in order on this dimension.
            "transformations": [
                {"name": "add", "args": [1]},
                {"name": "shift_up", "args": [2]},
            ],
        },
    ],
    # Optional gate, checked whenever the connector runs.
    "condition_name": "positive_only",
    "condition_args": [1],
})
```

To build on another connector, point a dimension at it as a `composite`. A connector can also fix running instances with `static_ri`:

JavaScript:

```ts
await sdk.connectorPost({
  name: "phrase",
  dimensions: [
    // This dimension builds on the published "pitch" connector.
    { composite: "pitch", transformations: [{ name: "add", args: [1] }] },
    { transformations: [{ name: "add", args: [2] }] },
  ],
  // Fixed running instance for position 0 (the connector itself).
  static_ri: { "0": { start_point: 60, transformation_shift: 0 } },
});
```

Python:

```python
sdk.connector_post({
    "name": "phrase",
    "dimensions": [
        # This dimension builds on the published "pitch" connector.
        {"composite": "pitch", "transformations": [{"name": "add", "args": [1]}]},
        {"transformations": [{"name": "add", "args": [2]}]},
    ],
    # Fixed running instance for position 0 (the connector itself).
    "static_ri": {"0": {"start_point": 60, "transformation_shift": 0}},
})
```

| Field | Description |
| --- | --- |
| `name` | Required. Unique name for the connector. |
| `dimensions` | Required, at least one. Each has `transformations` (ordered `{ name, args }` calls), and optionally `composite` and `bindings`. |
| `condition_name` | Optional. A condition checked on every run. Empty or omitted means none. |
| `condition_args` | Optional. Integer arguments for the condition. |
| `static_ri` | Optional. Fixed running instances keyed by position (`"0"`, `"1"`, …). |

## Simulating

Simulation runs a connector in the server's local EVM, so you can try drafts before paying for anything. It also uses published operations your drafts depend on. It takes the same arguments as `execute` and returns the output streams.

JavaScript:

```ts
// Runs your drafts, and any published operations they use, in the server's local EVM.
const streams = await sdk.simulate("rising_line", 16);
for (const { path, data } of streams) console.log(path, data);
```

Python:

```python
# Runs your drafts, and any published operations they use, in the server's local EVM.
streams = sdk.simulate("rising_line", 16)
for stream in streams:
    print(stream.path, stream.data)
```

Simulation results have no chain provenance: they show what a connector would produce, not what the network has recorded.

## Publishing

Publishing records a draft on chain under your address. You pay the gas from your own wallet; the transaction never transfers any other value. The server rebuilds exactly the definition it stored when you created the draft, so the published operation matches what you simulated.

### Publish with a local key

`publish` does everything in one call and needs no chain RPC endpoint: it prepares the transaction, signs it locally with the wallet or account you logged in with, lets the server broadcast it, and confirms it until it is mined. If the registry already holds exactly this operation, it returns without signing anything.

JavaScript:

```ts
import { Wallet } from "ethers";

const wallet = new Wallet(process.env.OWNER_KEY!); // no provider needed
await sdk.loginWithWallet(wallet);

// Dependencies first, one at a time, then the connector that uses them.
await sdk.publish("transformation", "shift_up", { maxFeePerGas: 50_000_000_000n });
await sdk.publish("condition", "positive_only", { maxFeePerGas: 50_000_000_000n });
const result = await sdk.publish("connector", "rising_line", {
  maxFeePerGas: 50_000_000_000n, // refuse to sign above 50 gwei
  chainId: 11155111,             // refuse to sign for any other chain (Sepolia)
});

console.log(result.status); // "mined", or "published" if it already was
```

Python:

```python
import os

from eth_account import Account

account = Account.from_key(os.environ["OWNER_KEY"])
sdk.login_with_account(account)

# Dependencies first, one at a time, then the connector that uses them.
sdk.publish("transformation", "shift_up", max_fee_per_gas=50_000_000_000)
sdk.publish("condition", "positive_only", max_fee_per_gas=50_000_000_000)
result = sdk.publish(
    "connector",
    "rising_line",
    max_fee_per_gas=50_000_000_000,  # refuse to sign above 50 gwei
    chain_id=11155111,               # refuse to sign for any other chain (Sepolia)
)

print(type(result).__name__)  # ConfirmResponse, or AlreadyPublished if it already was
```

### Publish from a browser wallet

Browser wallets such as MetaMask send transactions themselves and cannot sign offline, so `publish` stops with an explanation before anything is signed or sent. Use the two-step flow instead: prepare the transaction, let the wallet send it, then confirm it.

JavaScript:

```ts
const prepared = await sdk.publishPrepare("transformation", "shift_up");

if (prepared.status === "prepared") {
  // { from, to, data, chainId, gas } as hex quantities: the params of eth_sendTransaction.
  const txHash = (await window.ethereum.request({
    method: "eth_sendTransaction",
    params: [prepared.transaction],
  })) as string;

  // Store txHash now. If the page reloads, confirm again with the same hash.
  const request = { name: "shift_up", content_hash: prepared.content_hash, tx_hash: txHash };
  let confirmed = await sdk.publishConfirm("transformation", request);
  while (confirmed.status === "pending") {
    await new Promise((resolve) => setTimeout(resolve, 3000));
    confirmed = await sdk.publishConfirm("transformation", request);
  }
  console.log(confirmed.status); // "mined"
}
// prepared.status === "published": the registry already holds this exact entity.
```

### Step by step

The steps behind `publish` are available separately, for custom signers. With `relay`, the prepared answer also contains the account nonce and fees needed to sign offline.

JavaScript:

```ts
const prepared = await sdk.publishPrepare("transformation", "shift_up", { relay: true });
if (prepared.status === "prepared" && prepared.signing) {
  // Sign { ...prepared.transaction, ...prepared.signing } offline (eth_signTransaction).
  const raw_tx = await signOffline({ ...prepared.transaction, ...prepared.signing });
  const { tx_hash } = await sdk.publishSend("transformation", {
    name: "shift_up",
    content_hash: prepared.content_hash,
    raw_tx,
  });
  await sdk.publishConfirm("transformation", {
    name: "shift_up",
    content_hash: prepared.content_hash,
    tx_hash,
  });
}
```

Python:

```python
from decentralised_art.client import PreparedPublication

prepared = sdk.publish_prepare("transformation", "shift_up", relay=True)
if isinstance(prepared, PreparedPublication):
    raw_tx = sign_offline(prepared.transaction, prepared.signing)  # 0x02… signed transaction
    sent = sdk.publish_send("transformation", "shift_up", prepared.content_hash, raw_tx)
    sdk.publish_confirm("transformation", "shift_up", prepared.content_hash, sent.tx_hash)
```

### Rules to know

-   **Dependencies first.** A connector can only be published once every transformation, condition and connector it uses is published with the same definition. Otherwise preparing fails with `409` and lists them under `missing` and `mismatched`. Dependencies are never published automatically.
-   **One at a time per owner.** Publications from one address share a nonce. Publish serially, and resolve a pending publication before preparing the next.
-   **Keep the transaction hash.** If a confirmation is interrupted, confirm again with the same hash. Do not prepare and send a new transaction.
-   **Mined is not instantly executable.** Execution reads the chain at a safe block, so a just-mined operation can take a short while to become available. Retry the execution later instead of publishing again.
-   **Fee and chain limits.** `maxFeePerGas` and `chainId` make `publish` refuse to sign anything more expensive, or for another chain. During testing, publications go to Sepolia (chain id `11155111`).

## Executing on chain

`execute` runs a published connector through the on-chain runner. It is a read-only call: no login, no transaction and no gas. The result is pinned to a block, so anyone can check it by calling the same runner at the same block.

JavaScript:

```ts
const result = await sdk.execute("pitch", 8, {
  // Override the running instance at position 0 for this run only.
  "0": { start_point: 12, transformation_shift: 0 },
});

console.log(result.block_number, result.block_hash, result.runner, result.registry);
console.log(result.particles);
// [{ path: "/pitch:0", data: [12, 13, 14, 15, 16, 17, 18, 19] }]
```

Python:

```python
result = sdk.execute(
    "pitch",
    8,
    # Override the running instance at position 0 for this run only.
    {"0": {"start_point": 12, "transformation_shift": 0}},
)

print(result.block_number, result.block_hash, result.runner, result.registry)
print(result.particles[0].path, result.particles[0].data)
# /pitch:0 [12, 13, 14, 15, 16, 17, 18, 19]
```

| Field | Description |
| --- | --- |
| `particles` | Output streams: `{ path, data }` per path. |
| `block_number`, `block_hash` | The block the call was pinned to. |
| `runner` | Address of the runner contract that executed it. |
| `registry` | Registry address the runner looked the connector up in. |

The step count must be between 1 and 65536. Running instances (up to 4096) are keyed by position, as described in [Core concepts](https://decentralised.art/sdk#concepts). Keep the block, runner and registry together with the values whenever you store or share a result.

## Errors

A response outside the 2xx range raises `DecentralisedArtApiError`, carrying the HTTP status and the decoded response body. Network failures surface as the runtime's own errors.

JavaScript:

```ts
import { DecentralisedArtApiError } from "decentralised-art";

try {
  await sdk.connectorGet("does_not_exist");
} catch (error) {
  if (error instanceof DecentralisedArtApiError) {
    console.log(error.status, error.body); // 404 { message: "..." }
  } else {
    throw error; // network failure, aborted request, ...
  }
}
```

Python:

```python
from decentralised_art.client import DecentralisedArtApiError

try:
    sdk.connector_get("does_not_exist")
except DecentralisedArtApiError as error:
    print(error.status_code, error.body)  # 404 {'message': '...'}
```

| Status | Meaning |
| --- | --- |
| `400` | Invalid request, or the runner rejected the execution (for example a condition was not met). |
| `401` | Missing or expired access token. Log in again. |
| `403` | You do not own the operation, or publication is disabled on this server. |
| `404` | No operation with that name. |
| `409` | The name is taken on chain, dependencies are missing or different, or the account nonce is already in use. |
| `503` | The chain provider or artifact storage is temporarily unavailable. Retry later. |

A pending publication is not an error: `publishConfirm` returns it with `status: "pending"` (HTTP 202).

## Building a World

A World is a web page that interprets connector output as sound, image or interaction. It is a static bundle (HTML, JavaScript, CSS and assets) that the platform shows in a sandboxed iframe, on its World page and inside Studio.

A World cannot reach the network on its own. It talks to the page that hosts it through the **World runtime**, and the host makes each call on its behalf, but only if the World's manifest grants the permission for it. The World never holds a token or a key.

### Bundle layout

Upload a ZIP with `world-manifest.json` at its root, the HTML entry file it names, and everything the page loads. Limits: 25 MB compressed, 100 MB extracted, 1000 files.

Packaging:

```bash
cd my-world
zip -r ../my-world.zip world-manifest.json index.html world.js style.css preview.png
```

### Entry script

Import the runtime the platform serves instead of bundling it, so every World uses the same build. Subscribe to state, then announce that the World is ready:

world.js:

```ts
// world.js — loaded by index.html as <script type="module" src="world.js">.
// Import the runtime the platform serves; Worlds never bundle their own copy.
// From /world-assets/{id}/world.js this resolves to /js/sdk/world-runtime.js.
import { createWorldSdk } from "../../js/sdk/world-runtime.js";

const sdk = createWorldSdk({ worldId: "simple-counter" });

sdk.onState(async (state) => {
  const payload = state.payload ?? {};
  const streams = payload.executeOutput ?? []; // [{ path, data }]

  try {
    draw(streams, payload.particlesCount);

    // Brokered calls: the host checks this World's manifest permissions.
    if (payload.connectorName) {
      const connector = await sdk.connectorGet(payload.connectorName);
      showFormat(connector.format_hash);
    }
    sdk.reportRendered(state.requestId);
  } catch (error) {
    sdk.reportError(error instanceof Error ? error.message : "Render failed");
  }
});

// Tell the host the World is listening. Calls made before this are rejected.
sdk.ready();
```

Upload the ZIP from [Upload a World](https://decentralised.art/worlds/upload) while signed in. The upload page validates the bundle before publishing it to the gallery.

## World manifest

world-manifest.json:

```json
{
  "schemaVersion": 1,
  "slug": "simple-counter",
  "name": "Simple Counter World",
  "version": "0.1.0",
  "entry": "index.html",
  "runtime": "iframe",
  "surfaces": ["world-page", "studio-plugin"],
  "permissions": ["decentralised.art.connectors.read", "decentralised.art.execute"],
  "description": "Renders connector metadata and numeric output streams.",
  "shortDescription": "Minimal World example.",
  "accentColor": "#34d399",
  "preview": "preview.png",
  "acceptedConnectorSets": [
    { "connectors": ["simple_counter"], "optionalConnectors": ["velocity_midi"] }
  ],
  "valueLimits": {
    "particlesCount": { "min": 1, "max": 64 },
    "connectorValues": { "/simple_counter:0": { "min": 0, "max": 127 } }
  }
}
```

| Field | Description |
| --- | --- |
| `schemaVersion` | Required. Currently `1`. |
| `slug` | Required. Lowercase letters, digits and dashes, up to 80 characters. |
| `name`, `version`, `description` | Required. Shown in the gallery and on the World page. |
| `entry` | Required. Path of the HTML entry file inside the ZIP. |
| `runtime` | Required. Always `"iframe"`. |
| `surfaces` | Required, at least one: `"world-page"` (its own page) and/or `"studio-plugin"` (inside Studio). |
| `permissions` | What the World may ask the host to do. See below. |
| `acceptedConnectorSets` | Connector names the World understands, with optional extras. Declare these or `acceptedFormatHashes`; at least one is required. |
| `acceptedFormatHashes` | Formats the World understands. |
| `valueLimits` | Optional ranges for `particlesCount` and for values on specific output paths. The host enforces the step count range on every call. |
| `preview` | Gallery image inside the ZIP: PNG, JPEG or WebP, up to 8 MB. |
| `shortDescription`, `heroLabel`, `accentColor` | Optional presentation details. |

### Permissions

| Permission | Allows |
| --- | --- |
| `decentralised.art.connectors.read` | `connectorGet`, `connectorExists`, `listFormats`, `formatInfo` |
| `decentralised.art.transformations.read` | `transformationGet`, `transformationExists` |
| `decentralised.art.conditions.read` | `conditionGet`, `conditionExists` |
| `decentralised.art.social.read` | `feed` |
| `decentralised.art.execute` | `execute`, `simulate` |
| `browser.audio` | Playing audio. |
| `browser.downloads` | Offering files for download. |

## World runtime API

`createWorldSdk(options)` returns the object a World uses for everything. Create it once.

| Option | Description |
| --- | --- |
| `worldId` | Required. The World's id, echoed in every message. |
| `requestTimeoutMs` | Timeout per call. Default 15000. |
| `channelToken` | Defaults to the `worldChannel` URL parameter the host adds. Rarely needed. |
| `targetOrigin`, `expectedOrigin` | Restrict which origin messages go to and come from. Inferred by default. |

| Method | Description |
| --- | --- |
| `ready()` | Tell the host the World is listening. Calls before this are rejected. |
| `onState(callback)` | Receive state from the host. Returns an unsubscribe function. |
| `reportRendered(requestId?)` | Tell the host a state has been rendered. |
| `reportError(message)` | Report an unrecoverable error to the host. |
| `connectorGet`, `transformationGet`, `conditionGet`, and their `…Exists` versions | Read operations. Results are cached for the life of the World. |
| `listFormats`, `formatInfo`, `feed` | Same as on the client; page size 1–100. |
| `execute`, `simulate` | Run a connector. Up to 100 running instances per call. |
| `dispose()` | Stop listening and reject calls still in flight. |

Inside a World:

```ts
// Needs "decentralised.art.execute" in the manifest.
const result = await sdk.execute("pitch", 16, { "0": { start_point: 60, transformation_shift: 0 } });
const preview = await sdk.simulate("pitch", 16);

// Needs "decentralised.art.social.read".
const latest = await sdk.feed({ limit: 10 });
```

### State from the platform

When the platform shows a World, it pushes state whose `payload` describes the current composition. The fields a World usually needs:

| Field | Description |
| --- | --- |
| `executeOutput` | Output streams to interpret: `[{ path, data }]`. |
| `connectorName` | The connector that produced them. |
| `particlesCount` | Number of steps. |
| `executionMode` | `"execute"` for on-chain results, `"simulate"` for simulation. |
| `executionProvenance` | Block, runner and registry of an on-chain result. |
| `surface` | `"world-page"` or `"studio-plugin"`. |

Treat any other fields as optional; more may be added over time.

### Call errors

A rejected call throws `WorldRpcCallError` with a `code`: `permission_denied` (missing permission), `bad_request` (invalid arguments, or a call before `ready()`), `unknown_method`, `host_error` (the API call failed; `status` holds its HTTP status) or `timeout`.

## Hosting Worlds

To show Worlds in your own application, use the host side, `createWorldHost` from `decentralised-art/worlds/host`. It answers a World's calls with your client, enforces the World's permissions and value limits, and pushes state to it.

Host page:

```ts
import { DecentralisedArtClient } from "decentralised-art";
import { createWorldHost } from "decentralised-art/worlds/host";

const iframe = document.querySelector<HTMLIFrameElement>("#world")!;
iframe.setAttribute("sandbox", "allow-scripts"); // opaque "null" origin

const host = createWorldHost({
  client: new DecentralisedArtClient(),
  iframe,
  permissions: manifest.permissions,
  valueLimits: manifest.valueLimits,
  expectedOrigin: "null",
  onReady: () =>
    host.pushState({
      payload: { connectorName: "pitch", particlesCount: 8, executeOutput: result.particles },
    }),
  onRendered: () => console.log("rendered"),
  onError: ({ message }) => console.error(message),
});

// The per-mount channel token travels in the URL; set src only after creating the host.
iframe.src = host.worldUrl(worldEntryUrl);

// Later: host.dispose();
```

-   Load the World in an iframe with `sandbox="allow-scripts"` and without `allow-same-origin`, so it cannot reach your page or its storage.
-   Each mount gets a random channel token, added to the iframe URL by `worldUrl()`. Messages without it are ignored in both directions.
-   Pass the permissions and value limits from the World's validated manifest, never from the World itself.

## Client methods

The JavaScript client is `DecentralisedArtClient`; the Python client is `decentralised_art.Client`. Responses use the API's field names (`format_hash`, `block_number`, …) in both languages. Python returns typed models with a `to_dict()` method.

| Method | Description |
| --- | --- |
| JS `version()` PY `version()` | Chain API version and build timestamp. |
| JS `getNonce(address, opts?)` PY `get_nonce(address, origin=)` | One-time nonce and EIP-4361 sign-in message for an address. |
| JS `loginWithWallet(wallet)` PY `login_with_account(account)` | Sign the issued sign-in message and store the access token. The wallet or account also becomes the default publication signer. |
| JS `loginWithSignature(address, nonce, signature)` PY `login_with_signature(address, nonce, signature)` | Log in with a signature produced elsewhere. |
| JS `listAccounts({ limit, after })` PY `list_accounts(limit=, after=)` | Accounts that own published operations. |
| JS `accountInfo(address, opts)` PY `account_info(address, ...)` | Connectors, transformations and conditions owned by an address, each with its own cursor. |
| JS `connectorExists(name)` PY `connector_exists(name)` | true, or false on 404. |
| JS `connectorGet(name)` PY `connector_get(name)` | Connector definition, owner, address and format hash. |
| JS `connectorPost(request)` PY `connector_post(request)` | Login Create a connector draft. |
| JS `transformationExists(name)` PY `transformation_exists(name)` | true, or false on 404. |
| JS `transformationGet(name)` PY `transformation_get(name)` | Name, args\_count, owner and address. |
| JS `transformationPost(request)` PY `transformation_post(request)` | Login Create a transformation draft. |
| JS `conditionExists(name)` PY `condition_exists(name)` | true, or false on 404. |
| JS `conditionGet(name)` PY `condition_get(name)` | Name, args\_count, owner and address. |
| JS `conditionPost(request)` PY `condition_post(request)` | Login Create a condition draft. |
| JS `simulate(name, count, dynamicRi?)` PY `simulate(name, count, dynamic_ri=)` | Run a connector in the server's local EVM. Returns output streams. |
| JS `execute(name, count, dynamicRi?)` PY `execute(name, count, dynamic_ri=)` | Run a published connector on chain at a pinned block. |
| JS `publish(kind, name, opts)` PY `publish(kind, name, account=, ...)` | Login Prepare, sign offline, relay and confirm until mined. |
| JS `publishPrepare(kind, name, { relay })` PY `publish_prepare(kind, name, relay=)` | Login Unsigned publication transaction, or the existing identical publication. |
| JS `publishSend(kind, request)` PY `publish_send(kind, name, content_hash, raw_tx)` | Login Broadcast an offline-signed transaction through the server. |
| JS `publishConfirm(kind, request)` PY `publish_confirm(kind, name, content_hash, tx_hash)` | Login Look the receipt up once: mined, or pending. |
| JS `listFormats({ limit, after })` PY `list_formats(limit=, after=)` | Known format hashes. |
| JS `formatInfo(hash, opts)` PY `format_info(hash, ...)` | Connectors and scalar labels for one format. |
| JS `feed(opts)` PY `feed(...)` | Newest-first page of chain events. |
| JS `feedStream({ sinceSeq, limit })` PY `feed_stream(since_seq=, limit=)` | Server-Sent Events stream of new events. |
| JS `accessToken` PY `access_token` | The current bearer token, if logged in. |

## Python CLI

The Python package installs a small command, `decentralised-art-auth`, for quick checks against an API. It prints JSON.

Terminal:

```bash
decentralised-art-auth version
decentralised-art-auth nonce 0xYourAddress
decentralised-art-auth --base-url http://localhost:54321 version
```

## Versions and source

-   Source, issues and releases: [github.com/decentralised-art/sdk](https://github.com/decentralised-art/sdk).
-   The clients are generated from the OpenAPI contracts in [api-spec](https://github.com/decentralised-art/api-spec), and a release is tied to one version of them. The live API reports its own version through `version()`.
-   Endpoint-level details are in the [API reference](https://decentralised.art/api-reference), and the current state of the services is on [API status](https://decentralised.art/api-status).

Source: https://decentralised.art/sdk
