"""Persistent local signing accounts. Tool results never contain secret material."""
from __future__ import annotations

import json
import os
import re
import stat
import tempfile
from pathlib import Path

from eth_account import Account

from .errors import AuthConfigurationError, ValidationError


ACCOUNT_ID_PATTERN = r"[A-Za-z][A-Za-z0-9_]{0,63}"


def account_root() -> Path:
    configured = os.getenv("DECENTRALISED_ART_ACCOUNT_ROOT", "").strip()
    return Path(configured).expanduser() if configured else Path.home() / ".decentralised-art-mcp" / "accounts"


def _check_permissions(path: Path, *, directory: bool = False) -> None:
    info = path.lstat()
    expected = stat.S_ISDIR if directory else stat.S_ISREG
    if not expected(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise AuthConfigurationError(
            "Local account storage must be owner-only: directory mode 0700 and key file mode 0600."
        )


def _path(account_id: str, *, create_directory: bool = False) -> Path:
    if not isinstance(account_id, str) or not re.fullmatch(ACCOUNT_ID_PATTERN, account_id):
        raise ValidationError("account_id must start with a letter and contain up to 64 letters, digits or underscores.")
    if os.name != "posix":
        raise AuthConfigurationError(
            "Local account storage currently requires POSIX file permissions. Configure PRIVATE_KEY through the host's secret settings on this platform."
        )
    root = account_root()
    if create_directory:
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not root.exists():
        raise AuthConfigurationError("Unknown local account. Read core.documentation and use core.create_account with this account_id to create a fresh identity.")
    _check_permissions(root, directory=True)
    return root / f"{account_id}.json"


def load_local_account(account_id: str):
    path = _path(account_id)
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except FileNotFoundError as exc:
        raise AuthConfigurationError("Unknown local account. Use core.create_account with this account_id for a fresh identity; do not replace an existing draft owner's key.") from exc
    with os.fdopen(fd, "r", encoding="utf-8") as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise AuthConfigurationError("Local account key file must be owner-only (mode 0600).")
        try:
            record = json.load(handle)
            account = Account.from_key(record["private_key"])
            if record["account_id"] != account_id or record["address"] != account.address:
                raise ValueError("Account record mismatch")
        except (KeyError, TypeError, ValueError) as exc:
            raise AuthConfigurationError("Local account record is invalid; restore its original key from a local backup.") from exc
    return account


def create_local_account(account_id: str) -> dict:
    """Reuse a named identity on retries; never overwrite or rotate its key."""
    path = _path(account_id, create_directory=True)
    created = False
    if not path.exists() and not path.is_symlink():
        account = Account.create()
        record = {"account_id": account_id, "address": account.address, "private_key": account.key.hex()}
        # Write fully before exposing the record. Hard-linking is atomic and refuses
        # to overwrite a concurrent creator's account or an existing symlink.
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as handle:
            temporary_path = Path(handle.name)
            try:
                os.fchmod(handle.fileno(), 0o600)
                json.dump(record, handle)
                handle.flush()
                os.fsync(handle.fileno())
                try:
                    os.link(temporary_path, path)
                    created = True
                    directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
                    try:
                        os.fsync(directory_fd)
                    finally:
                        os.close(directory_fd)
                except FileExistsError:
                    pass
            finally:
                temporary_path.unlink(missing_ok=True)
    account = load_local_account(account_id)
    return {"account_id": account_id, "address": account.address, "created": created}
