from __future__ import annotations

import ipaddress
import os
import secrets
from dataclasses import dataclass


class ConfigError(ValueError):
    """Raised when deployment settings would create an unsafe service."""


def _flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _integer(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer") from exc
    if not minimum <= value <= maximum:
        raise ConfigError(f"{name} must be between {minimum} and {maximum}")
    return value


def _is_loopback(host: str) -> bool:
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host.split("%", 1)[0]).is_loopback
    except ValueError:
        return False


def _allowed_hosts(bind_host: str, configured: str) -> frozenset[str]:
    hosts = {item.strip().lower().rstrip(".") for item in configured.split(",") if item.strip()}
    if _is_loopback(bind_host):
        hosts.update({"localhost", "127.0.0.1", "::1"})
    elif not hosts:
        raise ConfigError("LANTERN_ALLOWED_HOSTS is required for a non-loopback bind")
    if any(host in {"*", "0.0.0.0", "::"} for host in hosts):  # nosec B104
        raise ConfigError("LANTERN_ALLOWED_HOSTS must list exact browser hostnames")
    return frozenset(hosts)


@dataclass(frozen=True, slots=True)
class AppConfig:
    bind_host: str
    port: int
    access_token: str
    generated_access_token: bool
    allowed_hosts: frozenset[str]
    demo: bool
    allow_private_http: bool

    @classmethod
    def from_env(cls, *, demo_override: bool | None = None) -> AppConfig:
        bind_host = os.getenv("LANTERN_BIND_HOST", "127.0.0.1").strip() or "127.0.0.1"
        port = _integer("LANTERN_PORT", 8769, 1, 65535)
        demo = _flag("LANTERN_DEMO") if demo_override is None else demo_override
        allow_private_http = _flag("LANTERN_ALLOW_PRIVATE_HTTP")
        token = os.getenv("LANTERN_ACCESS_TOKEN", "").strip()
        generated = False
        if not token and _is_loopback(bind_host):
            token = secrets.token_urlsafe(36)
            generated = True
        if len(token) < 24:
            raise ConfigError("LANTERN_ACCESS_TOKEN must contain at least 24 characters")
        if not _is_loopback(bind_host) and not allow_private_http:
            raise ConfigError(
                "non-loopback HTTP is disabled; bind to loopback behind HTTPS or set "
                "LANTERN_ALLOW_PRIVATE_HTTP=1 for an isolated private network"
            )
        return cls(
            bind_host=bind_host,
            port=port,
            access_token=token,
            generated_access_token=generated,
            allowed_hosts=_allowed_hosts(bind_host, os.getenv("LANTERN_ALLOWED_HOSTS", "")),
            demo=demo,
            allow_private_http=allow_private_http,
        )
