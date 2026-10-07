> Bundled platform snapshot. Retrieved 2026-10-07 from https://decentralised.art/api-reference.
> Read core.getting-started for account onboarding in this MCP release.

# API reference

Reference for the decentralised.art HTTP APIs: the chain API for operations, simulation, publication and execution, and the services API for sign-in, profiles and Worlds.

## Overview

decentralised.art has two HTTP APIs. Both speak JSON over HTTPS.

| API | Base URL | What it does |
| --- | --- | --- |
| **Chain API** | `https://api.decentralised.art/chain` | Connectors, transformations and conditions: reading them, creating drafts, simulating, publishing on chain and executing. Also accounts, formats and the event feed. |
| **Services API** | `https://api.decentralised.art/services` | Sign-in, user profiles, follows, and publishing and serving Worlds. |

Reading needs no account. The [SDK](https://decentralised.art/sdk) wraps the chain API for JavaScript and Python, and the [MCP server](https://decentralised.art/mcp) offers it to AI agents. For the ideas behind it, see [About](https://decentralised.art/about).

Try it:

```bash
# Read a connector
curl https://api.decentralised.art/chain/connector/pitch

# Run it on chain for four steps (no login, no gas)
curl -X POST https://api.decentralised.art/chain/execute \
  -H "Content-Type: application/json" \
  -d '{"connector_name":"pitch","particles_count":4}'
```

## Authentication

Each API has its own sign-in, and both prove that you control an Ethereum address by signing a message. Send the resulting token as `Authorization: Bearer <token>`.

|  | Chain API | Services API |
| --- | --- | --- |
| Needed for | Creating drafts and publishing | Your profile, follows, and uploading Worlds |
| Steps | `GET /nonce/{address}`, sign the returned `message`, then `POST /auth` with `{ address, nonce, signature }` | `POST /auth/siwe/challenge`, sign the message, then `POST /auth/siwe/verify` |
| Signature | Sign-In with Ethereum (EIP-4361), signed with EIP-191 | Sign-In with Ethereum (EIP-4361), signed with EIP-191 |
| Token | JWT access token | Session token |
| Valid for | 5 minutes | 24 hours, or until sign-out |

The two tokens are not interchangeable. Reading, simulating and executing need neither.

## Conventions

### Names and addresses

-   Operation names start with a letter or underscore and contain letters, digits and underscores, up to 128 characters. They are global and cannot be changed.
-   Addresses are 40 hexadecimal characters, with or without `0x`. The chain API returns owner addresses in lowercase without `0x`; the services API returns checksummed addresses with `0x`.
-   A draft reports the address `"0x0"` until it is published.

### Field names

The chain API and the user endpoints use snake\_case (`format_hash`, `display_name`). World endpoints use camelCase (`entryUrn`, `acceptedFormatHashes`). Publication transactions use the Ethereum JSON-RPC spelling with hex quantities (`chainId`, `maxFeePerGas`).

### Pagination

-   Chain API lists take a required `limit` (1–256) and return a cursor. Pass `cursor.next_after` back as `after` (or, for the feed, `cursor.next_before` as `before`) while `cursor.has_more` is true.
-   Services API lists take a zero-based `page` and a `limit`.

### Errors

Errors use HTTP status codes. Chain API errors carry a JSON body with a `message`; publication errors can add `status`, `tx_hash`, `missing` and `mismatched`. Services API errors carry the status, and World endpoints add a plain-text message.

Chain API error:

```json
{ "message": "Connector not found" }
```

## Chain API

Base URL `https://api.decentralised.art/chain`. This part of the reference is generated from the [OpenAPI specification](https://decentralised.art/api-reference#specification).

## Core

Server version information.

GET `/version` No auth

### Get version

Get server build/version info

#### Responses

| Status | Description | Body |
| --- | --- | --- |
| 200 | Version info | [VersionResponse](https://decentralised.art/api-reference#schema-VersionResponse) |

Request:

```bash
curl https://api.decentralised.art/chain/version
```

Response:

```json
{
  "build_timestamp": "2026-10-01 11:42:09 UTC",
  "version": "0.4.0"
}
```

## Authentication

Creating and publishing need a bearer token. Request a sign-in challenge, sign its exact EIP-4361 message with personal\_sign, and submit the address, nonce and signature to /auth. Challenges and access tokens are valid for five minutes. Browser clients pass their origin when requesting a challenge.

GET `/nonce/{address}` No auth

### Get nonce

Issue a one-time \[EIP-4361\](https://eips.ethereum.org/EIPS/eip-4361) sign-in message for an address. Have the wallet sign `message` with `personal_sign`, then submit the `nonce` and the signature to `/auth` within five minutes. Each nonce can be redeemed once; requesting another one does not invalidate those already issued. Issuing a nonce stores nothing on the server: the nonce itself carries its issue time and origin under the server's signature. The message names the site the user signs in through: the `origin` query parameter when given; otherwise the request's `Origin` header when it is one the server is configured with; otherwise the server's first configured origin. Wallets that support EIP-4361 reject or warn when the message names a different site from the one asking for the signature, so a page should pass its own origin.

#### Parameters

| Name | In | Type | Description |
| --- | --- | --- | --- |
| `origin` | query | string | Origin of the page signing in, as `window.location.origin` gives it, percent-encoded or not. Browsers send no `Origin` header on a same-origin GET, so this is how a page served from a secondary configured origin gets a message naming it. A value that is not a configured origin is refused with 400. |

#### Responses

| Status | Description | Body |
| --- | --- | --- |
| 200 | Sign-in message issued | [NonceResponse](https://decentralised.art/api-reference#schema-NonceResponse) |
| 400 | Invalid address, or an `origin` that is not a configured sign-in origin. | [ErrorResponse](https://decentralised.art/api-reference#schema-ErrorResponse) |

Request:

```bash
curl https://api.decentralised.art/chain/nonce/0xYourAddress?origin=https%3A%2F%2Fdecentralised.art
```

Response (illustrative):

```json
{
  "nonce": "ababababababababababababababababababababababababababababababababab",
  "message": "https://decentralised.art wants you to sign in with your Ethereum account:\n0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266\n\nSign in to decentralised.art.\n\nURI: https://decentralised.art\nVersion: 1\nChain ID: 11155111\nNonce: ababababababababababababababababababababababababababababababababab\nIssued At: 2026-10-04T12:00:00Z\nExpiration Time: 2026-10-04T12:05:00Z"
}
```

POST `/auth` No auth

### Authenticate

Authenticate using an address, the nonce `/nonce` issued to it, and the wallet's `personal_sign` signature of the message issued with that nonce. The server checks the signature against the message it issued.

#### Request body application/json [AuthRequest](https://decentralised.art/api-reference#schema-AuthRequest)

| Field | Type | Description |
| --- | --- | --- |
| `address`required | string (Address) | Ethereum-style address, with or without a 0x prefix. |
| `nonce`required | string | The nonce `/nonce` issued to `address`. |
| `signature`required | string | The wallet's `personal_sign` (EIP-191) signature of the `message` issued with `nonce`, as 65-byte hex. |

#### Responses

| Status | Description | Body |
| --- | --- | --- |
| 200 | Authentication successful. Send `access_token` as `Authorization: Bearer <access_token>` to protected chain endpoints; it expires five minutes after it is issued. | [AuthResponse](https://decentralised.art/api-reference#schema-AuthResponse) |
| 400 | Invalid request body, address, or signature; or a nonce that `/nonce` did not issue to this address, has expired, or was already redeemed. | [ErrorResponse](https://decentralised.art/api-reference#schema-ErrorResponse) |

Request:

```bash
curl -X POST https://api.decentralised.art/chain/auth \
  -H "Content-Type: application/json" \
  -d '{"address":"0xYourAddress","nonce":"ababababababababababababababababababababababababababababababababab","signature":"0x…"}'
```

Response (illustrative):

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs…"
}
```

## Accounts

Addresses that own published operations, and what each one owns.

GET `/accounts` No auth

### List accounts

List chain accounts known to the registry.

HEAD /accounts checks the same query without a body.

#### Parameters

| Name | In | Type | Description |
| --- | --- | --- | --- |
| `limit`required | query | integer | Page size. (1–256) |
| `after` | query | string | Account cursor from a previous response `cursor.next_after`. |

#### Responses

| Status | Description | Body |
| --- | --- | --- |
| 200 | Account page | [AccountListResponse](https://decentralised.art/api-reference#schema-AccountListResponse) |
| 400 | Invalid query | [ErrorResponse](https://decentralised.art/api-reference#schema-ErrorResponse) |

Request:

```bash
curl https://api.decentralised.art/chain/accounts?limit=50
```

Response:

```json
{
  "accounts": [
    "fa71ff2394596f824d69961293d095a50d322e4e"
  ],
  "cursor": {
    "has_more": false,
    "next_after": null
  },
  "limit": 50,
  "total_accounts": 1
}
```

GET `/account/{address}` No auth

### Get account

Get owned connectors/transformations/conditions for an address.

#### Parameters

| Name | In | Type | Description |
| --- | --- | --- | --- |
| `limit`required | query | integer | Page size for each ownership list. (1–256) |
| `after_connectors` | query | string | Cursor for owned connectors. |
| `after_transformations` | query | string | Cursor for owned transformations. |
| `after_conditions` | query | string | Cursor for owned conditions. |

#### Responses

| Status | Description | Body |
| --- | --- | --- |
| 200 | Account info | [AccountInfoResponse](https://decentralised.art/api-reference#schema-AccountInfoResponse) |
| 400 | Invalid address, limit, or cursor | [ErrorResponse](https://decentralised.art/api-reference#schema-ErrorResponse) |

Request:

```bash
curl https://api.decentralised.art/chain/account/fa71ff2394596f824d69961293d095a50d322e4e?limit=50
```

Response:

```json
{
  "address": "fa71ff2394596f824d69961293d095a50d322e4e",
  "owned_connectors": [
    "pitch"
  ],
  "owned_transformations": [
    "add"
  ],
  "owned_conditions": [],
  "cursor_connectors": {
    "has_more": false,
    "next_after": null
  },
  "cursor_transformations": {
    "has_more": false,
    "next_after": null
  },
  "cursor_conditions": {
    "has_more": false,
    "next_after": null
  },
  "limit": 50
}
```

## Connectors

Read a connector by name, or create one as your draft. A draft reports address "0x0" until it is published.

GET `/connector/{name}` No auth

### Get connector by name

Returns connector definition, owner and derived format hash.

HEAD /connector/{name} answers 200 or 404 without a body.

#### Responses

| Status | Description | Body |
| --- | --- | --- |
| 200 | Connector info. | [ConnectorInfoResponse](https://decentralised.art/api-reference#schema-ConnectorInfoResponse) |
| 400 | Invalid connector name. | [ErrorResponse](https://decentralised.art/api-reference#schema-ErrorResponse) |
| 404 | Connector not found. | [ErrorResponse](https://decentralised.art/api-reference#schema-ErrorResponse) |
| 500 | Internal connector serialization or format lookup error. | [ErrorResponse](https://decentralised.art/api-reference#schema-ErrorResponse) |

Request:

```bash
curl https://api.decentralised.art/chain/connector/pitch
```

Response:

```json
{
  "name": "pitch",
  "dimensions": [
    {
      "transformations": [
        {
          "name": "add",
          "args": [
            1
          ]
        }
      ],
      "composite": "",
      "bindings": {}
    }
  ],
  "condition_name": "",
  "condition_args": [],
  "static_ri": {},
  "owner": "fa71ff2394596f824d69961293d095a50d322e4e",
  "address": "0xee5fc0669ae1c9f12db4ef0c216ae387fbede644",
  "format_hash": "4e5aa46feeb2db48b7df17d424f29bfdee2ccbfdf2433a99da6be58d3c9e3101"
}
```

POST `/connector` Chain bearer token

### Create connector

Compile and deploy a connector locally for simulation. The name must not be reserved on chain. Publish it on chain through /publish/connector.

#### Request body application/json [CreateConnectorRequest](https://decentralised.art/api-reference#schema-CreateConnectorRequest)

| Field | Type | Description |
| --- | --- | --- |
| `name`required | string (EntityName) | Entity name. Starts with a letter or '\_', contains only letters, digits and '\_', at most 128 characters. |
| `dimensions`required | [array of ConnectorDimension](https://decentralised.art/api-reference#schema-ConnectorDimension) | Ordered dimension definitions. |
| `condition_name` | string | Condition name. Omitted or empty string means no condition. |
| `condition_args` | array of integer (int32) | Condition arguments. Omitted means no condition arguments. |
| `static_ri` | [map of RunningInstance](https://decentralised.art/api-reference#schema-RunningInstance) | Optional static running-instance map. Keys are canonical decimal positions (for example "0", "3", "5"). |

#### Responses

| Status | Description | Body |
| --- | --- | --- |
| 201 | Created. | [CreateConnectorResponse](https://decentralised.art/api-reference#schema-CreateConnectorResponse) |
| 400 | Invalid payload. | [ErrorResponse](https://decentralised.art/api-reference#schema-ErrorResponse) |
| 401 | Unauthorized. | [ErrorResponse](https://decentralised.art/api-reference#schema-ErrorResponse) |
| 409 | Name is reserved on chain. | [ErrorResponse](https://decentralised.art/api-reference#schema-ErrorResponse) |
| 500 | Internal connector format lookup error. | [ErrorResponse](https://decentralised.art/api-reference#schema-ErrorResponse) |
| 503 | Live on-chain name check is unavailable. | [ErrorResponse](https://decentralised.art/api-reference#schema-ErrorResponse) |

Request:

```bash
curl -X POST https://api.decentralised.art/chain/connector \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"rising_line","dimensions":[{"transformations":[{"name":"add","args":[1]},{"name":"shift_up","args":[2]}]}],"condition_name":"positive_only","condition_args":[1]}'
```

Response (illustrative):

```json
{
  "name": "rising_line",
  "owner": "0xyouraddress…",
  "address": "0x0",
  "format_hash": "…"
}
```

## Transformations

sol\_src is the body of function run(uint32 x, uint32\[\] args) returns (uint32); args\_count is derived from the highest args\[i\] it uses. Solidity source is never returned.

GET `/transformation/{name}` No auth

### Get transformation by name

HEAD /transformation/{name} answers 200 or 404 without a body.

#### Responses

| Status | Description | Body |
| --- | --- | --- |
| 200 | Transformation info. | [TransformationInfoResponse](https://decentralised.art/api-reference#schema-TransformationInfoResponse) |
| 400 | Invalid request. | [ErrorResponse](https://decentralised.art/api-reference#schema-ErrorResponse) |
| 404 | Not found. | [ErrorResponse](https://decentralised.art/api-reference#schema-ErrorResponse) |
| 500 | Internal transformation serialization error. | [ErrorResponse](https://decentralised.art/api-reference#schema-ErrorResponse) |

Request:

```bash
curl https://api.decentralised.art/chain/transformation/add
```

Response (illustrative):

```json
{
  "name": "add",
  "args_count": 1,
  "runtime_code": "0x…",
  "owner": "fa71ff2394596f824d69961293d095a50d322e4e",
  "address": "0xa112a62768ec809c50a66a6efc16cb9dd9545d03"
}
```

POST `/transformation` Chain bearer token

### Create transformation

Compile and deploy a transformation locally for simulation. The name must not be reserved on chain. Publish it on chain through /publish/transformation.

#### Request body application/json [CreateTransformationRequest](https://decentralised.art/api-reference#schema-CreateTransformationRequest)

| Field | Type | Description |
| --- | --- | --- |
| `name`required | string (EntityName) | Entity name. Starts with a letter or '\_', contains only letters, digits and '\_', at most 128 characters. |
| `sol_src`required | string | Solidity source code |

#### Responses

| Status | Description | Body |
| --- | --- | --- |
| 201 | Created. | [CreateTransformationResponse](https://decentralised.art/api-reference#schema-CreateTransformationResponse) |
| 400 | Invalid request. | [ErrorResponse](https://decentralised.art/api-reference#schema-ErrorResponse) |
| 401 | Unauthorized. | [ErrorResponse](https://decentralised.art/api-reference#schema-ErrorResponse) |
| 409 | Name is reserved on chain. | [ErrorResponse](https://decentralised.art/api-reference#schema-ErrorResponse) |
| 503 | Live on-chain name check is unavailable. | [ErrorResponse](https://decentralised.art/api-reference#schema-ErrorResponse) |

Request:

```bash
curl -X POST https://api.decentralised.art/chain/transformation \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"shift_up","sol_src":"return x + args[0];"}'
```

Response (illustrative):

```json
{
  "name": "shift_up",
  "owner": "0xyouraddress…",
  "address": "0x0",
  "args_count": 1
}
```

## Conditions

sol\_src is the body of function check(int32\[\] args) view returns (bool). A connector stops with ConditionNotMet when its condition returns false.

GET `/condition/{name}` No auth

### Get condition by name

HEAD /condition/{name} answers 200 or 404 without a body.

#### Responses

| Status | Description | Body |
| --- | --- | --- |
| 200 | Condition info. | [ConditionInfoResponse](https://decentralised.art/api-reference#schema-ConditionInfoResponse) |
| 400 | Invalid request. | [ErrorResponse](https://decentralised.art/api-reference#schema-ErrorResponse) |
| 404 | Not found. | [ErrorResponse](https://decentralised.art/api-reference#schema-ErrorResponse) |
| 500 | Internal condition serialization error. | [ErrorResponse](https://decentralised.art/api-reference#schema-ErrorResponse) |

Request:

```bash
curl https://api.decentralised.art/chain/condition/positive_only
```

Response (illustrative):

```json
{
  "name": "positive_only",
  "args_count": 1,
  "runtime_code": null,
  "owner": "fa71ff2394596f824d69961293d095a50d322e4e",
  "address": "0x…"
}
```

POST `/condition` Chain bearer token

### Create condition

Compile and deploy a condition locally for simulation. The name must not be reserved on chain. Publish it on chain through /publish/condition.

#### Request body application/json [CreateConditionRequest](https://decentralised.art/api-reference#schema-CreateConditionRequest)

| Field | Type | Description |
| --- | --- | --- |
| `name`required | string (EntityName) | Entity name. Starts with a letter or '\_', contains only letters, digits and '\_', at most 128 characters. |
| `sol_src`required | string | Solidity source code |

#### Responses

| Status | Description | Body |
| --- | --- | --- |
| 201 | Created. | [CreateConditionResponse](https://decentralised.art/api-reference#schema-CreateConditionResponse) |
| 400 | Invalid request. | [ErrorResponse](https://decentralised.art/api-reference#schema-ErrorResponse) |
| 401 | Unauthorized. | [ErrorResponse](https://decentralised.art/api-reference#schema-ErrorResponse) |
| 409 | Name is reserved on chain. | [ErrorResponse](https://decentralised.art/api-reference#schema-ErrorResponse) |
| 503 | Live on-chain name check is unavailable. | [ErrorResponse](https://decentralised.art/api-reference#schema-ErrorResponse) |

Request:

```bash
curl -X POST https://api.decentralised.art/chain/condition \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"positive_only","sol_src":"return args[0] > 0;"}'
```

Response (illustrative):

```json
{
  "name": "positive_only",
  "owner": "0xyouraddress…",
  "address": "0x0",
  "args_count": 1
}
```

## Formats

A format hash identifies the shape of a connector's output. Connectors that share it produce compatible streams.

GET `/formats` No auth

### List format hashes

List connector format hashes known to the registry.

HEAD /formats checks the same query without a body.

#### Parameters

| Name | In | Type | Description |
| --- | --- | --- | --- |
| `limit`required | query | integer | Page size. (1–256) |
| `after` | query | string | Format hash cursor from a previous response `cursor.next_after`. |

#### Responses

| Status | Description | Body |
| --- | --- | --- |
| 200 | Format hash page. | [FormatListResponse](https://decentralised.art/api-reference#schema-FormatListResponse) |
| 400 | Invalid query. | [ErrorResponse](https://decentralised.art/api-reference#schema-ErrorResponse) |

Request:

```bash
curl https://api.decentralised.art/chain/formats?limit=50
```

Response:

```json
{
  "formats": [
    "4e5aa46feeb2db48b7df17d424f29bfdee2ccbfdf2433a99da6be58d3c9e3101"
  ],
  "cursor": {
    "has_more": false,
    "next_after": null
  },
  "limit": 50,
  "total_formats": 1
}
```

GET `/format/{hash}` No auth

### Get format membership

List connector names and scalar labels for a format hash.

#### Parameters

| Name | In | Type | Description |
| --- | --- | --- | --- |
| `limit`required | query | integer | Page size for connector names. (1–256) |
| `after` | query | string | Connector name cursor from a previous response `cursor.next_after`. |

#### Responses

| Status | Description | Body |
| --- | --- | --- |
| 200 | Format membership. | [FormatInfoResponse](https://decentralised.art/api-reference#schema-FormatInfoResponse) |
| 400 | Invalid format hash, limit, or cursor. | [ErrorResponse](https://decentralised.art/api-reference#schema-ErrorResponse) |

Request:

```bash
curl https://api.decentralised.art/chain/format/4e5aa46feeb2db48b7df17d424f29bfdee2ccbfdf2433a99da6be58d3c9e3101?limit=50
```

Response:

```json
{
  "format_hash": "4e5aa46feeb2db48b7df17d424f29bfdee2ccbfdf2433a99da6be58d3c9e3101",
  "connectors": [
    "pitch"
  ],
  "scalars": [
    "pitch:0"
  ],
  "cursor": {
    "has_more": false,
    "next_after": null
  },
  "limit": 50,
  "total_connectors": 1
}
```

## Feed

Chain events, newest first, as connectors, transformations and conditions are published. Items move through observed, safe and finalized, or become removed after a reorganisation.

GET `/feed` No auth

### List feed items

Returns a newest-first page of feed items. Each item is keyed by a stable `feed_id` and includes compact payload metadata identifying the changed entity. Use `/connector/{name}`, `/transformation/{name}`, or `/condition/{name}` to hydrate full entity details.

#### Parameters

| Name | In | Type | Description |
| --- | --- | --- | --- |
| `limit`required | query | integer | Page size. (1–256) |
| `before` | query | string | History cursor from a previous response `cursor.next_before`. |
| `type` | query | FeedEventType | Optional event type filter. |
| `include_unfinalized` | query | 0 \| 1 | Set to `1` to include observed and safe events. Set to `0` to return only finalized events. When omitted, unfinalized events are included. |

#### Responses

| Status | Description | Body |
| --- | --- | --- |
| 200 | Feed page. | [FeedPage](https://decentralised.art/api-reference#schema-FeedPage) |
| 400 | Invalid query. | [ErrorResponse](https://decentralised.art/api-reference#schema-ErrorResponse) |

Request:

```bash
curl https://api.decentralised.art/chain/feed?limit=1&include_unfinalized=0
```

Response:

```json
{
  "items": [
    {
      "feed_id": "local:11155111:connector_added:pitch",
      "event_type": "connector_added",
      "status": "finalized",
      "visible": true,
      "tx_hash": "0x0fc499e4f88ae66792da639b29af1794fded0efd75d892b56e7591380e29d190",
      "block_number": 12,
      "tx_index": 0,
      "log_index": 0,
      "history_cursor": "c1790857774523:12:0:local:11155111:connector_added:pitch",
      "created_at_ms": 1790857774523,
      "updated_at_ms": 1790857792829,
      "projector_version": 1,
      "payload": {
        "type": "connector",
        "name": "pitch",
        "owner": "0xfa71ff2394596f824d69961293d095a50d322e4e"
      }
    }
  ],
  "cursor": {
    "has_more": true,
    "next_before": "c1790857774523:12:0:local:11155111:connector_added:pitch"
  },
  "limit": 1
}
```

GET `/feed/stream` No auth

### Stream feed deltas

Opens a Server-Sent Events stream. The response starts with a bounded replay from `since_seq`, then emits a `stream_meta` event describing the replay window, and then tails live feed deltas. Delta event names match their feed event type (`connector_added`, `transformation_added`, or `condition_added`). The JSON in each delta `data:` frame conforms to `schemas/feedStreamDelta.yaml`; `stream_meta` frame data conforms to `schemas/feedStreamMeta.yaml`. Idle live streams emit keepalive comments.

#### Parameters

| Name | In | Type | Description |
| --- | --- | --- | --- |
| `since_seq` | query | integer (int64) | Replay stream deltas with `stream_seq` greater than this value. (≥ 0, default 0) |
| `limit` | query | integer | Maximum number of replay deltas returned before live tailing. (1–2048, default 200) |

#### Responses

| Status | Description | Body |
| --- | --- | --- |
| 200 | Server-Sent Events stream. | string |
| 400 | Invalid query. | [ErrorResponse](https://decentralised.art/api-reference#schema-ErrorResponse) |

Request:

```bash
curl -N "https://api.decentralised.art/chain/feed/stream?since_seq=0"
```

Response:

```bash
: min_available_seq=1

id: 42
event: connector_added
data: {"stream_seq":42,"event_type":"connector_added","status":"finalized","feed_id":"…","history_cursor":"…","created_at_ms":1790857774523,"payload":{"type":"connector","name":"pitch","owner":"0x…"}}

event: stream_meta
data: {…}
```

## Run

Simulate drafts for free in the server's local EVM, or execute published connectors on chain. Neither needs a login. particles\_count is the number of steps; dynamic\_ri sets running instances by position for one run.

POST `/simulate` No auth

### Simulate locally

Run a connector in the server's local simulation EVM: drafts created on this server, and published connectors. A connector that exists only on chain is first deployed locally with its dependencies from their verified artifacts. No login is required, and the result carries no chain provenance.

#### Request body application/json [ExecuteRequest](https://decentralised.art/api-reference#schema-ExecuteRequest)

| Field | Type | Description |
| --- | --- | --- |
| `connector_name`required | string | Connector name to execute. |
| `particles_count`required | integer or string | Number of particles to generate. The backend accepts protobuf JSON uint32 values between 1 and 65536. |
| `dynamic_ri` | [map of RunningInstance](https://decentralised.art/api-reference#schema-RunningInstance) | Dynamic running-instance overrides keyed by canonical decimal RI position. Omitted means no overrides. At most 4096 entries. |

#### Responses

| Status | Description | Body |
| --- | --- | --- |
| 200 | Executed. | [array of ParticlesResultItem](https://decentralised.art/api-reference#schema-ParticlesResultItem) |
| 400 | Bad request, or execution rejected by the runner (for example a condition was not met). | [ErrorResponse](https://decentralised.art/api-reference#schema-ErrorResponse) |
| 404 | Connector not found. | [ErrorResponse](https://decentralised.art/api-reference#schema-ErrorResponse) |
| 500 | Internal deployment, execution or response decoding error. | [ErrorResponse](https://decentralised.art/api-reference#schema-ErrorResponse) |
| 503 | A chain-only connector cannot be simulated yet: the verified artifacts of it or its dependencies are not available. | [ErrorResponse](https://decentralised.art/api-reference#schema-ErrorResponse) |

Request:

```bash
curl -X POST https://api.decentralised.art/chain/simulate \
  -H "Content-Type: application/json" \
  -d '{"connector_name":"pitch","particles_count":4}'
```

Response:

```json
[
  {
    "path": "/pitch:0",
    "data": [
      0,
      1,
      2,
      3
    ]
  }
]
```

POST `/execute` No auth

### Execute on chain

eth\_call of Runner.gen on the configured runner, pinned to the block the server's execute block tag resolves to. The chain decides whether the connector exists; the server's own registry is not consulted. No login is required: an eth\_call sends no transaction and costs no gas.

#### Request body application/json [ExecuteRequest](https://decentralised.art/api-reference#schema-ExecuteRequest)

| Field | Type | Description |
| --- | --- | --- |
| `connector_name`required | string | Connector name to execute. |
| `particles_count`required | integer or string | Number of particles to generate. The backend accepts protobuf JSON uint32 values between 1 and 65536. |
| `dynamic_ri` | [map of RunningInstance](https://decentralised.art/api-reference#schema-RunningInstance) | Dynamic running-instance overrides keyed by canonical decimal RI position. Omitted means no overrides. At most 4096 entries. |

#### Responses

| Status | Description | Body |
| --- | --- | --- |
| 200 | Executed | [ExecuteResponse](https://decentralised.art/api-reference#schema-ExecuteResponse) |
| 400 | Bad request, or execution rejected by the runner. | [ErrorResponse](https://decentralised.art/api-reference#schema-ErrorResponse) |
| 404 | Connector not found in the runner's registry. | [ErrorResponse](https://decentralised.art/api-reference#schema-ErrorResponse) |
| 500 | Response decoding error. | [ErrorResponse](https://decentralised.art/api-reference#schema-ErrorResponse) |
| 502 | Chain returned a malformed result. | [ErrorResponse](https://decentralised.art/api-reference#schema-ErrorResponse) |
| 503 | On-chain execution is not configured, or the chain endpoint is unavailable. | [ErrorResponse](https://decentralised.art/api-reference#schema-ErrorResponse) |

Request:

```bash
curl -X POST https://api.decentralised.art/chain/execute \
  -H "Content-Type: application/json" \
  -d '{"connector_name":"pitch","particles_count":4,"dynamic_ri":{"0":{"start_point":12,"transformation_shift":0}}}'
```

Response:

```json
{
  "block_number": 11825489,
  "block_hash": "0x1c4b37dc907b055ffd53e0d32536a408a2d93e9bedfa7ed167cba14991729cfa",
  "runner": "0xe0e70f522b64a6c8d2301697cd7133be33eae77f",
  "registry": "0x7648cc2a6db6152a60615ebbba4b9e1f900e26fa",
  "particles": [
    {
      "path": "/pitch:0",
      "data": [
        12,
        13,
        14,
        15
      ]
    }
  ]
}
```

## Publication

Publish one of your drafts on chain, paid from your own wallet. Prepare, send the transaction (with a browser wallet, or signed offline and relayed through /send), then confirm. Dependencies must be published first, and publications from one owner must be made one at a time.

POST `/publish/{kind}/prepare` Chain bearer token

### Prepare publication

Rebuild the entity from the definition retained when it was created, store its artifact durably, and return the unsigned registry transaction. The caller must own the entity. A connector's dependencies must already be registered with the artifacts it was built against; they are never published recursively. Deterministic reverts (name taken, stale nonce, identity mismatch) are reported here, before the owner pays.

#### Request body application/json [PrepareRequest](https://decentralised.art/api-reference#schema-PrepareRequest)

| Field | Type | Description |
| --- | --- | --- |
| `name`required | string (EntityName) | Entity name. Starts with a letter or '\_', contains only letters, digits and '\_', at most 128 characters. |
| `relay` | boolean | Also return `signing`, what an offline signer needs to complete the transaction for POST /publish/{kind}/send. Leave unset for a browser wallet, which chooses its own nonce and fees. (default false) |

#### Responses

| Status | Description | Body |
| --- | --- | --- |
| 200 | Prepared transaction, or the existing identical publication. | [PrepareResponse](https://decentralised.art/api-reference#schema-PrepareResponse) |
| 400 | Invalid request, the entity cannot be rebuilt, or the transaction would revert. | [PublishError](https://decentralised.art/api-reference#schema-PublishError) |
| 401 | Unauthorized. | [PublishError](https://decentralised.art/api-reference#schema-PublishError) |
| 403 | Publication is disabled on this server, or the caller does not own the entity. | [PublishError](https://decentralised.art/api-reference#schema-PublishError) |
| 404 | Unknown kind, or no local definition of this entity exists. | [PublishError](https://decentralised.art/api-reference#schema-PublishError) |
| 409 | The registry holds different content under this name, or connector dependencies are `missing` or `mismatched`. | [PublishError](https://decentralised.art/api-reference#schema-PublishError) |
| 503 | Chain provider or durable artifact storage failure. | [PublishError](https://decentralised.art/api-reference#schema-PublishError) |

Request:

```bash
curl -X POST https://api.decentralised.art/chain/publish/transformation/prepare \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"shift_up","relay":true}'
```

Response (illustrative):

```json
{
  "status": "prepared",
  "kind": "transformation",
  "name": "shift_up",
  "address": "0x…",
  "content_hash": "0x5d3f…c41a",
  "publication_nonce": 0,
  "deadline": 1790903600,
  "transaction": {
    "from": "0xyouraddress…",
    "to": "0xregistry…",
    "data": "0x…",
    "chainId": "0xaa36a7",
    "gas": "0x3d090"
  },
  "signing": {
    "type": "0x2",
    "nonce": "0x7",
    "maxFeePerGas": "0x2540be400",
    "maxPriorityFeePerGas": "0x3b9aca00",
    "value": "0x0"
  }
}
```

POST `/publish/{kind}/send` Chain bearer token

### Relay publication

Broadcast a publication transaction the owner signed offline, through the server's own chain provider, so the owner needs no RPC endpoint. The owner still pays for it. The server forwards it only when the caller signed it, it calls the configured registry on its chain with no value, it publishes exactly the named entity with this content hash, and a dry run succeeds within its gas limit. Confirm it with POST /publish/{kind}.

#### Request body application/json [SendRequest](https://decentralised.art/api-reference#schema-SendRequest)

| Field | Type | Description |
| --- | --- | --- |
| `name`required | string (EntityName) | Entity name. Starts with a letter or '\_', contains only letters, digits and '\_', at most 128 characters. |
| `content_hash`required | string (Hash32) | 32-byte hex value. |
| `raw_tx`required | string | Signed type-2 transaction: `transaction` merged with `signing` from a relay prepare, as `0x02 \|\| rlp(...)`. |

#### Responses

| Status | Description | Body |
| --- | --- | --- |
| 202 | Broadcast, or already held by the provider. | [SendResponse](https://decentralised.art/api-reference#schema-SendResponse) |
| 400 | Invalid request or transaction, a transaction other than this publication, a dry-run revert, too little gas, or insufficient funds. | [PublishError](https://decentralised.art/api-reference#schema-PublishError) |
| 401 | Unauthorized. | [PublishError](https://decentralised.art/api-reference#schema-PublishError) |
| 403 | Publication is disabled on this server, or another account signed the transaction. | [PublishError](https://decentralised.art/api-reference#schema-PublishError) |
| 404 | Unknown kind. | [PublishError](https://decentralised.art/api-reference#schema-PublishError) |
| 409 | The account nonce is already used, or another transaction with it is pending. Prepare again. | [PublishError](https://decentralised.art/api-reference#schema-PublishError) |
| 503 | Chain provider failure. | [PublishError](https://decentralised.art/api-reference#schema-PublishError) |

Request:

```bash
curl -X POST https://api.decentralised.art/chain/publish/transformation/send \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"shift_up","content_hash":"0x5d3f…c41a","raw_tx":"0x02f8…"}'
```

Response (illustrative):

```json
{
  "status": "pending",
  "tx_hash": "0x8b21…77e0"
}
```

POST `/publish/{kind}` Chain bearer token

### Confirm publication

Look the transaction receipt up once. Repeat the request while it answers 202; that is the status check. The registry projection of the event, not this response, is what the read endpoints serve.

#### Request body application/json [ConfirmRequest](https://decentralised.art/api-reference#schema-ConfirmRequest)

| Field | Type | Description |
| --- | --- | --- |
| `name`required | string (EntityName) | Entity name. Starts with a letter or '\_', contains only letters, digits and '\_', at most 128 characters. |
| `content_hash`required | string (Hash32) | 32-byte hex value. |
| `tx_hash`required | string | Hash of the sent publication transaction. |

#### Responses

| Status | Description | Body |
| --- | --- | --- |
| 201 | Mined and matched. | [ConfirmResponse](https://decentralised.art/api-reference#schema-ConfirmResponse) |
| 202 | Transaction not mined yet (`status` is `pending`). | [PublishError](https://decentralised.art/api-reference#schema-PublishError) |
| 400 | Invalid request, the transaction reverted, or it registered something else. | [PublishError](https://decentralised.art/api-reference#schema-PublishError) |
| 401 | Unauthorized. | [PublishError](https://decentralised.art/api-reference#schema-PublishError) |
| 403 | Publication is disabled on this server. | [PublishError](https://decentralised.art/api-reference#schema-PublishError) |
| 404 | Unknown kind. | [PublishError](https://decentralised.art/api-reference#schema-PublishError) |
| 503 | Chain provider failure. | [PublishError](https://decentralised.art/api-reference#schema-PublishError) |

Request:

```bash
curl -X POST https://api.decentralised.art/chain/publish/transformation \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"shift_up","content_hash":"0x5d3f…c41a","tx_hash":"0x8b21…77e0"}'
```

Response (illustrative):

```json
{
  "status": "mined",
  "kind": "transformation",
  "name": "shift_up",
  "tx_hash": "0x8b21…77e0",
  "block_number": 11825600,
  "address": "0x…",
  "owner": "0xyouraddress…",
  "content_hash": "0x5d3f…c41a"
}
```

## Services API

Base URL `https://api.decentralised.art/services`.

## Health

Liveness check.

GET `/health` No auth

### Health check

Answers ok when the service is running.

#### Responses

| Status | Description | Body |
| --- | --- | --- |
| 200 | The text ok. | text/plain |

Request:

```bash
curl https://api.decentralised.art/services/health
```

Response:

```bash
ok
```

## Sign-in (SIWE)

Sign-In with Ethereum (EIP-4361). Ask for a challenge, sign its message with the wallet (EIP-191), and verify it to get a session token. Send the token as Authorization: Bearer <token>. Sessions last 24 hours. This session is separate from the chain API's access token.

POST `/auth/siwe/challenge` No auth

### Request a sign-in message

Creates a single-use SIWE message for the address, valid for five minutes. Its domain and URI come from the request's Origin header (or app\_origin), which must be an allowed origin. At most five unexpired challenges can exist per address.

#### Request body application/json

| Field | Type | Description |
| --- | --- | --- |
| `address`required | string | The wallet's Ethereum address. |
| `chain_id`required | integer | The wallet's chain. Must be a chain the server allows (by default Ethereum mainnet 1, Sepolia 11155111 and local development chains). |
| `app_origin` | string | The page's origin, used when the request carries no Origin header. |

#### Responses

| Status | Description | Body |
| --- | --- | --- |
| 200 | The message to sign and when it expires. | { message, expires\_at } |
| 400 | Invalid address, chain not allowed, or invalid origin. |  |
| 403 | The origin is not allowed. |  |
| 429 | Too many active challenges for this address. |  |

Request:

```bash
curl -X POST https://api.decentralised.art/services/auth/siwe/challenge \
  -H "Content-Type: application/json" \
  -H "Origin: https://decentralised.art" \
  -d '{"address":"0xfa71Ff2394596F824D69961293D095A50d322e4E","chain_id":11155111}'
```

Response (illustrative):

```json
{
  "message": "decentralised.art wants you to sign in with your Ethereum account:\n0xfa71Ff…2e4E\n\nSign in to decentralised.art.\n\nURI: https://decentralised.art/auth/siwe/verify\nVersion: 1\nChain ID: 11155111\nNonce: …\nIssued At: …\nExpiration Time: …",
  "expires_at": "2026-10-02T10:05:00Z"
}
```

POST `/auth/siwe/verify` No auth

### Verify the signed message

Checks the signature against an unused, unexpired challenge and opens a session. The response body is the session token itself, as a JSON string. The user record is created on first sign-in.

#### Request body application/json

| Field | Type | Description |
| --- | --- | --- |
| `message`required | string | The exact message from the challenge. |
| `signature`required | string | The wallet's EIP-191 signature of the message, hex encoded. |

#### Responses

| Status | Description | Body |
| --- | --- | --- |
| 200 | The session token: two 64-character hex parts joined by a dot. | string |
| 400 | Malformed message or signature. |  |
| 401 | Unknown, used or expired challenge, or the signature does not match. |  |

Request:

```bash
curl -X POST https://api.decentralised.art/services/auth/siwe/verify \
  -H "Content-Type: application/json" \
  -d '{"message":"decentralised.art wants you to sign in…","signature":"0x…"}'
```

Response (illustrative):

```json
"6f1c…e2a0.b94d…07c3"
```

GET `/auth/me` Session

### Current user

The signed-in user's record.

#### Responses

| Status | Description | Body |
| --- | --- | --- |
| 200 | The user. | [UserPublic](https://decentralised.art/api-reference#schema-UserPublic) |
| 401 | Missing, invalid or expired session. |  |

Request:

```bash
curl https://api.decentralised.art/services/auth/me \
  -H "Authorization: Bearer $SESSION"
```

POST `/auth/logout` Session

### Sign out

Ends the current session.

#### Responses

| Status | Description | Body |
| --- | --- | --- |
| 204 | Signed out. |  |
| 401 | Missing, invalid or expired session. |  |

Request:

```bash
curl -X POST https://api.decentralised.art/services/auth/logout \
  -H "Authorization: Bearer $SESSION"
```

## Users

Public profiles. A user's id is their Ethereum address.

GET `/users` No auth

### List users

Addresses of registered users, one page at a time.

#### Parameters

| Name | In | Type | Description |
| --- | --- | --- | --- |
| `page` | query | integer | Zero-based page number (default 0). |
| `limit` | query | integer | Page size (default 50). |

#### Responses

| Status | Description | Body |
| --- | --- | --- |
| 200 | User addresses. | array of string |

Request:

```bash
curl "https://api.decentralised.art/services/users?limit=50"
```

Response:

```json
[
  "0xfa71Ff2394596F824D69961293D095A50d322e4E",
  "0xb530bF08D76015080C67D6b5f00CdeE53b45bdDA"
]
```

GET `/users/{address}` No auth

### Get a user

A user's public record.

#### Parameters

| Name | In | Type | Description |
| --- | --- | --- | --- |
| `address`required | path | string | Ethereum address, in any letter case. |

#### Responses

| Status | Description | Body |
| --- | --- | --- |
| 200 | The user. | [UserPublic](https://decentralised.art/api-reference#schema-UserPublic) |
| 400 | Not a valid address. |  |
| 404 | No user with this address. |  |

Request:

```bash
curl https://api.decentralised.art/services/users/0xfa71Ff2394596F824D69961293D095A50d322e4E
```

Response:

```json
{
  "id": "0xfa71Ff2394596F824D69961293D095A50d322e4E",
  "display_name": "Sawyer",
  "status": "active",
  "roles": [
    "user"
  ],
  "profile_json": {
    "public": {
      "bio": "",
      "kind": "human",
      "nickname": "Sawyer"
    }
  },
  "created_at": "2026-10-01T00:48:26.030755101Z",
  "updated_at": "2026-10-01T03:09:12.648956949Z",
  "last_login_at": "2026-10-01T03:09:12.648956949Z"
}
```

PATCH `/users/{address}` Session · owner only

### Update your profile

Changes your own display name or profile. Fields you leave out are not changed.

#### Parameters

| Name | In | Type | Description |
| --- | --- | --- | --- |
| `address`required | path | string | Your own address. |

#### Request body application/json

| Field | Type | Description |
| --- | --- | --- |
| `display_name` | string, nullable | New display name; null clears it. |
| `profile_json` | object | Replaces the profile data. |

#### Responses

| Status | Description | Body |
| --- | --- | --- |
| 200 | The updated user. | [UserPublic](https://decentralised.art/api-reference#schema-UserPublic) |
| 400 | Not a valid address. |  |
| 401 | Missing, invalid or expired session. |  |
| 403 | This is not your profile. |  |

Request:

```bash
curl -X PATCH https://api.decentralised.art/services/users/0xfa71Ff2394596F824D69961293D095A50d322e4E \
  -H "Authorization: Bearer $SESSION" \
  -H "Content-Type: application/json" \
  -d '{"display_name":"Sawyer","profile_json":{"public":{"nickname":"Sawyer","bio":"Composer"}}}'
```

DELETE `/users/{address}` Session · owner only

### Delete your account

Deletes your own user record.

#### Parameters

| Name | In | Type | Description |
| --- | --- | --- | --- |
| `address`required | path | string | Your own address. |

#### Responses

| Status | Description | Body |
| --- | --- | --- |
| 204 | Deleted. |  |
| 401 | Missing, invalid or expired session. |  |
| 403 | This is not your account. |  |

## Follows

Follow other users. These endpoints act on the signed-in user.

GET `/social/following` Session

### Who you follow

Addresses the signed-in user follows.

GET /social/followers returns the addresses that follow the signed-in user.

#### Responses

| Status | Description | Body |
| --- | --- | --- |
| 200 | Addresses. | array of string |
| 401 | Missing, invalid or expired session. |  |

POST `/social/follow` Session

### Follow a user

Starts following another user.

POST /social/unfollow takes the same body and stops following.

#### Request body application/json

| Field | Type | Description |
| --- | --- | --- |
| `followed_id`required | string | Address of the user to follow. |

#### Responses

| Status | Description | Body |
| --- | --- | --- |
| 204 | Done. |  |
| 400 | Empty id, or your own address. |  |
| 401 | Missing, invalid or expired session. |  |
| 404 | No such user. |  |

Request:

```bash
curl -X POST https://api.decentralised.art/services/social/follow \
  -H "Authorization: Bearer $SESSION" \
  -H "Content-Type: application/json" \
  -d '{"followed_id":"0xfa71Ff2394596F824D69961293D095A50d322e4E"}'
```

## Worlds

Browse and publish Worlds. Uploads are multipart/form-data with the ZIP in a field named bundle (up to 25 MB). The bundle rules are described in SDK → Building a World. World endpoints answer errors with a plain-text message.

GET `/worlds` No auth

### List Worlds

Active Worlds, one page at a time.

#### Parameters

| Name | In | Type | Description |
| --- | --- | --- | --- |
| `page` | query | integer | Zero-based page number (default 0). |
| `limit` | query | integer | Page size, 1–100 (default 50). |
| `surface` | query | "world-page" \| "studio-plugin" | Only Worlds that support this surface. |
| `q` | query | string | Search text. |

#### Responses

| Status | Description | Body |
| --- | --- | --- |
| 200 | Worlds. | [array of WorldDescriptor](https://decentralised.art/api-reference#schema-WorldDescriptor) |
| 400 | Invalid surface. |  |

Request:

```bash
curl "https://api.decentralised.art/services/worlds?surface=world-page&limit=30"
```

GET `/worlds/{id}` No auth

### Get a World

One World's descriptor.

#### Parameters

| Name | In | Type | Description |
| --- | --- | --- | --- |
| `id`required | path | string | World id. |

#### Responses

| Status | Description | Body |
| --- | --- | --- |
| 200 | The World. | [WorldDescriptor](https://decentralised.art/api-reference#schema-WorldDescriptor) |
| 404 | World not found. |  |

POST `/worlds/validate` No auth

### Validate a bundle

Checks a World bundle without publishing it. No sign-in needed.

#### Request body multipart/form-data

| Field | Type | Description |
| --- | --- | --- |
| `bundle`required | file (ZIP) | The World bundle, with world-manifest.json at its root. |

#### Responses

| Status | Description | Body |
| --- | --- | --- |
| 200 | The manifest as it would be published, bundle and manifest hashes, and warnings. | { descriptor, bundleHash, manifestHash, warnings } |
| 400 | Invalid bundle or manifest; the message says what is wrong. |  |
| 413 | The bundle is larger than 25 MB. |  |

Request:

```bash
curl -X POST https://api.decentralised.art/services/worlds/validate \
  -F "bundle=@my-world.zip"
```

POST `/worlds/upload` Session

### Publish a World

Validates and publishes a bundle. You become the World's owner.

#### Request body multipart/form-data

| Field | Type | Description |
| --- | --- | --- |
| `bundle`required | file (ZIP) | The World bundle. |

#### Responses

| Status | Description | Body |
| --- | --- | --- |
| 200 | The published World. | [WorldDescriptor](https://decentralised.art/api-reference#schema-WorldDescriptor) |
| 400 | Invalid bundle or manifest. |  |
| 401 | Missing, invalid or expired session. |  |
| 409 | The World already exists. |  |
| 413 | The bundle is larger than 25 MB. |  |

Request:

```bash
curl -X POST https://api.decentralised.art/services/worlds/upload \
  -H "Authorization: Bearer $SESSION" \
  -F "bundle=@my-world.zip"
```

PATCH `/worlds/{id}` Session · owner only

### Replace a World's bundle

Publishes a new bundle for a World you own (administrators can update any World).

#### Parameters

| Name | In | Type | Description |
| --- | --- | --- | --- |
| `id`required | path | string | World id. |

#### Request body multipart/form-data

| Field | Type | Description |
| --- | --- | --- |
| `bundle`required | file (ZIP) | The new World bundle. |

#### Responses

| Status | Description | Body |
| --- | --- | --- |
| 200 | The updated World. | [WorldDescriptor](https://decentralised.art/api-reference#schema-WorldDescriptor) |
| 400 | Invalid bundle or manifest. |  |
| 401 | Missing, invalid or expired session. |  |
| 403 | You do not own this World. |  |
| 404 | World not found. |  |
| 409 | The bundle conflicts with the World's current content. |  |

DELETE `/worlds/{id}` Session · owner only

### Delete a World

Removes a World you own from the gallery and stops serving its files.

#### Parameters

| Name | In | Type | Description |
| --- | --- | --- | --- |
| `id`required | path | string | World id. |

#### Responses

| Status | Description | Body |
| --- | --- | --- |
| 204 | Deleted. |  |
| 401 | Missing, invalid or expired session. |  |
| 403 | You do not own this World. |  |
| 404 | World not found. |  |

## World files and SDK

Static files served for Worlds.

GET `/world-assets/{id}/{path}` No auth

### World file

A file from a published World's bundle, such as its entry page. Files are served with a Content-Security-Policy that keeps the World from reaching the network directly; it talks to its host through the World runtime.

#### Parameters

| Name | In | Type | Description |
| --- | --- | --- | --- |
| `id`required | path | string | World id. |
| `path`required | path | string | File path inside the bundle. |

#### Responses

| Status | Description | Body |
| --- | --- | --- |
| 200 | The file. |  |
| 404 | Unknown or deleted World, or no such file. |  |

GET `/js/sdk/{file}` No auth

### World runtime and host scripts

The platform's builds of the SDK's World modules: world-runtime.js (imported by Worlds) and world-host.js (used by pages that embed Worlds).

#### Parameters

| Name | In | Type | Description |
| --- | --- | --- | --- |
| `file`required | path | "world-runtime.js" \| "world-host.js" | Script name. |

#### Responses

| Status | Description | Body |
| --- | --- | --- |
| 200 | JavaScript module. |  |
| 404 | Any other file name. |  |

Request:

```bash
curl https://api.decentralised.art/services/js/sdk/world-runtime.js
```

## Chain schemas

Object types used by the chain API, from its OpenAPI specification.

### AccountAddressCursorState

Cursor state for the account list.

| Field | Type | Description |
| --- | --- | --- |
| `has_more`required | boolean | Indicates whether more account addresses are available. |
| `next_after`required | string, nullable | Account cursor for the next page, or null when exhausted. |

### AccountInfoResponse

Cursor-based account ownership response.

| Field | Type | Description |
| --- | --- | --- |
| `address`required | string (Address) | Ethereum-style address, with or without a 0x prefix. |
| `limit`required | integer | Page size used for this response. (1–256) |
| `owned_connectors`required | array of string | Owned connector names. |
| `owned_transformations`required | array of string | Owned transformation names. |
| `owned_conditions`required | array of string | Owned condition names. |
| `cursor_connectors`required | [NameCursorState](https://decentralised.art/api-reference#schema-NameCursorState) | Cursor state for one ownership list. |
| `cursor_transformations`required | [NameCursorState](https://decentralised.art/api-reference#schema-NameCursorState) | Cursor state for one ownership list. |
| `cursor_conditions`required | [NameCursorState](https://decentralised.art/api-reference#schema-NameCursorState) | Cursor state for one ownership list. |

### AccountListResponse

Cursor-based account list response.

| Field | Type | Description |
| --- | --- | --- |
| `limit`required | integer | Page size used for this response. (1–256) |
| `total_accounts`required | integer | Total number of known accounts. (≥ 0) |
| `cursor`required | [AccountAddressCursorState](https://decentralised.art/api-reference#schema-AccountAddressCursorState) | Cursor state for the account list. |
| `accounts`required | array of string (Address) | Account addresses in ascending cursor order. |

### AlreadyPublished

The registry already holds this exact publication; nothing to send.

| Field | Type | Description |
| --- | --- | --- |
| `status`required | "published" |  |
| `kind`required | EntityKind | Kind of entity being published. |
| `name`required | string (EntityName) | Entity name. Starts with a letter or '\_', contains only letters, digits and '\_', at most 128 characters. |
| `address`required | string (Address) | Ethereum-style address, with or without a 0x prefix. |
| `owner`required | string (Address) | Ethereum-style address, with or without a 0x prefix. |
| `content_hash`required | string (Hash32) | 32-byte hex value. |

### AuthRequest

Auth request.

| Field | Type | Description |
| --- | --- | --- |
| `address`required | string (Address) | Ethereum-style address, with or without a 0x prefix. |
| `nonce`required | string | The nonce \`/nonce\` issued to \`address\`. |
| `signature`required | string | The wallet's \`personal\_sign\` (EIP-191) signature of the \`message\` issued with \`nonce\`, as 65-byte hex. |

### AuthResponse

Auth response.

| Field | Type | Description |
| --- | --- | --- |
| `access_token`required | string | JWT access token for protected chain endpoints. |

### ConditionInfoResponse

Condition information. The Solidity source is an execution input kept in local storage or a verified artifact and is never served.

| Field | Type | Description |
| --- | --- | --- |
| `name`required | string | Condition name. |
| `args_count`required | integer | Number of arguments (uint32), derived from the source and registered on chain. (0–4294967295) |
| `runtime_code`required | string, nullable | Deployed runtime bytecode as 0x-prefixed hex, or null while the registry does not hold it. |
| `owner`required | string (Address) | Ethereum-style address, with or without a 0x prefix. |
| `address`required | string | On-chain address once published; "0x0" for a local simulation entity. |

### ConfirmRequest

Confirm a publication transaction the owner's wallet sent.

| Field | Type | Description |
| --- | --- | --- |
| `name`required | string (EntityName) | Entity name. Starts with a letter or '\_', contains only letters, digits and '\_', at most 128 characters. |
| `content_hash`required | string (Hash32) | 32-byte hex value. |
| `tx_hash`required | string | Hash of the sent publication transaction. |

### ConfirmResponse

The transaction was mined with status 1 and carries exactly one matching registry event naming the entity, owner, content and metadata hashes.

| Field | Type | Description |
| --- | --- | --- |
| `status`required | "mined" |  |
| `kind`required | EntityKind | Kind of entity being published. |
| `name`required | string (EntityName) | Entity name. Starts with a letter or '\_', contains only letters, digits and '\_', at most 128 characters. |
| `tx_hash`required | string |  |
| `block_number`required | integer (int64) | (≥ 0) |
| `address`required | string (Address) | Ethereum-style address, with or without a 0x prefix. |
| `owner`required | string (Address) | Ethereum-style address, with or without a 0x prefix. |
| `content_hash`required | string (Hash32) | 32-byte hex value. |

### ConnectorDimension

Single connector dimension definition.

| Field | Type | Description |
| --- | --- | --- |
| `transformations`required | [array of TransformationCallDef](https://decentralised.art/api-reference#schema-TransformationCallDef) | Ordered transformation calls for this dimension. |
| `composite` | string | Connected composite connector name. Omitted or empty string means none. |
| `bindings` | map of string | Slot bindings map for composite connectors. Omitted means no bindings. Keys are canonical decimal slot ids and values are connector names. |

### ConnectorInfoResponse

Connector definition payload returned by GET /connector/{name}.

| Field | Type | Description |
| --- | --- | --- |
| `name`required | string | Connector name. |
| `dimensions`required | [array of ConnectorDimension](https://decentralised.art/api-reference#schema-ConnectorDimension) | Ordered dimension definitions. |
| `condition_name`required | string | Condition name. Empty string means no condition. |
| `condition_args`required | array of integer (int32) | Condition arguments. |
| `static_ri`required | [map of RunningInstance](https://decentralised.art/api-reference#schema-RunningInstance) | Static running-instance map keyed by decimal position; empty object when none. |
| `owner`required | string (Address) | Ethereum-style address, with or without a 0x prefix. |
| `address`required | string | On-chain address once published; "0x0" for a local simulation entity. |
| `format_hash`required | string | Derived format hash for this connector definition. |

### CreateConditionRequest

Create condition request

| Field | Type | Description |
| --- | --- | --- |
| `name`required | string (EntityName) | Entity name. Starts with a letter or '\_', contains only letters, digits and '\_', at most 128 characters. |
| `sol_src`required | string | Solidity source code |

### CreateConditionResponse

Create condition response

| Field | Type | Description |
| --- | --- | --- |
| `name`required | string | Name of the created condition |
| `owner`required | string (Address) | Ethereum-style address, with or without a 0x prefix. |
| `address`required | string | Always "0x0"; the entity is local until published through /publish/condition. |
| `args_count`required | integer | Number of arguments (uint32) parsed from the Solidity source. (0–4294967295) |

### CreateConnectorRequest

Connector create request payload.

| Field | Type | Description |
| --- | --- | --- |
| `name`required | string (EntityName) | Entity name. Starts with a letter or '\_', contains only letters, digits and '\_', at most 128 characters. |
| `dimensions`required | [array of ConnectorDimension](https://decentralised.art/api-reference#schema-ConnectorDimension) | Ordered dimension definitions. |
| `condition_name` | string | Condition name. Omitted or empty string means no condition. |
| `condition_args` | array of integer (int32) | Condition arguments. Omitted means no condition arguments. |
| `static_ri` | [map of RunningInstance](https://decentralised.art/api-reference#schema-RunningInstance) | Optional static running-instance map. Keys are canonical decimal positions (for example "0", "3", "5"). |

### CreateConnectorResponse

Connector create response payload.

| Field | Type | Description |
| --- | --- | --- |
| `name`required | string | Connector name. |
| `owner`required | string (Address) | Ethereum-style address, with or without a 0x prefix. |
| `address`required | string | Always "0x0"; the entity is local until published through /publish/connector. |
| `format_hash`required | string | Derived format hash for this connector definition. |

### CreateTransformationRequest

Create transformation request

| Field | Type | Description |
| --- | --- | --- |
| `name`required | string (EntityName) | Entity name. Starts with a letter or '\_', contains only letters, digits and '\_', at most 128 characters. |
| `sol_src`required | string | Solidity source code |

### CreateTransformationResponse

Create transformation response

| Field | Type | Description |
| --- | --- | --- |
| `name`required | string | Name of the created transformation |
| `owner`required | string (Address) | Ethereum-style address, with or without a 0x prefix. |
| `address`required | string | Always "0x0"; the entity is local until published through /publish/transformation. |
| `args_count`required | integer | Number of arguments (uint32) parsed from the Solidity source. (0–4294967295) |

### ErrorResponse

Error response

| Field | Type | Description |
| --- | --- | --- |
| `message`required | string | Human-readable message. |

### ExecuteRequest

Execute request payload.

| Field | Type | Description |
| --- | --- | --- |
| `connector_name`required | string | Connector name to execute. |
| `particles_count`required | integer or string | Number of particles to generate. The backend accepts protobuf JSON uint32 values between 1 and 65536. |
| `dynamic_ri` | [map of RunningInstance](https://decentralised.art/api-reference#schema-RunningInstance) | Dynamic running-instance overrides keyed by canonical decimal RI position. Omitted means no overrides. At most 4096 entries. |

### ExecuteResponse

On-chain execution result. Anyone can check it by calling the runner at the same block.

| Field | Type | Description |
| --- | --- | --- |
| `block_number`required | integer (int64) | Block the call was pinned to. (≥ 0) |
| `block_hash`required | string | Hash of that block. |
| `runner`required | string | Runner contract address that executed the call. |
| `registry`required | string | Registry contract address the runner looked the connector up in. |
| `particles`required | [array of ParticlesResultItem](https://decentralised.art/api-reference#schema-ParticlesResultItem) | Execution result list. |

### FeedCursor

Pagination cursor metadata for \`/feed\`.

| Field | Type | Description |
| --- | --- | --- |
| `has_more`required | boolean | Whether another older page is available. |
| `next_before`required | string, nullable | Cursor to pass as \`before\` for the next older page. |

### FeedEventPayload

Compact feed payload for discovery. Full entity details are available through the exact entity endpoints.

| Field | Type | Description |
| --- | --- | --- |
| `type`required | "connector" \| "transformation" \| "condition" | Entity kind represented by the feed item. |
| `name`required | string | Entity name. |
| `owner`required | string (Address) | Ethereum-style address, with or without a 0x prefix. |

### FeedItem

One projected chain feed item.

| Field | Type | Description |
| --- | --- | --- |
| `feed_id`required | string | Stable feed identity for this logical entity event. |
| `event_type`required | FeedEventType | Supported feed event type. |
| `status`required | FeedEventStatus | Chain-finality or removal status for a feed item. |
| `visible`required | boolean | False when the item should be hidden, for example after removal. |
| `tx_hash`required | string | Source transaction hash. |
| `block_number`required | integer (int64) | Source block number. (≥ 0) |
| `tx_index`required | integer (int64) | Source transaction index inside the block. (≥ 0) |
| `log_index`required | integer (int64) | Source log index. (≥ 0) |
| `history_cursor`required | string | Cursor identifying this feed item's position in history. |
| `created_at_ms`required | integer (int64) | Feed creation time in Unix milliseconds. (≥ 0) |
| `updated_at_ms`required | integer (int64) | Feed update time in Unix milliseconds. (≥ 0) |
| `projector_version`required | integer | Feed projector version that produced this item. (≥ 1) |
| `payload`required | [FeedEventPayload](https://decentralised.art/api-reference#schema-FeedEventPayload) | Compact feed payload for discovery. Full entity details are available through the exact entity endpoints. |

### FeedPage

Newest-first feed page.

| Field | Type | Description |
| --- | --- | --- |
| `limit`required | integer | Page size used for this response. (1–256) |
| `cursor`required | [FeedCursor](https://decentralised.art/api-reference#schema-FeedCursor) | Pagination cursor metadata for \`/feed\`. |
| `items`required | [array of FeedItem](https://decentralised.art/api-reference#schema-FeedItem) | Feed items in newest-first order. |

### FormatHashCursorState

Cursor state for the format hash list.

| Field | Type | Description |
| --- | --- | --- |
| `has_more`required | boolean | Indicates whether more format hashes are available. |
| `next_after`required | string, nullable | Format hash cursor for the next page, or null when exhausted. |

### FormatInfoResponse

Connector membership and scalar labels for one format hash.

| Field | Type | Description |
| --- | --- | --- |
| `format_hash`required | string (FormatHash) | 32-byte connector format hash, with or without a 0x prefix. |
| `limit`required | integer | Page size used for connector names. (1–256) |
| `total_connectors`required | integer | Total number of connectors using this format hash. (≥ 0) |
| `cursor`required | [FormatNameCursorState](https://decentralised.art/api-reference#schema-FormatNameCursorState) | Cursor state for connector names within one format. |
| `scalars`required | array of string | Scalar labels encoded as \`scalar:tail\_id\` entries. |
| `connectors`required | array of string | Connector names using this format hash. |

### FormatListResponse

Cursor-based format hash list response.

| Field | Type | Description |
| --- | --- | --- |
| `limit`required | integer | Page size used for this response. (1–256) |
| `total_formats`required | integer | Total number of known format hashes. (≥ 0) |
| `cursor`required | [FormatHashCursorState](https://decentralised.art/api-reference#schema-FormatHashCursorState) | Cursor state for the format hash list. |
| `formats`required | array of string (FormatHash) | Format hashes in ascending cursor order. |

### FormatNameCursorState

Cursor state for connector names within one format.

| Field | Type | Description |
| --- | --- | --- |
| `has_more`required | boolean | Indicates whether more connector names are available. |
| `next_after`required | string, nullable | Connector name cursor for the next page, or null when exhausted. |

### NameCursorState

Cursor state for one ownership list.

| Field | Type | Description |
| --- | --- | --- |
| `has_more`required | boolean | Indicates whether more names are available. |
| `next_after`required | string, nullable | Cursor token for the next page (or null when exhausted). |

### NonceResponse

Nonce response.

| Field | Type | Description |
| --- | --- | --- |
| `nonce`required | string | One-time nonce identifying \`message\`; submit it to \`/auth\`. |
| `message`required | string | EIP-4361 sign-in message for the wallet to sign with \`personal\_sign\`. It names the site with its scheme, the checksummed address, the chain ID, the nonce, and when it was issued and expires. |

### ParticlesResultItem

One returned scalar stream for an execution path.

| Field | Type | Description |
| --- | --- | --- |
| `path`required | string | Fully-qualified execution path. |
| `data`required | array of integer | Output particle values for this path (uint32). |

### PreparedPublication

The transaction the owner's wallet must send to publish the entity.

| Field | Type | Description |
| --- | --- | --- |
| `status`required | "prepared" |  |
| `kind`required | EntityKind | Kind of entity being published. |
| `name`required | string (EntityName) | Entity name. Starts with a letter or '\_', contains only letters, digits and '\_', at most 128 characters. |
| `transaction`required | [UnsignedTransaction](https://decentralised.art/api-reference#schema-UnsignedTransaction) | Registry call ready for eth\_sendTransaction; quantities are hex, as wallets expect. The calldata carries an empty owner signature, which the registry accepts because the owner is the sender. |
| `address`required | string (Address) | Ethereum-style address, with or without a 0x prefix. |
| `content_hash`required | string (Hash32) | 32-byte hex value. |
| `publication_nonce`required | integer (int64) | Owner's publication nonce bound into the transaction. (≥ 0) |
| `deadline`required | integer (int64) | Unix seconds after which the registry refuses the transaction. (≥ 0) |
| `signing` | [SigningFields](https://decentralised.art/api-reference#schema-SigningFields) | Present only when the request set \`relay\`. Merged into \`transaction\`, these complete an EIP-1559 transaction an owner can sign offline. Quantities are hex. |

### PrepareRequest

Prepare the publication of an entity the caller created on this server.

| Field | Type | Description |
| --- | --- | --- |
| `name`required | string (EntityName) | Entity name. Starts with a letter or '\_', contains only letters, digits and '\_', at most 128 characters. |
| `relay` | boolean | Also return \`signing\`, what an offline signer needs to complete the transaction for POST /publish/{kind}/send. Leave unset for a browser wallet, which chooses its own nonce and fees. (default false) |

### PrepareResponse

Either the transaction the owner's wallet must send, or, when the registry already holds this exact publication, the existing registration.

One of: [PreparedPublication](https://decentralised.art/api-reference#schema-PreparedPublication), [AlreadyPublished](https://decentralised.art/api-reference#schema-AlreadyPublished)

### PublishError

Publication error. Optional fields appear only when relevant.

| Field | Type | Description |
| --- | --- | --- |
| `message`required | string | Human-readable message. |
| `status` | "pending" | Present on 202 while the transaction is not mined yet. |
| `tx_hash` | string | Transaction the error refers to. |
| `missing` | array of string | Connector dependencies absent from the target registry. |
| `mismatched` | array of string | Connector dependencies registered with a different artifact. |

### RunningInstance

Running-instance coordinates pair.

| Field | Type | Description |
| --- | --- | --- |
| `start_point`required | integer | Start point index (uint32). (0–4294967295) |
| `transformation_shift`required | integer | Transformation shift index (uint32). (0–4294967295) |

### SendRequest

Broadcast a publication transaction the owner signed offline.

| Field | Type | Description |
| --- | --- | --- |
| `name`required | string (EntityName) | Entity name. Starts with a letter or '\_', contains only letters, digits and '\_', at most 128 characters. |
| `content_hash`required | string (Hash32) | 32-byte hex value. |
| `raw_tx`required | string | Signed type-2 transaction: \`transaction\` merged with \`signing\` from a relay prepare, as \`0x02 \|\| rlp(...)\`. |

### SendResponse

The provider accepted the transaction, or already held it. Confirm it with POST /publish/{kind}.

| Field | Type | Description |
| --- | --- | --- |
| `status`required | "pending" |  |
| `tx_hash`required | string | Hash of the broadcast transaction. |

### SigningFields

Present only when the request set \`relay\`. Merged into \`transaction\`, these complete an EIP-1559 transaction an owner can sign offline. Quantities are hex.

| Field | Type | Description |
| --- | --- | --- |
| `type`required | "0x2" |  |
| `nonce`required | string | The owner's pending account nonce. |
| `maxFeePerGas`required | string |  |
| `maxPriorityFeePerGas`required | string |  |
| `value`required | "0x0" |  |

### TransformationCallDef

Transformation invocation in a connector dimension.

| Field | Type | Description |
| --- | --- | --- |
| `name`required | string | Transformation name |
| `args` | array of integer (int32) | Transformation arguments. Omitted means no arguments. |

### TransformationInfoResponse

Transformation information. The Solidity source is an execution input kept in local storage or a verified artifact and is never served.

| Field | Type | Description |
| --- | --- | --- |
| `name`required | string | Transformation name. |
| `args_count`required | integer | Number of arguments (uint32), derived from the source and registered on chain. (0–4294967295) |
| `runtime_code`required | string, nullable | Deployed runtime bytecode as 0x-prefixed hex, or null while the registry does not hold it. |
| `owner`required | string (Address) | Ethereum-style address, with or without a 0x prefix. |
| `address`required | string | On-chain address once published; "0x0" for a local simulation entity. |

### UnsignedTransaction

Registry call ready for eth\_sendTransaction; quantities are hex, as wallets expect. The calldata carries an empty owner signature, which the registry accepts because the owner is the sender.

| Field | Type | Description |
| --- | --- | --- |
| `from`required | string (Address) | Ethereum-style address, with or without a 0x prefix. |
| `to`required | string (Address) | Ethereum-style address, with or without a 0x prefix. |
| `data`required | string | Hex-encoded calldata. |
| `chainId`required | string | Chain id as a hex quantity. |
| `gas`required | string | Gas limit (estimate plus headroom) as a hex quantity. |

### VersionResponse

Version information.

| Field | Type | Description |
| --- | --- | --- |
| `build_timestamp`required | string | ISO-8601 build timestamp of the running server |
| `version`required | string | Human-readable API version |

## Services schemas

### UserPublic

A user's public record. Fields are snake\_case.

| Field | Type | Description |
| --- | --- | --- |
| `id`required | string | The user's Ethereum address (EIP-55 checksummed). Users are identified by address. |
| `display_name`required | string, nullable | Name shown on the platform. |
| `status`required | "active" \| "suspended" \| "deleted" | Account status. |
| `roles`required | array of "user" \| "admin" \| "moderator" | Roles of the user. |
| `profile_json`required | object | Free-form profile data, such as public.nickname, public.bio and public.kind. |
| `created_at`required | string (date-time) | When the user first signed in. |
| `updated_at`required | string (date-time) | Last profile change. |
| `last_login_at`required | string (date-time), nullable | Last sign-in. |

### WorldDescriptor

A published World. Fields are camelCase.

| Field | Type | Description |
| --- | --- | --- |
| `id`required | string | World id, used in asset URLs. |
| `slug, name, version, description`required | string | From the World's manifest. |
| `entryUrn`required | string | Where the World's entry page is served, under /world-assets. |
| `entryPath`required | string | Entry file inside the bundle. |
| `runtime`required | "iframe" | How the World runs. |
| `surfaces`required | array of "world-page" \| "studio-plugin" | Where the World can be shown. |
| `permissions`required | array of string | Permissions granted to the World. |
| `shortDescription, heroLabel, accentColor, preview` | string | Optional presentation details from the manifest. |
| `acceptedFormatHashes`required | array of string | Formats the World understands. |
| `acceptedConnectorSets`required | array of { connectors, optionalConnectors } | Connector names the World understands. |
| `valueLimits` | object | Ranges for particlesCount and for values on specific output paths. |
| `ownerId`required | string | Address of the user who uploaded it. |
| `bundleHash, manifestHash`required | string | Hashes of the uploaded bundle and its manifest. |
| `status`required | "active" \| "deleted" | World status. |
| `createdAt, updatedAt`required | string (date-time) | Timestamps. |

## Specification

-   The chain API is specified in OpenAPI 3.0 in [decentralised-art/api-spec](https://github.com/decentralised-art/api-spec), which is also published as [browsable docs](https://decentralised-art.github.io/api-spec/). The specification this reference is built from is also served as [openapi/chain.json](https://decentralised.art/openapi/chain.json). The live server reports its version at `GET /version` (currently 0.4.0).
-   The services API is documented here from [services-backend](https://github.com/decentralised-art/services-backend).
-   Live availability of both APIs is on [API status](https://decentralised.art/api-status).
-   For AI agents, [llms.txt](https://decentralised.art/llms.txt) lists the documentation in markdown and [llms-full.txt](https://decentralised.art/llms-full.txt) contains all of it in one file. Every docs page has a markdown version at the same address with `.md` added, for example [/api-reference.md](https://decentralised.art/api-reference.md).

Source: https://decentralised.art/api-reference
