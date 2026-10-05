from __future__ import annotations

from typing import Any, Dict, Iterable, List, Sequence, Tuple

from ..config import DEFAULT_PREFERRED_TRANSFORMATION_PAIRS, MAX_TIMEOUT_SECONDS, MIN_TIMEOUT_SECONDS
from ..context import context_from_params
from ..errors import ValidationError
from ..artifacts import resolve_artifact_path
from ..lifecycle import confirm_existing, publish_recorded
from ..schemas import array_schema, boolean_schema, integer_schema, number_schema, object_schema, string_schema

MAX_PAGE_LIMIT = 256
MAX_STREAM_REPLAY_LIMIT = 2048
MAX_PARTICLES_COUNT = 65536

TIMEOUT_SCHEMA = number_schema(minimum=MIN_TIMEOUT_SECONDS, maximum=MAX_TIMEOUT_SECONDS)
PAGE_LIMIT_SCHEMA = integer_schema(minimum=1, maximum=MAX_PAGE_LIMIT)
STREAM_REPLAY_LIMIT_SCHEMA = integer_schema(minimum=1, maximum=MAX_STREAM_REPLAY_LIMIT)
PARTICLES_COUNT_SCHEMA = integer_schema(minimum=1, maximum=MAX_PARTICLES_COUNT)
TRANSFORMATION_PAIR_SCHEMA = array_schema(string_schema(min_length=1), min_items=2, max_items=2)
TRANSFORMATION_PAIRS_SCHEMA = array_schema(TRANSFORMATION_PAIR_SCHEMA, min_items=1)


def _optional_int(params: Dict[str, Any], key: str, *, default: int, minimum: int, maximum: int) -> int:
    if key not in params or params[key] is None:
        return default
    value = params[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"params.{key} must be an integer.", details={"path": f"params.{key}", "expected_type": "integer"})
    if value < minimum or value > maximum:
        raise ValidationError(f"params.{key} must be between {minimum} and {maximum}.", details={"path": f"params.{key}", "minimum": minimum, "maximum": maximum})
    return value


def _transformation_pairs(value: Any, *, field_name: str, default: Iterable[Tuple[str, str]]) -> List[Tuple[str, str]]:
    raw = list(default) if value is None else value
    if not isinstance(raw, (list, tuple)) or isinstance(raw, (str, bytes)):
        raise ValidationError(f"params.{field_name} must be an array of [add, subtract] pairs.", details={"path": f"params.{field_name}"})
    if len(raw) == 0:
        raise ValidationError(f"params.{field_name} must include at least one pair.", details={"path": f"params.{field_name}", "min_items": 1})
    pairs: List[Tuple[str, str]] = []
    for index, item in enumerate(raw):
        if not isinstance(item, (list, tuple)) or isinstance(item, (str, bytes)) or len(item) != 2:
            raise ValidationError(
                f"params.{field_name}[{index}] must contain exactly two names.",
                details={"path": f"params.{field_name}[{index}]", "expected_items": 2},
            )
        add, subtract = str(item[0]).strip(), str(item[1]).strip()
        if not add or not subtract:
            raise ValidationError(
                f"params.{field_name}[{index}] names must be non-empty strings.",
                details={"path": f"params.{field_name}[{index}]"},
            )
        pairs.append((add, subtract))
    return pairs


def build_parent_connector(child_names: Sequence[str], *, name: str) -> Dict[str, Any]:
    return {
        "name": str(name),
        "dimensions": [{"transformations": [], "composite": child_name, "bindings": {}} for child_name in child_names],
        "condition_name": "",
        "condition_args": [],
        "static_ri": {},
    }


