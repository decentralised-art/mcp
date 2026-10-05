import unittest
from unittest.mock import Mock

from eth_account import Account
from eth_account.messages import encode_defunct

from decentralised_art_mcp.client import DecentralisedArtClient, parse_sse_replay_lines
from decentralised_art_mcp.errors import ValidationError


class FakeResponse:
    ok = True
    status_code = 200
    text = ""

    def __init__(self, payload, *, lines=None):
        self.payload = payload
        self.lines = lines or []
        self.closed = False

    def json(self):
        return self.payload

    def raise_for_status(self):
        return None

    def iter_lines(self, decode_unicode=False):
        return iter(self.lines)

    def close(self):
        self.closed = True


class FakeSession:
    def __init__(self):
        self.headers = {}
        self.calls = []
        self.closed = False

    def get(self, url, **kwargs):
        self.calls.append(("get", url, kwargs))
        return FakeResponse({"ok": True})

    def close(self):
        self.closed = True


class ClientTests(unittest.TestCase):
    def test_decimal_nonce_auth_signs_and_submits_the_login_message(self):
        client = DecentralisedArtClient("https://api.example/chain")
        account = Account.create()
        client.session.get = Mock(return_value=FakeResponse({"nonce": "193752"}))
        client.session.post = Mock(return_value=FakeResponse({"access_token": "test-token"}))

        client.ensure_auth(account)

        payload = client.session.post.call_args.kwargs["json"]
        self.assertEqual(set(payload), {"address", "message", "signature"})
        self.assertEqual(payload["message"], "Login nonce: 193752")
        self.assertEqual(Account.recover_message(encode_defunct(text=payload["message"]),
                                                signature=payload["signature"]), account.address)
        self.assertEqual(client.access_token, "test-token")

    def test_auth_signs_issued_message_and_submits_nonce_once(self):
        client = DecentralisedArtClient("https://api.example/chain")
        account = Account.create()
        challenge = {"nonce": "ab" * 33, "message": "Sign in to decentralised.art.\nNonce: " + "ab" * 33}
        client.session.get = Mock(return_value=FakeResponse(challenge))
        client.session.post = Mock(return_value=FakeResponse({"access_token": "test-token"}))

        client.ensure_auth(account)
        client.ensure_auth(account)

        client.session.get.assert_called_once_with(
            f"https://api.example/chain/nonce/{account.address}", timeout=15.0)
        client.session.post.assert_called_once()
        call = client.session.post.call_args
        self.assertEqual(call.args[0], "https://api.example/chain/auth")
        payload = call.kwargs["json"]
        self.assertEqual(set(payload), {"address", "nonce", "signature"})
        self.assertEqual(payload["nonce"], challenge["nonce"])
        self.assertEqual(Account.recover_message(encode_defunct(text=challenge["message"]),
                                                signature=payload["signature"]), account.address)
        self.assertEqual(client.access_token, "test-token")

    def test_incomplete_auth_challenge_is_rejected_before_signing(self):
        client = DecentralisedArtClient("https://api.example/chain")
        account = Mock(address="0x" + "11" * 20)
        client.session.get = Mock(return_value=FakeResponse({"nonce": "ab" * 33}))
        client.session.post = Mock()

        with self.assertRaises(ValidationError):
            client.ensure_auth(account)

        account.sign_message.assert_not_called()
        client.session.post.assert_not_called()

    def test_expired_token_reauthenticates_with_a_fresh_challenge(self):
        client = DecentralisedArtClient("https://api.example/chain")
        account = Account.create()
        challenges = [{"nonce": value * 33, "message": f"Sign-in message {value}"} for value in ("ab", "cd")]
        client.session.get = Mock(side_effect=[FakeResponse(value) for value in challenges])
        rejected = FakeResponse({"message": "expired"})
        rejected.status_code = 401
        client.session.post = Mock(side_effect=[
            FakeResponse({"access_token": "first-token"}), rejected,
            FakeResponse({"access_token": "second-token"}), FakeResponse({"created": True}),
        ])

        response = client._post_with_reauth("/connector", {"name": "example"}, account)

        self.assertEqual(response.json(), {"created": True})
        calls = client.session.post.call_args_list
        self.assertEqual([calls[index].kwargs["json"]["nonce"] for index in (0, 2)],
                         [challenge["nonce"] for challenge in challenges])
        self.assertEqual([calls[index].kwargs["headers"] for index in (1, 3)],
                         [{"Authorization": "Bearer first-token"}, {"Authorization": "Bearer second-token"}])
        self.assertEqual(client.access_token, "second-token")

    def test_account_uses_the_spec_route_and_independent_cursors(self):
        client = DecentralisedArtClient("https://api.example/chain")
        session = FakeSession()
        client.session = session

        client.get_account("0x" + "11" * 20, limit=7, after_connectors="pitch", after_conditions="gate")

        self.assertEqual(session.calls[0][1], "https://api.example/chain/account/0x" + "11" * 20)
        self.assertEqual(session.calls[0][2]["params"],
                         {"limit": 7, "after_connectors": "pitch", "after_conditions": "gate"})

    def test_query_params_are_passed_to_requests(self):
        client = DecentralisedArtClient("https://api.example/chain")
        session = FakeSession()
        client.session = session

        cursor = "ab" * 32
        client.list_formats(limit=10, after=cursor)

        self.assertEqual(session.calls[0][1], "https://api.example/chain/formats")
        self.assertEqual(session.calls[0][2]["params"], {"limit": 10, "after": cursor})

    def test_path_segments_are_url_encoded(self):
        client = DecentralisedArtClient("https://api.example/chain")
        session = FakeSession()
        client.session = session

        client.get_format("abc/def", limit=1)

        self.assertEqual(session.calls[0][1], "https://api.example/chain/format/abc%2Fdef")

    def test_condition_uses_condition_endpoint(self):
        client = DecentralisedArtClient("https://api.example/chain")
        session = FakeSession()
        client.session = session

        client.get_condition("cond/a")

        self.assertEqual(session.calls[0][1], "https://api.example/chain/condition/cond%2Fa")

    def test_feed_page_uses_current_cursor_and_type_params(self):
        client = DecentralisedArtClient("https://api.example/chain")
        session = FakeSession()
        client.session = session

        client.get_feed_page(limit=7, before="42:abc", event_type="connector_added", include_unfinalized=True)

        self.assertEqual(session.calls[0][1], "https://api.example/chain/feed")
        self.assertEqual(
            session.calls[0][2]["params"],
            {"limit": 7, "before": "42:abc", "type": "connector_added", "include_unfinalized": 1},
        )

    def test_parse_sse_replay_lines_stops_at_stream_meta(self):
        payload = parse_sse_replay_lines(
            [
                ": connected",
                "id: 9",
                "event: event_delta",
                'data: {"feed_id":"connector:demo","seq":9}',
                "",
                "event: stream_meta",
                'data: {"replay_count":1,"live":false}',
                "",
                "event: event_delta",
                'data: {"feed_id":"ignored"}',
                "",
            ]
        )

        self.assertEqual(payload["comments"], ["connected"])
        self.assertEqual(payload["deltas"][0]["id"], "9")
        self.assertEqual(payload["deltas"][0]["data"]["feed_id"], "connector:demo")
        self.assertEqual(payload["meta"], {"replay_count": 1, "live": False})

    def test_client_close_closes_session(self):
        client = DecentralisedArtClient("https://api.example/chain")
        session = FakeSession()
        client.session = session

        client.close()

        self.assertTrue(session.closed)


if __name__ == "__main__":
    unittest.main()
