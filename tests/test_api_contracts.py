import unittest
from unittest.mock import Mock

import requests

from decentralised_art_mcp.api_contracts import api_path, requires_auth, spec_commit, validate_query, validate_response
from decentralised_art_mcp.client import DecentralisedArtClient
from decentralised_art_mcp.errors import ValidationError


class ApiContractsTests(unittest.TestCase):
    def test_routes_are_derived_from_the_pinned_openapi(self):
        self.assertEqual(api_path("GET_format", hash="abc/def"), "/format/abc%2Fdef")
        self.assertEqual(api_path("POST_publishPrepare", kind="connector"), "/publish/connector/prepare")
        self.assertEqual(len(spec_commit()), 40)

    def test_spec_marks_execution_public_and_creation_authenticated(self):
        self.assertFalse(requires_auth("POST_execute"))
        self.assertFalse(requires_auth("POST_simulate"))
        self.assertTrue(requires_auth("POST_connector"))
        self.assertTrue(requires_auth("POST_publishPrepare"))

    def test_create_request_rejects_missing_spec_fields_before_http(self):
        client = DecentralisedArtClient("https://api.example/chain")
        client._post_with_reauth = Mock()
        with self.assertRaises(ValidationError) as raised:
            client.post_connector({"name": "example"}, object())
        self.assertIn("dimensions", str(raised.exception))
        client._post_with_reauth.assert_not_called()

    def test_spec_validates_cursor_and_particle_values(self):
        with self.assertRaises(ValidationError):
            validate_query("GET_formats", {"limit": 10, "after": "not-a-format-hash"})
        with self.assertRaises(ValidationError):
            validate_response("POST_execute", {
                "block_number": 1,
                "block_hash": "0x" + "ab" * 32,
                "runner": "0x" + "12" * 20,
                "registry": "0x" + "34" * 20,
                "particles": [{"path": "/example:0", "data": [1.5]}],
            })

    def test_publication_confirmation_uses_http_status_specific_schema(self):
        client = DecentralisedArtClient("https://api.example/chain")
        account = object()
        tx_hash = "0x" + "cd" * 32
        pending = {"message": "not mined yet", "status": "pending", "tx_hash": tx_hash}
        response = requests.Response()
        response.status_code = 202
        response._content = b'{"message":"not mined yet","status":"pending","tx_hash":"' + tx_hash.encode() + b'"}'
        client._post_with_reauth = Mock(return_value=response)

        self.assertEqual(client.publish_confirm(account, "connector", "piece", "0x" + "ab" * 32, tx_hash), pending)
        with self.assertRaises(ValidationError):
            validate_response("POST_publishConfirm", pending, 201)
        validate_response("POST_publishConfirm", pending, 202)


if __name__ == "__main__":
    unittest.main()
