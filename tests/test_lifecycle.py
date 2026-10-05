import copy
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from threading import Barrier
import unittest
from unittest.mock import Mock

from decentralised_art_mcp.client import DecentralisedArtClient
from decentralised_art_mcp.errors import error_to_payload
from decentralised_art_mcp.lifecycle import LifecycleClientMixin, PublicationPending, execution_particles, publish_recorded

OWNER = "0x" + "11" * 20
HASH = "0x" + "ab" * 32
TX_HASH = "0x" + "cd" * 32
ENVELOPE = {"block_number": 123, "block_hash": HASH, "runner": "0x" + "22" * 20,
            "registry": "0x" + "33" * 20,
            "particles": [{"path": "/piece:0/pitch:0", "data": [60]}]}
PREPARED = {"status": "prepared", "kind": "connector", "name": "piece", "content_hash": HASH,
            "deadline": 4102444800, "transaction": {"from": OWNER, "to": "0x" + "22" * 20,
            "chainId": hex(11155111), "gas": "0x5208", "data": "0x12345678"},
            "signing": {"type": "0x2", "value": "0x0", "nonce": "0x7", "maxFeePerGas": "0x64", "maxPriorityFeePerGas": "0x2"}}
MINED = {"status": "mined", "kind": "connector", "name": "piece", "content_hash": HASH,
         "tx_hash": TX_HASH, "owner": OWNER, "address": "0x" + "33" * 20, "block_number": 123}


class Account:
    address = OWNER

    def __init__(self):
        self.transactions = []

    def sign_transaction(self, tx):
        self.transactions.append(tx)
        return SimpleNamespace(raw_transaction=b"\x02\xab", hash=bytes.fromhex("cd" * 32))


class Client(LifecycleClientMixin):
    base_url = "https://example.invalid/chain"

    def __init__(self):
        self.prepared = copy.deepcopy(PREPARED)
        self.prepares = 0
        self.sends = 0
        self.confirms = 0
        self.responses = [{"status": "pending"}, copy.deepcopy(MINED)]

    def publish_prepare(self, *args):
        self.prepares += 1
        return self.prepared

    def publish_send(self, *args):
        self.sends += 1
        return {"status": "pending", "tx_hash": TX_HASH}

    def publish_confirm(self, *args):
        self.confirms += 1
        return self.responses.pop(0)


LIMITS = {"max_fee_per_gas": 100, "max_total_fee": 2100000, "poll_interval": 0}


