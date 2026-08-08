from __future__ import annotations

import hmac
import re
import threading
import time
from collections import defaultdict, deque
from urllib.parse import urlsplit

EMAIL_RE = re.compile(r"^[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Z0-9.-]+\.[A-Z]{2,63}$", re.I)
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def clean_text(value: object, *, limit: int) -> str:
    text = CONTROL_RE.sub("", str(value or "")).strip()
    if len(text) > limit:
        raise ValueError(f"text exceeds {limit} characters")
    return text


def normalize_email(value: object) -> str:
    email = clean_text(value, limit=320).lower()
    if not EMAIL_RE.fullmatch(email) or ".." in email:
        raise ValueError("valid email address required")
    return email


def mask_email(value: str) -> str:
    local, domain = value.split("@", 1)
    domain_name, dot, suffix = domain.partition(".")
    masked_local = local[:1] + "•" * min(max(len(local) - 1, 3), 6)
    masked_domain = domain_name[:1] + "•" * min(max(len(domain_name) - 1, 3), 6)
    return f"{masked_local}@{masked_domain}{dot}{suffix}"


def bearer_matches(header: str | None, expected: str) -> bool:
    prefix = "Bearer "
    return bool(header and header.startswith(prefix) and hmac.compare_digest(header[len(prefix) :], expected))


def host_allowed(header: str | None, allowed_hosts: frozenset[str]) -> bool:
    if not header or any(char in header for char in "\r\n/@"):
        return False
    candidate = header.strip().lower()
    if candidate.startswith("["):
        end = candidate.find("]")
        if end < 0:
            return False
        host = candidate[1:end]
    else:
        host = candidate.rsplit(":", 1)[0] if candidate.count(":") == 1 else candidate
    return host.rstrip(".") in allowed_hosts


def same_origin(origin: str | None, host_header: str | None) -> bool:
    if not origin:
        return True
    if not host_header:
        return False
    try:
        parsed = urlsplit(origin)
    except ValueError:
        return False
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
        return False
    return parsed.netloc.lower().rstrip(".") == host_header.lower().rstrip(".")


class SlidingWindowLimiter:
    def __init__(self, *, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, *, now: float | None = None) -> bool:
        moment = time.monotonic() if now is None else now
        cutoff = moment - self.window_seconds
        with self._lock:
            bucket = self._events[key]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= self.limit:
                return False
            bucket.append(moment)
            return True
