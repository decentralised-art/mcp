from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import requests
from eth_account.messages import encode_defunct

from .api_contracts import api_path, validate_query, validate_request, validate_response
from .lifecycle import LifecycleClientMixin, execution_particles
from .models import ChainCursor, TransformationPair


class DecentralisedArtClient(LifecycleClientMixin):
    def __init__(self, base_url: str, timeout: float = 15.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = float(timeout)
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
        })
        self.access_token: Optional[str] = None

    def close(self) -> None:
        self.session.close()

    def __enter__(self) -> "DecentralisedArtClient":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()

    def _handle_response(self, response: requests.Response) -> Any:
        try:
            data = response.json()
        except json.JSONDecodeError:
            response.raise_for_status()
            return {"raw": response.text}
        if not response.ok:
            raise requests.HTTPError(f"{response.status_code} {data}", response=response)
        return data

    def _handle_sse_replay_response(self, response: requests.Response) -> Dict[str, Any]:
        if not response.ok:
            self._handle_response(response)
        try:
            return parse_sse_replay_lines(response.iter_lines(decode_unicode=True))
        finally:
            response.close()

    def _authz_headers(self) -> Dict[str, str]:
        if not self.access_token:
            return {}
        return {"Authorization": f"Bearer {self.access_token}"}

    def _get(self, path: str, *, params: Optional[Dict[str, Any]] = None) -> requests.Response:
        return self.session.get(
            f"{self.base_url}{path}",
            params=params,
            headers=self._authz_headers(),
            timeout=self.timeout,
        )

    def _post_with_reauth(self, path: str, payload: Dict[str, Any], acct) -> requests.Response:
        self.ensure_auth(acct)
        url = f"{self.base_url}{path}"
        response = self.session.post(
            url,
            json=payload,
            headers=self._authz_headers(),
            timeout=self.timeout,
        )
        if response.status_code == 401:
            self.access_token = None
            self.ensure_auth(acct)
            response = self.session.post(
                url,
                json=payload,
                headers=self._authz_headers(),
                timeout=self.timeout,
            )
        return response

    def get_nonce(self, address: str) -> Dict[str, Any]:
        response = self.session.get(f"{self.base_url}{api_path('GET_nonce', address=address)}", timeout=self.timeout)
        payload = self._handle_response(response)
        operation_id = "GET_nonce"
        if (isinstance(payload, dict) and set(payload) == {"nonce"}
                and isinstance(payload["nonce"], str) and payload["nonce"].isdigit()):
            operation_id = "GET_nonce_legacy"
        validate_response(operation_id, payload, response.status_code)
        return payload

    def post_auth(self, address: str, nonce: str, signature: str,
                  *, message: str | None = None) -> Dict[str, Any]:
        operation_id = "POST_auth" if message is None else "POST_auth_legacy"
        payload = {"address": address, "signature": signature}
        payload.update({"nonce": nonce} if message is None else {"message": message})
        validate_request(operation_id, payload)
        response = self.session.post(
            f"{self.base_url}{api_path(operation_id)}",
            json=payload,
            timeout=self.timeout,
        )
        data = self._handle_response(response)
        validate_response(operation_id, data, response.status_code)
        self.access_token = data.get("access_token")
        return data

    def ensure_auth(self, acct) -> None:
        if self.access_token:
            return
        challenge = self.get_nonce(acct.address)
        message = challenge.get("message", f"Login nonce: {challenge['nonce']}")
        signature = acct.sign_message(encode_defunct(text=message)).signature.hex()
        auth_result = self.post_auth(acct.address, challenge["nonce"], signature,
                                     message=message if "message" not in challenge else None)
        if not self.access_token:
            raise RuntimeError(f"Auth failed — missing access token: {auth_result}")

    def get_connector(self, name: str) -> Dict[str, Any]:
        return self._handle_response(self._get(api_path("GET_connector", name=name)))

    def get_transformation(self, name: str) -> Dict[str, Any]:
        return self._handle_response(self._get(api_path("GET_transformation", name=name)))

    def get_condition(self, name: str) -> Dict[str, Any]:
        return self._handle_response(self._get(api_path("GET_condition", name=name)))

    def connector_exists(self, name: str) -> bool:
        response = self._get(api_path("GET_connector", name=name))
        if response.status_code == 404:
            return False
        if response.ok:
            return True
        body = (response.text or "").strip().replace("\n", " ")
        raise RuntimeError(f"Failed to check connector '{name}': {response.status_code} {body}")

    def transformation_exists(self, name: str) -> bool:
        response = self._get(api_path("GET_transformation", name=name))
        if response.status_code == 404:
            return False
        if response.ok:
            return True
        body = (response.text or "").strip().replace("\n", " ")
        raise RuntimeError(f"Failed to check transformation '{name}': {response.status_code} {body}")

    def condition_exists(self, name: str) -> bool:
        response = self._get(api_path("GET_condition", name=name))
        if response.status_code == 404:
            return False
        if response.ok:
            return True
        body = (response.text or "").strip().replace("\n", " ")
        raise RuntimeError(f"Failed to check condition '{name}': {response.status_code} {body}")

    def post_connector(self, payload: Dict[str, Any], acct) -> Dict[str, Any]:
        validate_request("POST_connector", payload)
        return self._handle_response(self._post_with_reauth(api_path("POST_connector"), payload, acct))

    def post_transformation(self, payload: Dict[str, Any], acct) -> Dict[str, Any]:
        validate_request("POST_transformation", payload)
        return self._handle_response(self._post_with_reauth(api_path("POST_transformation"), payload, acct))

    def post_condition(self, payload: Dict[str, Any], acct) -> Dict[str, Any]:
        validate_request("POST_condition", payload)
        return self._handle_response(self._post_with_reauth(api_path("POST_condition"), payload, acct))

    def _run_connector(self, operation_id, connector_name, particles_count, dynamic_ri):
        payload = {"connector_name": connector_name, "particles_count": int(particles_count),
                   "dynamic_ri": dynamic_ri or {}}
        validate_request(operation_id, payload)
        response = self.session.post(
            f"{self.base_url}{api_path(operation_id)}", json=payload, timeout=self.timeout,
        )
        data = self._handle_response(response)
        if operation_id == "POST_execute" and not isinstance(data, dict):
            raise ValueError("/execute requires a block-anchored execution envelope")
        if operation_id == "POST_simulate" and not isinstance(data, list):
            raise ValueError("/simulate requires a particle array")
        execution_particles(data)
        validate_response(operation_id, data, getattr(response, "status_code", None))
        return data

    def execute_connector(self, connector_name: str, particles_count: int,
                          dynamic_ri=None) -> Dict[str, Any]:
        """Read the published connector on chain, preserving block provenance."""
        return self._run_connector("POST_execute", connector_name, particles_count, dynamic_ri)

    def simulate_connector(self, connector_name: str, particles_count: int,
                           dynamic_ri=None) -> List[Dict[str, Any]]:
        """Preview a local draft in the server simulation EVM; no publication."""
        return self._run_connector("POST_simulate", connector_name, particles_count, dynamic_ri)

    def list_formats(self, limit: int = 100, after: Optional[str] = None) -> Dict[str, Any]:
        params: Dict[str, Any] = {"limit": int(limit)}
        if after is not None:
            params["after"] = after
        validate_query("GET_formats", params)
        return self._handle_response(self._get(api_path("GET_formats"), params=params))

    def get_format(self, format_hash: str, limit: int = 256, after: Optional[str] = None) -> Dict[str, Any]:
        params: Dict[str, Any] = {"limit": int(limit)}
        if after is not None:
            params["after"] = after
        validate_query("GET_format", params)
        return self._handle_response(self._get(api_path("GET_format", hash=format_hash), params=params))

    def get_account(
        self,
        address: str,
        *,
        limit: int = 256,
        after_connectors: Optional[str] = None,
        after_transformations: Optional[str] = None,
        after_conditions: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"limit": int(limit)}
        if after_connectors is not None:
            params["after_connectors"] = after_connectors
        if after_transformations is not None:
            params["after_transformations"] = after_transformations
        if after_conditions is not None:
            params["after_conditions"] = after_conditions
        validate_query("GET_accountInfo", params)
        return self._handle_response(self._get(api_path("GET_accountInfo", address=address), params=params))

    def get_feed_page(
        self,
        *,
        limit: int = 100,
        before: Optional[str] = None,
        event_type: Optional[str] = None,
        include_unfinalized: Optional[bool] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"limit": int(limit)}
        if before is not None:
            params["before"] = before
        if event_type is not None:
            params["type"] = event_type
        if include_unfinalized is not None:
            params["include_unfinalized"] = 1 if include_unfinalized else 0
        validate_query("GET_feed", params)
        return self._handle_response(self._get(api_path("GET_feed"), params=params))

    def get_feed_stream_replay(self, *, since_seq: int = 0, limit: int = 200) -> Dict[str, Any]:
        params = {"since_seq": int(since_seq), "limit": int(limit)}
        validate_query("GET_feedStream", params)
        response = self.session.get(
            f"{self.base_url}{api_path('GET_feedStream')}",
            params=params,
            headers=self._authz_headers(),
            timeout=self.timeout,
            stream=True,
        )
        return self._handle_sse_replay_response(response)

    def ensure_connectors_exist(self, names: Iterable[str]) -> None:
        missing = [name for name in names if not self.connector_exists(name)]
        if missing:
            raise RuntimeError("Missing required connector primitives: " + ", ".join(missing))

    def resolve_preferred_transformation_pair(self, preferred_pairs: Sequence[Tuple[str, str]]) -> TransformationPair:
        for add_name, subtract_name in preferred_pairs:
            if self.transformation_exists(add_name) and self.transformation_exists(subtract_name):
                return TransformationPair(add=add_name, subtract=subtract_name)
        attempted = [f"{add}/{subtract}" for add, subtract in preferred_pairs]
        raise RuntimeError("No supported transformation pair found on the network. Tried: " + ", ".join(attempted))

    def ensure_preflight(self, acct, *, required_connectors: Sequence[str], preferred_transformation_pairs: Sequence[Tuple[str, str]]) -> TransformationPair:
        self.ensure_auth(acct)
        self.ensure_connectors_exist(required_connectors)
        return self.resolve_preferred_transformation_pair(preferred_transformation_pairs)