class LifecycleTests(unittest.TestCase):
    def test_envelope_preserves_provenance_and_draft_route_uses_array(self):
        client = DecentralisedArtClient("https://example.invalid/chain")
        client.ensure_auth = Mock(side_effect=AssertionError("execution must not authenticate"))
        client.access_token = "unused-token"
        responses = [SimpleNamespace(status_code=200, ok=True, json=lambda payload=payload: payload)
                     for payload in (ENVELOPE, ENVELOPE["particles"])]
        client.session.post = Mock(side_effect=responses)
        envelope = client.execute_connector("piece", 8)
        self.assertIs(envelope, ENVELOPE)
        self.assertEqual(envelope["registry"], "0x" + "33" * 20)
        self.assertEqual(execution_particles(envelope), ENVELOPE["particles"])
        self.assertEqual(client.simulate_connector("piece", 8), ENVELOPE["particles"])
        self.assertEqual([call.args[0] for call in client.session.post.call_args_list],
                         ["https://example.invalid/chain/execute", "https://example.invalid/chain/simulate"])
        self.assertTrue(all("headers" not in call.kwargs for call in client.session.post.call_args_list))
        client.ensure_auth.assert_not_called()

    def test_execute_rejects_legacy_array_and_missing_provenance(self):
        for value in ([], {"particles": []}, {**ENVELOPE, "block_number": True}, {**ENVELOPE, "runner": "0x0"},
                      {key: value for key, value in ENVELOPE.items() if key != "registry"},
                      {**ENVELOPE, "registry": "0x0"}):
            with self.subTest(value=value):
                client = DecentralisedArtClient("https://example.invalid/chain")
                client._handle_response = lambda value: value
                client.session.post = Mock(return_value=value)
                with self.assertRaises(ValueError):
                    client.execute_connector("piece", 8)

    def test_malformed_streams_fail_before_interpretation(self):
        for stream in ({"path": 1, "data": []}, {"path": "/pitch", "data": None},
                       {"path": "/pitch", "data": [True]}, {"path": "/pitch", "data": ["60"]},
                       {"path": "/pitch", "data": [float("nan")]}, {"path": "/pitch", "data": [float("inf")]}):
            with self.subTest(stream=stream):
                with self.assertRaises(ValueError):
                    execution_particles({**ENVELOPE, "particles": [stream]})
                with self.assertRaises(ValueError):
                    execution_particles([stream])

    def test_sign_once_send_once_poll_pending_until_mined(self):
        client, account = Client(), Account()
        result = client.publish(account, "connector", "piece", **LIMITS)
        self.assertEqual(result, MINED)
        self.assertEqual((client.prepares, client.sends, client.confirms), (1, 1, 2))
        self.assertEqual(len(account.transactions), 1)
        tx = account.transactions[0]
        self.assertEqual((tx["type"], tx["chainId"], tx["nonce"], tx["value"]), (2, 11155111, 7, 0))

    def test_owner_chain_fee_value_deadline_and_tip_guards_run_before_signing(self):
        edits = [("transaction", "from", "0x" + "44" * 20), ("transaction", "chainId", "0x1"),
                 ("transaction", "gas", "0x5209"), ("signing", "maxFeePerGas", "0x65"),
                 ("signing", "value", "0x1"), ("transaction", "value", "0x1"),
                 ("signing", "type", "0x1"), ("signing", "maxPriorityFeePerGas", "0x65")]
        for section, key, value in edits:
            with self.subTest(key=key, section=section):
                client, account = Client(), Account()
                client.prepared[section][key] = value
                with self.assertRaises(ValueError):
                    client.publish(account, "connector", "piece", **LIMITS)
                self.assertEqual((client.sends, len(account.transactions)), (0, 0))
        client, account = Client(), Account()
        client.prepared["deadline"] = 1
        with self.assertRaises(ValueError):
            client.publish(account, "connector", "piece", **LIMITS)
        self.assertEqual(account.transactions, [])

    def test_already_published_signs_nothing(self):
        client, account = Client(), Account()
        client.prepared = {**MINED, "status": "published"}
        self.assertEqual(client.publish(account, "connector", "piece", **LIMITS)["status"], "published")
        self.assertEqual((client.sends, client.confirms, len(account.transactions)), (0, 0, 0))

    def test_published_shortcut_and_mined_result_validate_identity_and_shape(self):
        for status in ("published", "mined"):
            variants = [("owner", "0x" + "44" * 20), ("address", "0x0"), ("content_hash", "bad")]
            if status == "mined":
                variants += [("block_number", True), ("block_number", -1)]
            for key, value in variants:
                with self.subTest(status=status, key=key):
                    client, account = Client(), Account()
                    invalid = {**MINED, "status": status, key: value}
                    if status == "published":
                        client.prepared = invalid
                    else:
                        client.responses = [invalid]
                    with self.assertRaises(ValueError):
                        client.publish(account, "connector", "piece", **LIMITS)
                    if status == "published":
                        self.assertEqual(account.transactions, [])

    def test_confirmation_error_does_not_resend(self):
        client = Client()
        client.responses = [{"message": "receipt reverted"}]
        with self.assertRaises(ValueError):
            client.publish(Account(), "connector", "piece", **LIMITS)
        self.assertEqual(client.sends, 1)
        with self.assertRaises(PublicationPending):
            client.publish(Account(), "connector", "piece", **LIMITS)
        self.assertEqual(client.sends, 1)

    def test_record_precedes_broadcast_and_resume_confirms_without_send(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "piece.json"
            client = Client()
            def lost_response(*args):
                record = json.loads(path.read_text())
                self.assertEqual(record["publication"]["tx_hash"], TX_HASH)
                client.sends += 1
                raise TimeoutError("lost response")
            client.publish_send = lost_response
            with self.assertRaises(PublicationPending):
                publish_recorded(client, Account(), "connector", "piece", path, **LIMITS)
            resumed = Client()
            resumed.responses = [MINED, MINED]
            self.assertEqual(publish_recorded(resumed, Account(), "connector", "piece", path, **LIMITS), MINED)
            self.assertEqual((resumed.prepares, resumed.sends, resumed.confirms), (0, 0, 1))
            self.assertEqual(publish_recorded(resumed, Account(), "connector", "piece", path, **LIMITS), MINED)
            self.assertEqual(resumed.confirms, 2)

    def test_poll_exhaustion_and_record_owner_change_never_broadcast_again(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "piece.json"
            client = Client()
            with self.assertRaises(PublicationPending):
                publish_recorded(client, Account(), "connector", "piece", path, max_confirm_attempts=1, **LIMITS)
            another = Account()
            another.address = "0x" + "44" * 20
            with self.assertRaises(ValueError):
                publish_recorded(client, another, "connector", "piece", path, **LIMITS)
            self.assertEqual(client.sends, 1)

    def test_confirm_transport_failure_preserves_identity_on_publish_and_resume(self):
        import requests
        for resumed in (False, True):
            with self.subTest(resumed=resumed), TemporaryDirectory() as directory:
                path = Path(directory) / "piece.json"
                client = Client()
                if resumed:
                    with self.assertRaises(PublicationPending):
                        publish_recorded(client, Account(), "connector", "piece", path, max_confirm_attempts=1, **LIMITS)
                    client = Client()
                response = requests.Response()
                response.status_code = 503
                client.publish_confirm = Mock(side_effect=requests.HTTPError("indexer unavailable", response=response))
                with self.assertRaises(PublicationPending) as raised:
                    publish_recorded(client, Account(), "connector", "piece", path, **LIMITS)
                self.assertEqual(raised.exception.publication["tx_hash"], TX_HASH)
                self.assertEqual(raised.exception.publication["content_hash"], HASH)
                self.assertEqual(json.loads(path.read_text())["publication"]["tx_hash"], TX_HASH)
                self.assertEqual(client.sends, 0 if resumed else 1)

    def test_concurrent_record_claims_broadcast_at_most_once(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "piece.json"
            barrier = Barrier(2)
            clients = [Client(), Client()]
            def publish(client):
                original = client.publish_prepare
                def prepare(*args):
                    result = original(*args)
                    barrier.wait(timeout=3)
                    return result
                client.publish_prepare = prepare
                try:
                    return publish_recorded(client, Account(), "connector", "piece", path, **LIMITS)
                except FileExistsError:
                    return None
            with ThreadPoolExecutor(max_workers=2) as executor:
                results = list(executor.map(publish, clients))
            self.assertEqual(sum(client.sends for client in clients), 1)
            self.assertEqual(sum(result is not None for result in results), 1)
            self.assertEqual(json.loads(path.read_text())["publication"]["status"], "mined")

    def test_broadcast_http_request_has_no_401_retry(self):
        client = DecentralisedArtClient("https://example.invalid/chain")
        client.ensure_auth = Mock()
        client.session.post = Mock(return_value=SimpleNamespace(status_code=401, ok=False, json=lambda: {"message": "expired"}))
        with self.assertRaises(Exception):
            client.publish_send(Account(), "connector", "piece", HASH, "0x02ab")
        self.assertEqual(client.session.post.call_count, 1)
        self.assertTrue(client.session.post.call_args.args[0].endswith("/publish/connector/send"))

    def test_publication_dependency_errors_are_actionable(self):
        import requests
        response = requests.Response()
        response.status_code = 409
        response._content = b'{"message":"dependencies missing","missing":["connector/child"]}'
        result = error_to_payload(requests.HTTPError(response=response))
        self.assertEqual(result["code"], "http_error")
        self.assertEqual(result["details"]["missing"], ["connector/child"])


if __name__ == "__main__":
    unittest.main()
