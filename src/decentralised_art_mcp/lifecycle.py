"""Current decentralised.art draft, simulation and owner-paid publication contract.

This module deliberately needs no RPC provider: the owner's account signs locally
and the authenticated server relays a single EIP-1559 transaction.
"""
from __future__ import annotations

import json
import math
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Any

from .api_contracts import api_path, validate_request, validate_response

SEPOLIA_CHAIN_ID = 11155111
KINDS = {"connector", "transformation", "condition"}


def execution_particles(result: Any) -> list[dict]:
    """Accept simulation arrays or validate an execution envelope without losing it."""
    if isinstance(result, list):
        particles = result
    elif isinstance(result, dict):
        block = result.get("block_number")
        if isinstance(block, bool) or not isinstance(block, int) or block < 0:
            raise ValueError("Execution must include a nonnegative block_number")
        if not re.fullmatch(r"0x[0-9a-fA-F]{64}", str(result.get("block_hash", ""))):
            raise ValueError("Execution must include block_hash")
        if not re.fullmatch(r"0x[0-9a-fA-F]{40}", str(result.get("runner", ""))):
            raise ValueError("Execution must include runner")
        if not re.fullmatch(r"0x[0-9a-fA-F]{40}", str(result.get("registry", ""))):
            raise ValueError("Execution must include registry")
        particles = result.get("particles")
    else:
        particles = None
    if not isinstance(particles, list) or any(not isinstance(item, dict) for item in particles):
        raise ValueError("Expected particle objects in simulation array or execution envelope")
    for item in particles:
        if not isinstance(item.get("path"), str) or not isinstance(item.get("data"), list):
            raise ValueError("Each particle stream requires path string and data array")
        for value in item["data"]:
            if isinstance(value, bool) or not isinstance(value, (int, float)) or (isinstance(value, float) and not math.isfinite(value)):
                raise ValueError("Particle data must contain finite numbers, not booleans")
    return particles


def _quantity(value: Any, label: str) -> int:
    if not isinstance(value, str) or not re.fullmatch(r"0x[0-9a-fA-F]+", value):
        raise ValueError(f"Invalid hex quantity: {label}")
    return int(value, 16)


class PublicationPending(TimeoutError):
    def __init__(self, publication: dict, reason: str = "confirmation pending"):
        self.publication = {**publication, "recovery_reason": reason}
        super().__init__(f"Publication {publication['tx_hash']} requires confirmation ({reason}); confirm this transaction without rebroadcasting")


def _validate_publication_result(result, acct, kind, name, pending=None):
    if not isinstance(result, dict) or result.get("status") not in {"mined", "published"}:
        raise ValueError("Expected a mined or already-published result")
    if result.get("kind") != kind or result.get("name") != name:
        raise ValueError("Publication result does not match requested entity")
    for key in ("owner", "address"):
        value = result.get(key)
        if not isinstance(value, str) or not re.fullmatch(r"0x[0-9a-fA-F]{40}", value) or int(value, 16) == 0:
            raise ValueError(f"Publication requires a nonzero {key} address")
    if result["owner"].lower() != acct.address.lower():
        raise ValueError("Publication owner mismatch")
    if not re.fullmatch(r"0x[0-9a-fA-F]{64}", str(result.get("content_hash", ""))):
        raise ValueError("Invalid publication content hash")
    if result["status"] == "mined":
        block = result.get("block_number")
        if isinstance(block, bool) or not isinstance(block, int) or block < 0:
            raise ValueError("Mined publication requires a nonnegative block_number")
        if not re.fullmatch(r"0x[0-9a-fA-F]{64}", str(result.get("tx_hash", ""))):
            raise ValueError("Invalid publication transaction hash")
    if pending:
        for key in ("kind", "name", "content_hash", "tx_hash"):
            if result.get(key) != pending[key]:
                raise ValueError(f"Confirmation mismatch: {key}")
    return result