def resolve_cursor(payload: Dict[str, Any]) -> ChainCursor:
    cursor = payload.get("cursor")
    if isinstance(cursor, dict):
        return ChainCursor(
            has_more=bool(cursor.get("has_more")),
            next_after=(str(cursor.get("next_after")).strip() if cursor.get("next_after") else None),
        )
    return ChainCursor(
        has_more=bool(payload.get("has_more")),
        next_after=(str(payload.get("next_after")).strip() if payload.get("next_after") else None),
    )


def parse_sse_replay_lines(lines: Iterable[Any]) -> Dict[str, Any]:
    deltas: List[Dict[str, Any]] = []
    comments: List[str] = []
    meta: Optional[Any] = None
    event_name = "message"
    event_id: Optional[str] = None
    data_lines: List[str] = []

    def flush_frame() -> Optional[Dict[str, Any]]:
        nonlocal event_name, event_id, data_lines
        if not data_lines:
            event_name = "message"
            event_id = None
            data_lines = []
            return None
        data_raw = "\n".join(data_lines)
        try:
            data: Any = json.loads(data_raw)
        except json.JSONDecodeError:
            data = data_raw
        frame = {"event": event_name, "id": event_id, "data": data}
        event_name = "message"
        event_id = None
        data_lines = []
        return frame

    def consume_frame(frame: Optional[Dict[str, Any]]) -> bool:
        nonlocal meta
        if frame is None:
            return False
        if frame["event"] == "stream_meta":
            meta = frame["data"]
            return True
        deltas.append(frame)
        return False

    for raw_line in lines:
        line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else str(raw_line)
        line = line.rstrip("\r\n")
        if line == "":
            if consume_frame(flush_frame()):
                break
            continue
        if line.startswith(":"):
            comments.append(line[1:].strip())
            continue
        field, separator, value = line.partition(":")
        if not separator:
            continue
        if value.startswith(" "):
            value = value[1:]
        if field == "event":
            event_name = value or "message"
        elif field == "id":
            event_id = value
        elif field == "data":
            data_lines.append(value)

    if meta is None:
        consume_frame(flush_frame())

    return {"deltas": deltas, "meta": meta, "comments": comments}
