import unittest
from unittest.mock import Mock

from decentralised_art_mcp.context import clear_runtime_overrides, set_runtime_overrides
from decentralised_art_mcp.server import build_registries


class FakeAccount:
    address = "0xabc"


class FakeClient:
    def __init__(self, api_base, timeout):
        self.api_base = api_base
        self.timeout = timeout
        self.closed = False

    def close(self):
        self.closed = True

    def connector_exists(self, name):
        return name == "pitch"

    def get_nonce(self, address):
        return {"nonce": "ab" * 33, "message": "Sign in to decentralised.art."}

    def transformation_exists(self, name):
        return name == "math_add_v1"

    def condition_exists(self, name):
        return name == "always_true"

    def get_connector(self, name):
        return {"name": name, "dimensions": []}

    def get_transformation(self, name):
        return {"name": name, "args_count": 1, "owner": "0xabc", "address": "0x0"}

    def get_condition(self, name):
        return {"name": name, "args_count": 0, "owner": "0xabc", "address": "0x0"}

    def get_feed_page(self, *, limit=100, before=None, event_type=None, include_unfinalized=None):
        return {
            "events": [{"feed_id": "connector:a", "event_type": "connector_added", "seq": 1}],
            "cursor": {"has_more": False, "next_before": None},
            "limit": limit,
            "before": before,
            "type": event_type,
            "include_unfinalized": include_unfinalized,
        }

    def get_feed_stream_replay(self, *, since_seq=0, limit=200):
        return {
            "deltas": [{"event": "event_delta", "id": str(since_seq + 1), "data": {"seq": since_seq + 1}}],
            "meta": {"replay_count": 1, "limit": limit},
            "comments": [],
        }

    def list_formats(self, limit=100, after=None):
        return {"formats": ["fmt1"], "limit": limit, "after": after}

    def get_format(self, format_hash, limit=256, after=None):
        return {"format_hash": format_hash, "features": ["pitch", "time"], "limit": limit, "after": after}

    def get_account(self, address, *, limit=256, after_connectors=None, after_transformations=None, after_conditions=None):
        return {
            "address": address,
            "limit": limit,
            "owned_connectors": ["a", "b"],
            "owned_transformations": ["math_add_v1"],
            "owned_conditions": [],
            "cursor_connectors": {"has_more": False, "next_after": None},
            "cursor_transformations": {"has_more": False, "next_after": None},
            "cursor_conditions": {"has_more": False, "next_after": None},
        }

    def ensure_preflight(self, acct, *, required_connectors, preferred_transformation_pairs):
        class Pair:
            add = "math_add_v1"
            subtract = "math_subtract_v1"
        return Pair()

    def post_connector(self, payload, acct):
        return {"name": payload.get("name"), "owner": acct.address}

    def post_transformation(self, payload, acct):
        return {"name": payload.get("name"), "owner": acct.address}

    def post_condition(self, payload, acct):
        return {"name": payload.get("name"), "owner": acct.address}

    def simulate_connector(self, connector_name, particles_count, dynamic_ri=None):
        return [{"path": "/cell:0/pitch:0", "data": [60]}]

    def execute_connector(self, connector_name, particles_count, dynamic_ri=None):
        return {"block_number": 42, "block_hash": "0x" + "ab" * 32, "runner": "0x" + "12" * 20, "registry": "0x" + "34" * 20, "particles": [{"path": "/cell:0/pitch:0", "data": [60]}]}


def fake_account_loader(_private_key):
    return FakeAccount()