def confirm_existing(client, acct, kind, name, content_hash, tx_hash):
    pending = {"status": "pending", "kind": kind, "name": name,
               "content_hash": content_hash, "tx_hash": tx_hash}
    try:
        result = client.publish_confirm(acct, kind, name, content_hash, tx_hash)
    except OSError as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        if status is None or status >= 500:
            raise PublicationPending(pending, "confirmation service unavailable") from exc
        raise
    if not isinstance(result, dict):
        raise ValueError("Invalid publication confirmation")
    if result.get("status") == "mined":
        return _validate_publication_result(result, acct, kind, name, pending)
    if result.get("status") != "pending":
        raise ValueError(f"Unexpected publication confirmation: {result}")
    return result


class LifecycleClientMixin:
    def _publication_post(self, kind, suffix, payload, acct, *, broadcast=False):
        if kind not in KINDS:
            raise ValueError("kind must be connector, transformation or condition")
        operation_id = {
            "/prepare": "POST_publishPrepare",
            "/send": "POST_publishSend",
            "": "POST_publishConfirm",
        }[suffix]
        validate_request(operation_id, payload)
        path = api_path(operation_id, kind=kind)
        if not broadcast:
            response = self._post_with_reauth(path, payload, acct)
            result = self._handle_response(response)
            validate_response(operation_id, result, getattr(response, "status_code", None))
            return result
        # Broadcast must never be retried automatically, including after an HTTP
        # timeout. The signed transaction hash can be used to reconcile the result.
        self.ensure_auth(acct)
        response = self.session.post(
            f"{self.base_url}{path}", json=payload,
            headers=self._authz_headers(), timeout=self.timeout,
        )
        result = self._handle_response(response)
        validate_response(operation_id, result, getattr(response, "status_code", None))
        return result

    def publish_prepare(self, acct, kind: str, name: str):
        return self._publication_post(kind, "/prepare", {"name": name, "relay": True}, acct)

    def publish_confirm(self, acct, kind: str, name: str, content_hash: str, tx_hash: str):
        return self._publication_post(kind, "", {"name": name, "content_hash": content_hash, "tx_hash": tx_hash}, acct)

    def publish_send(self, acct, kind: str, name: str, content_hash: str, raw_tx: str):
        return self._publication_post(kind, "/send", {"name": name, "content_hash": content_hash, "raw_tx": raw_tx}, acct, broadcast=True)

    def publish(self, acct, kind: str, name: str, *, max_fee_per_gas: int,
                max_total_fee: int, chain_id: int = SEPOLIA_CHAIN_ID,
                max_confirm_attempts: int = 20, poll_interval: float = 1.0,
                on_pending=None):
        """Explicit opt-in publication; fee caps are wei and apply before signing.

        on_pending persists the transaction identity BEFORE network broadcast so
        callers can safely resume with publish_confirm even after a lost response.
        """
        for key, value in (("max_fee_per_gas", max_fee_per_gas), ("max_total_fee", max_total_fee),
                           ("chain_id", chain_id), ("max_confirm_attempts", max_confirm_attempts)):
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{key} must be a positive integer")
        if max_confirm_attempts > 200 or not 0 <= poll_interval <= 30:
            raise ValueError("Invalid publication polling bounds")
        existing = getattr(self, "pending_publication", None)
        if existing:
            raise PublicationPending(existing)
        prepared = self.publish_prepare(acct, kind, name)
        if not isinstance(prepared, dict) or prepared.get("kind") != kind or prepared.get("name") != name:
            raise ValueError("Publication preparation does not match requested entity")
        if prepared.get("status") == "published":
            return _validate_publication_result(prepared, acct, kind, name)
        if prepared.get("status") != "prepared":
            raise ValueError("Expected prepared publication")
        tx, signing = prepared.get("transaction", {}), prepared.get("signing", {})
        if str(tx.get("from", "")).lower() != acct.address.lower():
            raise ValueError("Signer is not the entity owner")
        if _quantity(tx.get("chainId"), "chainId") != chain_id:
            raise ValueError("Publication chain does not match expected chain_id")
        if _quantity(signing.get("type"), "type") != 2 or _quantity(signing.get("value"), "value") != 0:
            raise ValueError("Publication must be a zero-value type-2 transaction")
        if "value" in tx and _quantity(tx["value"], "value") != 0:
            raise ValueError("Publication cannot transfer value")
        gas = _quantity(tx.get("gas"), "gas")
        fee = _quantity(signing.get("maxFeePerGas"), "maxFeePerGas")
        tip = _quantity(signing.get("maxPriorityFeePerGas"), "maxPriorityFeePerGas")
        if gas <= 0 or fee > max_fee_per_gas or gas * fee > max_total_fee or tip > fee:
            raise ValueError("Publication exceeds fee budget or contains invalid fees")
        if not re.fullmatch(r"0x[0-9a-fA-F]{40}", str(tx.get("to", ""))):
            raise ValueError("Invalid publication registry address")
        if not re.fullmatch(r"0x(?:[0-9a-fA-F]{2}){4,}", str(tx.get("data", ""))):
            raise ValueError("Invalid publication calldata")
        if not re.fullmatch(r"0x[0-9a-fA-F]{64}", str(prepared.get("content_hash", ""))):
            raise ValueError("Invalid publication content hash")
        deadline = prepared.get("deadline")
        if not isinstance(deadline, int) or deadline <= time.time():
            raise ValueError("Publication authorization has expired")
        signed = acct.sign_transaction({
            "type": 2, "chainId": chain_id, "to": tx["to"], "data": tx["data"],
            "nonce": _quantity(signing.get("nonce"), "nonce"), "gas": gas,
            "maxFeePerGas": fee, "maxPriorityFeePerGas": tip, "value": 0,
        })
        raw = "0x" + bytes(signed.raw_transaction).hex()
        tx_hash = "0x" + bytes(signed.hash).hex()
        pending = {"status": "pending", "kind": kind, "name": name,
                   "content_hash": prepared["content_hash"], "tx_hash": tx_hash}
        # Also expose identity on the client if the transport raises an exception.
        self.pending_publication = pending
        if on_pending:
            on_pending(dict(pending))
        try:
            sent = self.publish_send(acct, kind, name, prepared["content_hash"], raw)
        except Exception as exc:
            raise PublicationPending(pending, "broadcast outcome unknown") from exc
        if sent.get("status") != "pending" or str(sent.get("tx_hash", "")).lower() != tx_hash.lower():
            raise ValueError(f"Relay response disagrees with signed transaction {tx_hash}; confirm before retrying")
        for attempt in range(max_confirm_attempts):
            confirmed = confirm_existing(self, acct, kind, name, prepared["content_hash"], tx_hash)
            if confirmed.get("status") == "mined":
                self.pending_publication = None
                return confirmed
            if confirmed.get("status") != "pending":
                raise ValueError(f"Unexpected publication confirmation: {confirmed}")
            if attempt + 1 < max_confirm_attempts:
                time.sleep(poll_interval)
        raise PublicationPending(pending)


