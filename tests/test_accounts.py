import json
import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from decentralised_art_mcp.accounts import create_local_account, load_local_account
from decentralised_art_mcp.context import clear_runtime_overrides, context_from_params, set_runtime_overrides
from decentralised_art_mcp.errors import AuthConfigurationError, ValidationError
from decentralised_art_mcp.server import build_registries
from test_core_integration import FakeClient


@unittest.skipUnless(os.name == "posix", "Local account storage requires POSIX permissions")
class AccountTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name) / "accounts"
        env = patch.dict(os.environ, {"DECENTRALISED_ART_ACCOUNT_ROOT": str(self.root), "PRIVATE_KEY": ""})
        env.start()
        self.addCleanup(env.stop)
        self.addCleanup(clear_runtime_overrides)
        self.registry, _ = build_registries()

    def test_retries_and_new_contexts_preserve_owner_without_returning_key(self):
        first = self.registry.invoke("core.create_account", {"account_id": "draft_owner"})
        second = self.registry.invoke("core.create_account", {"account_id": "draft_owner"})
        self.assertTrue(first["ok"])
        self.assertTrue(first["data"]["created"])
        self.assertFalse(second["data"]["created"])
        self.assertEqual(first["data"]["address"], second["data"]["address"])
        self.assertEqual(set(first["data"]), {"address", "account_id", "created"})
        with context_from_params({"account_id": "draft_owner"}) as context:
            self.assertEqual(context.account().address, first["data"]["address"])
        self.assertEqual(self.root.stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.root / "draft_owner.json").stat().st_mode & 0o777, 0o600)
        self.assertEqual(len(list(self.root.iterdir())), 1)
        key = load_local_account("draft_owner").key.hex()
        self.assertNotIn(key, json.dumps(first))
        self.assertNotIn(key, json.dumps(second))

    def test_concurrent_creation_does_not_rotate_identity(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(create_local_account, ["one_owner"] * 8))
        self.assertEqual(len({result["address"] for result in results}), 1)
        self.assertEqual(sum(result["created"] for result in results), 1)
        self.assertEqual(len(list(self.root.iterdir())), 1)

    def test_local_identity_is_used_for_all_draft_types_and_preflight(self):
        account = create_local_account("owner")
        set_runtime_overrides(client_factory=lambda *args: FakeClient(*args))
        with patch.dict(os.environ, {"PRIVATE_KEY": "invalid_existing_key"}):
            for kind in ("connector", "transformation", "condition"):
                result = self.registry.invoke(f"core.create_{kind}", {"account_id": "owner", "payload": {"name": "draft"}})
                self.assertTrue(result["ok"], result)
                self.assertEqual(result["data"]["owner"], account["address"])
            result = self.registry.invoke("core.ensure_preflight", {"account_id": "owner", "required_connectors": ["pitch"]})
            self.assertEqual(result["data"]["address"], account["address"])

    def test_ambiguous_signer_inputs_are_rejected(self):
        with self.assertRaises(ValidationError):
            context_from_params({"account_id": "owner", "private_key": "another_key"})

    def test_no_account_is_actionable_and_does_not_silently_generate_one(self):
        result = self.registry.invoke("core.create_connector", {"payload": {"name": "draft"}})
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "auth_configuration_error")
        self.assertIn("core.create_account", result["error"]["message"])
        self.assertIn("core.documentation", result["error"]["message"])
        self.assertFalse(self.root.exists())

    def test_account_ids_cannot_escape_storage(self):
        for account_id in ("../escape", "/tmp/escape", "owner/name", "", "a" * 65):
            with self.assertRaises(ValidationError):
                create_local_account(account_id)
        self.assertFalse(self.root.exists())

    def test_rejects_symlinks_and_shared_storage(self):
        create_local_account("owner")
        record = self.root / "owner.json"
        original = record.read_bytes()
        record.chmod(0o644)
        with self.assertRaises(AuthConfigurationError):
            load_local_account("owner")
        record.chmod(0o600)
        self.root.chmod(0o755)
        with self.assertRaises(AuthConfigurationError):
            create_local_account("another")
        self.root.chmod(0o700)
        (self.root / "symlink.json").symlink_to(record)
        result = self.registry.invoke("core.create_account", {"account_id": "symlink"})
        self.assertFalse(result["ok"])
        self.assertEqual(record.read_bytes(), original)
        self.assertNotIn(original.decode(), json.dumps(result))
        linked_root = Path(self.directory.name) / "linked"
        linked_root.symlink_to(self.root)
        with patch.dict(os.environ, {"DECENTRALISED_ART_ACCOUNT_ROOT": str(linked_root)}):
            with self.assertRaises(AuthConfigurationError):
                create_local_account("another")

    def test_corrupt_records_are_not_overwritten_or_exposed(self):
        create_local_account("owner")
        path = self.root / "owner.json"
        path.write_text('{"private_key":"secret_marker"}')
        result = self.registry.invoke("core.create_account", {"account_id": "owner"})
        self.assertFalse(result["ok"])
        self.assertNotIn("secret_marker", json.dumps(result))
        self.assertEqual(path.read_text(), '{"private_key":"secret_marker"}')