class CoreIntegrationTests(unittest.TestCase):
    def setUp(self):
        set_runtime_overrides(client_factory=lambda api_base, timeout: FakeClient(api_base, timeout), account_loader=fake_account_loader)
        self.registry, _ = build_registries()

    def tearDown(self):
        clear_runtime_overrides()

    def test_connector_exists_uses_fake_client(self):
        result = self.registry.invoke("core.connector_exists", {"name": "pitch"})
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"], {"name": "pitch", "exists": True})

    def test_get_nonce_returns_the_message_and_nonce(self):
        result = self.registry.invoke("core.get_nonce", {"address": "0x" + "11" * 20})
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"], {"address": "0x" + "11" * 20,
                                         "nonce": "ab" * 33, "message": "Sign in to decentralised.art."})

    def test_transformation_exists_uses_fake_client(self):
        result = self.registry.invoke("core.transformation_exists", {"name": "math_add_v1"})
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"], {"name": "math_add_v1", "exists": True})

    def test_condition_exists_uses_fake_client(self):
        result = self.registry.invoke("core.condition_exists", {"name": "always_true"})
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"], {"name": "always_true", "exists": True})

    def test_get_condition_uses_fake_client(self):
        result = self.registry.invoke("core.get_condition", {"name": "always_true"})
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"], {"name": "always_true", "args_count": 0, "owner": "0xabc", "address": "0x0"})

    def test_get_feed_page_uses_fake_client(self):
        result = self.registry.invoke("core.get_feed_page", {"limit": 50, "type": "connector_added", "include_unfinalized": True})
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["limit"], 50)
        self.assertEqual(result["data"]["type"], "connector_added")
        self.assertTrue(result["data"]["include_unfinalized"])

    def test_get_feed_stream_replay_uses_fake_client(self):
        result = self.registry.invoke("core.get_feed_stream_replay", {"since_seq": 5, "limit": 10})
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["deltas"][0]["data"]["seq"], 6)
        self.assertEqual(result["data"]["meta"]["limit"], 10)

    def test_get_account_uses_fake_client(self):
        result = self.registry.invoke("core.get_account", {"address": "0xabc", "limit": 64})
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["address"], "0xabc")
        self.assertEqual(result["data"]["limit"], 64)
        self.assertEqual(result["data"]["owned_connectors"], ["a", "b"])

    def test_limit_zero_is_validation_error(self):
        result = self.registry.invoke("core.get_account", {"address": "0xabc", "limit": 0})
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "validation_error")

    def test_execute_and_simulate_need_no_account(self):
        account_loader = Mock(side_effect=AssertionError("execution must not load a private key"))
        set_runtime_overrides(client_factory=lambda api_base, timeout: FakeClient(api_base, timeout), account_loader=account_loader)
        result = self.registry.invoke("core.execute_connector", {"connector_name": "piece", "particles_count": 8})
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["particles"][0]["data"], [60])
        self.assertNotIn("samples", result["data"])
        self.assertEqual(result["data"]["block_number"], 42)
        self.assertEqual(result["data"]["registry"], "0x" + "34" * 20)
        self.assertEqual(result["data"]["execution_mode"], "chain")
        simulated = self.registry.invoke("core.simulate_connector", {"connector_name": "draft", "particles_count": 8})
        self.assertTrue(simulated["ok"])
        self.assertEqual(simulated["data"]["execution_mode"], "simulation")
        account_loader.assert_not_called()

    def test_creation_and_simulation_never_publish(self):
        client = FakeClient("https://example.invalid", 1)
        client.publish = Mock(side_effect=AssertionError("draft must not spend gas"))
        set_runtime_overrides(client_factory=lambda *args: client, account_loader=fake_account_loader)
        for kind in ("connector", "transformation", "condition"):
            result = self.registry.invoke(f"core.create_{kind}", {"payload": {"name": "draft"}})
            self.assertTrue(result["ok"])
        result = self.registry.invoke("core.simulate_connector", {"connector_name": "draft", "particles_count": 8})
        self.assertEqual(result["data"]["execution_mode"], "simulation")
        self.assertNotIn("block_hash", result["data"])
        self.assertNotIn("samples", result["data"])
        client.publish.assert_not_called()

    def test_execute_not_yet_at_safe_block_never_substitutes_simulation(self):
        import requests
        for status in (404, 503):
            client = FakeClient("https://example.invalid", 1)
            response = requests.Response()
            response.status_code = status
            client.execute_connector = Mock(side_effect=requests.HTTPError("not available at execution block", response=response))
            client.simulate_connector = Mock(side_effect=AssertionError("must not fall back"))
            set_runtime_overrides(client_factory=lambda *args: client, account_loader=fake_account_loader)
            result = self.registry.invoke("core.execute_connector", {"connector_name": "piece", "particles_count": 8})
            self.assertFalse(result["ok"])
            self.assertNotIn("data", result)
            client.simulate_connector.assert_not_called()

    def test_create_transformation_and_condition_use_fake_client_and_account(self):
        transformation = self.registry.invoke("core.create_transformation", {"payload": {"name": "xform"}})
        condition = self.registry.invoke("core.create_condition", {"payload": {"name": "cond"}})
        self.assertTrue(transformation["ok"])
        self.assertTrue(condition["ok"])
        self.assertEqual(transformation["data"], {"name": "xform", "owner": "0xabc"})
        self.assertEqual(condition["data"], {"name": "cond", "owner": "0xabc"})

    def test_ensure_preflight_uses_fake_client_and_account(self):
        result = self.registry.invoke("core.ensure_preflight", {"required_connectors": ["pitch", "time"]})
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["add"], "math_add_v1")
        self.assertEqual(result["data"]["address"], "0xabc")

    def test_bad_transformation_pairs_are_validation_errors(self):
        result = self.registry.invoke("core.resolve_transformation_pair", {"pairs": [["math_add_v1"]]})
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "validation_error")

    def test_empty_transformation_pairs_do_not_fallback_to_defaults(self):
        result = self.registry.invoke("core.resolve_transformation_pair", {"pairs": []})
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "validation_error")

    def test_tool_context_closes_client_after_call(self):
        created = []

        def factory(api_base, timeout):
            client = FakeClient(api_base, timeout)
            created.append(client)
            return client

        set_runtime_overrides(client_factory=factory, account_loader=fake_account_loader)
        result = self.registry.invoke("core.connector_exists", {"name": "pitch"})
        self.assertTrue(result["ok"])
        self.assertEqual(len(created), 1)
        self.assertTrue(created[0].closed)


if __name__ == "__main__":
    unittest.main()
