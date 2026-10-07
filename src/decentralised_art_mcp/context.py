from __future__ import annotations

import math
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

from .auth import load_account
from .accounts import load_local_account
from .client import DecentralisedArtClient
from .config import DEFAULT_API_BASE, DEFAULT_TIMEOUT, MAX_TIMEOUT_SECONDS, MIN_TIMEOUT_SECONDS
from .errors import AuthConfigurationError, ValidationError

ClientFactory = Callable[[str, float], Any]
AccountLoader = Callable[[Optional[str]], Any]

_CLIENT_FACTORY_OVERRIDE: ContextVar[Optional[ClientFactory]] = ContextVar("decentralised_art_mcp_client_factory_override", default=None)
_ACCOUNT_LOADER_OVERRIDE: ContextVar[Optional[AccountLoader]] = ContextVar("decentralised_art_mcp_account_loader_override", default=None)


def set_runtime_overrides(*, client_factory: Optional[ClientFactory] = None, account_loader: Optional[AccountLoader] = None) -> None:
    _CLIENT_FACTORY_OVERRIDE.set(client_factory)
    _ACCOUNT_LOADER_OVERRIDE.set(account_loader)


def clear_runtime_overrides() -> None:
    set_runtime_overrides(client_factory=None, account_loader=None)


@dataclass
class RuntimeContext:
    api_base: str = DEFAULT_API_BASE
    timeout: float = DEFAULT_TIMEOUT
    private_key: Optional[str] = None
    account_id: Optional[str] = None
    client_factory: Optional[ClientFactory] = None
    account_loader: Optional[AccountLoader] = None
    _client: Optional[Any] = field(default=None, init=False, repr=False)
    _account: Any = field(default=None, init=False, repr=False)

    def client(self) -> Any:
        if self._client is None:
            factory = self.client_factory or _CLIENT_FACTORY_OVERRIDE.get() or (lambda api_base, timeout: DecentralisedArtClient(api_base, timeout=timeout))
            self._client = factory(str(self.api_base), float(self.timeout))
        return self._client

    def close(self) -> None:
        client = self._client
        self._client = None
        close = getattr(client, "close", None)
        if callable(close):
            close()

    def __enter__(self) -> "RuntimeContext":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()

    def account(self, *, required: bool = True):
        if self._account is not None:
            return self._account
        if self.account_id is not None:
            self._account = load_local_account(self.account_id)
            return self._account
        loader = self.account_loader or _ACCOUNT_LOADER_OVERRIDE.get() or load_account
        try:
            self._account = loader(self.private_key)
            return self._account
        except Exception as exc:
            if not required:
                return None
            raise AuthConfigurationError(
                "Missing or invalid account configuration. Read core.documentation for onboarding. "
                "For a fresh identity, use core.create_account and pass its account_id; "
                "for an existing owner, configure PRIVATE_KEY locally. Never ask for a private key in chat.",
                details={"exception_type": exc.__class__.__name__},
            ) from exc


def context_from_params(params: Dict[str, Any]) -> RuntimeContext:
    if params.get("account_id") is not None and params.get("private_key") is not None:
        raise ValidationError("Use account_id or private_key, not both.")
    timeout = DEFAULT_TIMEOUT
    if "timeout" in params and params["timeout"] is not None:
        try:
            timeout = float(params["timeout"])
        except (TypeError, ValueError) as exc:
            raise ValidationError("params.timeout must be a positive number.", details={"path": "params.timeout"}) from exc
        if not math.isfinite(timeout) or timeout < MIN_TIMEOUT_SECONDS or timeout > MAX_TIMEOUT_SECONDS:
            raise ValidationError(
                f"params.timeout must be between {MIN_TIMEOUT_SECONDS} and {MAX_TIMEOUT_SECONDS} seconds.",
                details={"path": "params.timeout", "minimum": MIN_TIMEOUT_SECONDS, "maximum": MAX_TIMEOUT_SECONDS},
            )
    api_base = DEFAULT_API_BASE
    if "api_base" in params and params["api_base"] is not None:
        api_base = str(params["api_base"]).strip() or DEFAULT_API_BASE
    return RuntimeContext(
        api_base=api_base,
        timeout=timeout,
        private_key=params.get("private_key"),
        account_id=params.get("account_id"),
    )