def publish_recorded(client, acct, kind: str, name: str, record_path, **limits):
    """Persist transaction identity before send; re-entry only confirms it.

    A pending record is intentionally never discarded automatically, even when a
    receipt is absent. Inspect/reconcile that transaction before a fresh attempt.
    """
    path = Path(record_path)
    identity = {"api_base": client.base_url, "owner": acct.address.lower(),
                "chain_id": limits.get("chain_id", SEPOLIA_CHAIN_ID), "kind": kind, "name": name}
    if path.exists():
        stored = json.loads(path.read_text(encoding="utf-8"))
        if stored.get("identity") != identity:
            raise ValueError("Publication record belongs to another API, owner, chain or entity")
        result = stored["publication"]
        if result.get("status") == "published":
            return _validate_publication_result(result, acct, kind, name)
        if result.get("status") == "mined":
            _validate_publication_result(result, acct, kind, name)
        result = confirm_existing(client, acct, kind, name, result["content_hash"], result["tx_hash"])
        if result.get("status") == "pending":
            raise PublicationPending(stored["publication"])
        client.pending_publication = None
    else:
        def persist_pending(pending):
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("x", encoding="utf-8") as handle:
                json.dump({"identity": identity, "publication": pending}, handle, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
        result = client.publish(acct, kind, name, on_pending=persist_pending, **limits)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, prefix=path.name + ".", delete=False) as handle:
        json.dump({"identity": identity, "publication": result}, handle, indent=2)
        handle.flush()
        os.fsync(handle.fileno())
    Path(handle.name).replace(path)
    return result