def register(registry) -> None:
    @registry.tool(
        namespace="core",
        name="connector_exists",
        description="Check whether a connector exists on decentralised.art.",
        input_schema=object_schema({"name": string_schema(min_length=1), "api_base": string_schema(), "timeout": TIMEOUT_SCHEMA}, required=["name"]),
    )
    def _connector_exists(params: Dict[str, Any]) -> Dict[str, Any]:
        with context_from_params(params) as ctx:
            return {"name": params["name"], "exists": ctx.client().connector_exists(str(params["name"]))}

    @registry.tool(
        namespace="core",
        name="get_nonce",
        description="Fetch a one-time auth nonce and the sign-in message when supplied by the API.",
        input_schema=object_schema({"address": string_schema(min_length=1), "api_base": string_schema(), "timeout": TIMEOUT_SCHEMA}, required=["address"]),
    )
    def _get_nonce(params: Dict[str, Any]) -> Dict[str, Any]:
        with context_from_params(params) as ctx:
            return {"address": params["address"], **ctx.client().get_nonce(str(params["address"]))}

    @registry.tool(
        namespace="core",
        name="get_connector",
        description="Fetch a connector payload by name.",
        input_schema=object_schema({"name": string_schema(min_length=1), "api_base": string_schema(), "timeout": TIMEOUT_SCHEMA}, required=["name"]),
    )
    def _get_connector(params: Dict[str, Any]) -> Dict[str, Any]:
        with context_from_params(params) as ctx:
            return ctx.client().get_connector(str(params["name"]))

    @registry.tool(
        namespace="core",
        name="get_transformation",
        description="Fetch a transformation payload by name.",
        input_schema=object_schema({"name": string_schema(min_length=1), "api_base": string_schema(), "timeout": TIMEOUT_SCHEMA}, required=["name"]),
    )
    def _get_transformation(params: Dict[str, Any]) -> Dict[str, Any]:
        with context_from_params(params) as ctx:
            return ctx.client().get_transformation(str(params["name"]))

    @registry.tool(
        namespace="core",
        name="get_condition",
        description="Fetch a condition payload by name.",
        input_schema=object_schema({"name": string_schema(min_length=1), "api_base": string_schema(), "timeout": TIMEOUT_SCHEMA}, required=["name"]),
    )
    def _get_condition(params: Dict[str, Any]) -> Dict[str, Any]:
        with context_from_params(params) as ctx:
            return ctx.client().get_condition(str(params["name"]))

    @registry.tool(
        namespace="core",
        name="transformation_exists",
        description="Check whether a transformation exists on decentralised.art.",
        input_schema=object_schema({"name": string_schema(min_length=1), "api_base": string_schema(), "timeout": TIMEOUT_SCHEMA}, required=["name"]),
    )
    def _transformation_exists(params: Dict[str, Any]) -> Dict[str, Any]:
        with context_from_params(params) as ctx:
            return {"name": params["name"], "exists": ctx.client().transformation_exists(str(params["name"]))}

    @registry.tool(
        namespace="core",
        name="condition_exists",
        description="Check whether a condition exists on decentralised.art.",
        input_schema=object_schema({"name": string_schema(min_length=1), "api_base": string_schema(), "timeout": TIMEOUT_SCHEMA}, required=["name"]),
    )
    def _condition_exists(params: Dict[str, Any]) -> Dict[str, Any]:
        with context_from_params(params) as ctx:
            return {"name": params["name"], "exists": ctx.client().condition_exists(str(params["name"]))}

    @registry.tool(
        namespace="core",
        name="get_feed_page",
        description="Fetch a page from the decentralised.art event feed.",
        input_schema=object_schema(
            {
                "limit": PAGE_LIMIT_SCHEMA,
                "before": string_schema(),
                "type": string_schema(),
                "include_unfinalized": boolean_schema(),
                "api_base": string_schema(),
                "timeout": TIMEOUT_SCHEMA,
            },
        ),
    )
    def _get_feed_page(params: Dict[str, Any]) -> Dict[str, Any]:
        with context_from_params(params) as ctx:
            return ctx.client().get_feed_page(
                limit=_optional_int(params, "limit", default=100, minimum=1, maximum=MAX_PAGE_LIMIT),
                before=params.get("before"),
                event_type=params.get("type"),
                include_unfinalized=params.get("include_unfinalized"),
            )

    @registry.tool(
        namespace="core",
        name="get_feed_stream_replay",
        description="Read a bounded replay from the decentralised.art event feed SSE stream.",
        input_schema=object_schema(
            {
                "since_seq": integer_schema(minimum=0),
                "limit": STREAM_REPLAY_LIMIT_SCHEMA,
                "api_base": string_schema(),
                "timeout": TIMEOUT_SCHEMA,
            },
        ),
    )
    def _get_feed_stream_replay(params: Dict[str, Any]) -> Dict[str, Any]:
        with context_from_params(params) as ctx:
            return ctx.client().get_feed_stream_replay(
                since_seq=_optional_int(params, "since_seq", default=0, minimum=0, maximum=2**63 - 1),
                limit=_optional_int(params, "limit", default=200, minimum=1, maximum=MAX_STREAM_REPLAY_LIMIT),
            )

    @registry.tool(
        namespace="core",
        name="list_formats",
        description="List formats known to decentralised.art.",
        input_schema=object_schema({"limit": PAGE_LIMIT_SCHEMA, "after": string_schema(), "api_base": string_schema(), "timeout": TIMEOUT_SCHEMA}),
    )
    def _list_formats(params: Dict[str, Any]) -> Dict[str, Any]:
        with context_from_params(params) as ctx:
            return ctx.client().list_formats(limit=_optional_int(params, "limit", default=100, minimum=1, maximum=MAX_PAGE_LIMIT), after=params.get("after"))

    @registry.tool(
        namespace="core",
        name="get_format",
        description="Fetch one format and its features.",
        input_schema=object_schema({"format_hash": string_schema(min_length=1), "limit": PAGE_LIMIT_SCHEMA, "after": string_schema(), "api_base": string_schema(), "timeout": TIMEOUT_SCHEMA}, required=["format_hash"]),
    )
    def _get_format(params: Dict[str, Any]) -> Dict[str, Any]:
        with context_from_params(params) as ctx:
            return ctx.client().get_format(str(params["format_hash"]), limit=_optional_int(params, "limit", default=256, minimum=1, maximum=MAX_PAGE_LIMIT), after=params.get("after"))

    @registry.tool(
        namespace="core",
        name="get_account",
        description="Fetch account-owned connectors, transformations, and conditions for an address.",
        input_schema=object_schema(
            {
                "address": string_schema(min_length=1),
                "limit": PAGE_LIMIT_SCHEMA,
                "after_connectors": string_schema(),
                "after_transformations": string_schema(),
                "after_conditions": string_schema(),
                "api_base": string_schema(),
                "timeout": TIMEOUT_SCHEMA,
            },
            required=["address"],
        ),
    )
    def _get_account(params: Dict[str, Any]) -> Dict[str, Any]:
        with context_from_params(params) as ctx:
            return ctx.client().get_account(
                str(params["address"]),
                limit=_optional_int(params, "limit", default=256, minimum=1, maximum=MAX_PAGE_LIMIT),
                after_connectors=params.get("after_connectors"),
                after_transformations=params.get("after_transformations"),
                after_conditions=params.get("after_conditions"),
            )

    @registry.tool(
        namespace="core",
        name="create_connector",
        description="Create a server-local connector draft. Does not publish or spend gas.",
        input_schema=object_schema({"payload": object_schema(), "private_key": string_schema(), "api_base": string_schema(), "timeout": TIMEOUT_SCHEMA}, required=["payload"]),
    )
    def _create_connector(params: Dict[str, Any]) -> Dict[str, Any]:
        with context_from_params(params) as ctx:
            return ctx.client().post_connector(dict(params["payload"]), ctx.account())

    @registry.tool(
        namespace="core",
        name="create_transformation",
        description="Create a server-local transformation draft. Does not publish or spend gas.",
        input_schema=object_schema({"payload": object_schema(), "private_key": string_schema(), "api_base": string_schema(), "timeout": TIMEOUT_SCHEMA}, required=["payload"]),
    )
    def _create_transformation(params: Dict[str, Any]) -> Dict[str, Any]:
        with context_from_params(params) as ctx:
            return ctx.client().post_transformation(dict(params["payload"]), ctx.account())

    @registry.tool(
        namespace="core",
        name="create_condition",
        description="Create a server-local condition draft. Does not publish or spend gas.",
        input_schema=object_schema({"payload": object_schema(), "private_key": string_schema(), "api_base": string_schema(), "timeout": TIMEOUT_SCHEMA}, required=["payload"]),
    )
    def _create_condition(params: Dict[str, Any]) -> Dict[str, Any]:
        with context_from_params(params) as ctx:
            return ctx.client().post_condition(dict(params["payload"]), ctx.account())

    @registry.tool(
        namespace="core", name="simulate_connector",
        description="Simulate a connector draft locally on the server without login; returns particles without chain provenance or publication.",
        input_schema=object_schema({"connector_name": string_schema(min_length=1), "particles_count": PARTICLES_COUNT_SCHEMA,
            "dynamic_ri": object_schema(), "api_base": string_schema(), "timeout": TIMEOUT_SCHEMA},
            required=["connector_name", "particles_count"]),
    )
    def _simulate(params):
        with context_from_params(params) as ctx:
            particles = ctx.client().simulate_connector(str(params["connector_name"]), int(params["particles_count"]), dict(params.get("dynamic_ri") or {}))
            return {"particles": particles, "execution_mode": "simulation"}

    publication_schema = {"kind": string_schema(min_length=1), "name": string_schema(min_length=1),
        "private_key": string_schema(), "api_base": string_schema(), "timeout": TIMEOUT_SCHEMA}

    @registry.tool(namespace="core", name="prepare_publication",
        description="Prepare a draft for owner-paid chain publication and inspect relay transaction/fee fields. Does not sign or send.",
        input_schema=object_schema(publication_schema, required=["kind", "name"]))
    def _prepare_publication(params):
        with context_from_params(params) as ctx:
            return ctx.client().publish_prepare(ctx.account(), params["kind"], params["name"])

    @registry.tool(namespace="core", name="publish_entity",
        description="Explicitly spend owner gas to publish a draft (dependencies must already be published). Publish serially per owner and resolve pending receipts first. Signs locally, relays once, and confirms. Requires fee limits and a persistent record path within the artifact root. Reusing the same record confirms without rebroadcasting.",
        input_schema=object_schema({**publication_schema,
            "record_path": string_schema(min_length=1), "chain_id": integer_schema(minimum=1),
            "max_fee_per_gas": integer_schema(minimum=1), "max_total_fee": integer_schema(minimum=1),
            "max_confirm_attempts": integer_schema(minimum=1, maximum=200)},
            required=["kind", "name", "record_path", "max_fee_per_gas", "max_total_fee"]))
    def _publish(params):
        with context_from_params(params) as ctx:
            return publish_recorded(ctx.client(), ctx.account(), params["kind"], params["name"],
                resolve_artifact_path(params["record_path"]), chain_id=params.get("chain_id", 11155111),
                max_fee_per_gas=params["max_fee_per_gas"], max_total_fee=params["max_total_fee"],
                max_confirm_attempts=params.get("max_confirm_attempts", 20))

    @registry.tool(namespace="core", name="confirm_publication",
        description="Check the receipt of an existing publication transaction; does not sign or send another transaction.",
        input_schema=object_schema({**publication_schema, "content_hash": string_schema(min_length=1), "tx_hash": string_schema(min_length=1)},
            required=["kind", "name", "content_hash", "tx_hash"]))
    def _confirm_publication(params):
        with context_from_params(params) as ctx:
            return confirm_existing(ctx.client(), ctx.account(), params["kind"], params["name"], params["content_hash"], params["tx_hash"])

    @registry.tool(
        namespace="core",
        name="execute_connector",
        description="Read a published connector from the chain runner without login or gas and return particles with block_number, block_hash, runner and registry provenance.",
        input_schema=object_schema(
            {
                "connector_name": string_schema(min_length=1),
                "particles_count": PARTICLES_COUNT_SCHEMA,
                "dynamic_ri": object_schema(),
                "api_base": string_schema(),
                "timeout": TIMEOUT_SCHEMA,
            },
            required=["connector_name", "particles_count"],
        ),
    )
    def _execute_connector(params: Dict[str, Any]) -> Dict[str, Any]:
        dynamic_ri = params["dynamic_ri"] if "dynamic_ri" in params and params["dynamic_ri"] is not None else {}
        with context_from_params(params) as ctx:
            execution = ctx.client().execute_connector(
                connector_name=str(params["connector_name"]),
                particles_count=int(params["particles_count"]),
                dynamic_ri=dict(dynamic_ri),
            )
            return {**execution, "execution_mode": "chain"}

    @registry.tool(
        namespace="core",
        name="resolve_transformation_pair",
        description="Resolve the first supported add/subtract transformation pair on the network.",
        input_schema=object_schema({"pairs": TRANSFORMATION_PAIRS_SCHEMA, "api_base": string_schema(), "timeout": TIMEOUT_SCHEMA}),
    )
    def _resolve_pair(params: Dict[str, Any]) -> Dict[str, Any]:
        pairs = _transformation_pairs(params.get("pairs"), field_name="pairs", default=DEFAULT_PREFERRED_TRANSFORMATION_PAIRS)
        with context_from_params(params) as ctx:
            pair = ctx.client().resolve_preferred_transformation_pair(pairs)
            return {"add": pair.add, "subtract": pair.subtract}

    @registry.tool(
        namespace="core",
        name="ensure_preflight",
        description="Authenticate, ensure required connectors exist, and resolve a preferred transformation pair.",
        input_schema=object_schema(
            {
                "required_connectors": array_schema(string_schema(min_length=1), min_items=1),
                "preferred_transformation_pairs": TRANSFORMATION_PAIRS_SCHEMA,
                "private_key": string_schema(),
                "api_base": string_schema(),
                "timeout": TIMEOUT_SCHEMA,
            },
            required=["required_connectors"],
        ),
    )
    def _ensure_preflight(params: Dict[str, Any]) -> Dict[str, Any]:
        pairs = _transformation_pairs(params.get("preferred_transformation_pairs"), field_name="preferred_transformation_pairs", default=DEFAULT_PREFERRED_TRANSFORMATION_PAIRS)
        with context_from_params(params) as ctx:
            acct = ctx.account()
            pair = ctx.client().ensure_preflight(
                acct,
                required_connectors=list(params["required_connectors"]),
                preferred_transformation_pairs=pairs,
            )
            return {"add": pair.add, "subtract": pair.subtract, "address": acct.address}

    @registry.tool(
        namespace="core",
        name="build_parent_connector",
        description="Build a generic structural parent connector over child connector names.",
        input_schema=object_schema({"name": string_schema(min_length=1), "child_names": array_schema(string_schema(min_length=1), min_items=1)}, required=["name", "child_names"]),
    )
    def _build_parent(params: Dict[str, Any]) -> Dict[str, Any]:
        return build_parent_connector(params["child_names"], name=params["name"])
