from __future__ import annotations

import json
import logging
import mimetypes
import threading
from collections.abc import Callable
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from .config import AppConfig
from .scanner import IMAP_HOST, IMAP_PORT, ScanError, ScanRequest, demo_messages, scan_icloud
from .security import SlidingWindowLimiter, bearer_matches, host_allowed, same_origin

LOGGER = logging.getLogger("mail_lantern")
MAX_REQUEST_BYTES = 32 * 1024
MAX_RESPONSE_BYTES = 1024 * 1024
STATIC_ROOT = Path(str(files("mail_lantern").joinpath("static"))).resolve()
CONTENT_TYPES = {
    ".css": "text/css; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".ico": "image/x-icon",
    ".js": "text/javascript; charset=utf-8",
    ".png": "image/png",
    ".svg": "image/svg+xml",
}
SECURITY_HEADERS = {
    "Cache-Control": "no-store",
    "Content-Security-Policy": (
        "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
        "connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; "
        "frame-ancestors 'none'"
    ),
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
}
ScanFunction = Callable[[ScanRequest], list[dict[str, object]]]


class MailLanternHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        address: tuple[str, int],
        config: AppConfig,
        scanner: ScanFunction,
    ) -> None:
        self.config = config
        self.scanner = scanner
        self.limiter = SlidingWindowLimiter(limit=12, window_seconds=60)
        self.scan_slots = threading.BoundedSemaphore(4)
        super().__init__(address, MailLanternHandler)


class MailLanternHandler(BaseHTTPRequestHandler):
    server: MailLanternHTTPServer
    protocol_version = "HTTP/1.1"
    server_version = "MailLantern"
    sys_version = ""

    def log_message(self, format: str, *args: object) -> None:
        LOGGER.info("%s - %s", self.client_address[0], format % args)

    def _headers(self, status: int, content_type: str, length: int) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        for name, value in SECURITY_HEADERS.items():
            self.send_header(name, value)
        self.end_headers()

    def _bytes(self, status: int, body: bytes, content_type: str) -> None:
        if len(body) > MAX_RESPONSE_BYTES:
            body = b'{"ok":false,"error":"response too large"}'
            status = HTTPStatus.INTERNAL_SERVER_ERROR
            content_type = "application/json; charset=utf-8"
        self._headers(status, content_type, len(body))
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self._bytes(status, body, "application/json; charset=utf-8")

    def _reject(self, status: int, message: str) -> None:
        self._json(status, {"ok": False, "error": message})

    def _host_valid(self) -> bool:
        return host_allowed(self.headers.get("Host"), self.server.config.allowed_hosts)

    def _authorized(self) -> bool:
        return bearer_matches(self.headers.get("Authorization"), self.server.config.access_token)

    def _origin_valid(self) -> bool:
        if not same_origin(self.headers.get("Origin"), self.headers.get("Host")):
            return False
        return self.headers.get("Sec-Fetch-Site", "same-origin") in {"same-origin", "none"}

    def _client_key(self) -> str:
        return self.client_address[0]

    def _read_json_body(self) -> dict[str, object] | None:
        raw_length = self.headers.get("Content-Length")
        try:
            length = int(raw_length or "0")
        except ValueError:
            self._reject(HTTPStatus.BAD_REQUEST, "invalid content length")
            return None
        if length <= 0 or length > MAX_REQUEST_BYTES:
            self._reject(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "request body must be 1 to 32768 bytes")
            return None
        body = self.rfile.read(length)
        try:
            value: Any = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._reject(HTTPStatus.BAD_REQUEST, "invalid JSON body")
            return None
        if not isinstance(value, dict):
            self._reject(HTTPStatus.BAD_REQUEST, "JSON body must be an object")
            return None
        return value

    def _static_path(self) -> Path | None:
        path = unquote(urlsplit(self.path).path)
        if path in {"", "/"}:
            path = "/index.html"
        candidate = (STATIC_ROOT / path.lstrip("/")).resolve()
        try:
            candidate.relative_to(STATIC_ROOT)
        except ValueError:
            return None
        return candidate if candidate.is_file() else None

    def _serve_static(self) -> None:
        target = self._static_path()
        if target is None:
            self._reject(HTTPStatus.NOT_FOUND, "not found")
            return
        content_type = CONTENT_TYPES.get(target.suffix.lower()) or mimetypes.guess_type(target.name)[0]
        self._bytes(HTTPStatus.OK, target.read_bytes(), content_type or "application/octet-stream")

    def _bootstrap(self) -> None:
        if not self._authorized():
            self._reject(HTTPStatus.UNAUTHORIZED, "access token required")
            return
        self._json(
            HTTPStatus.OK,
            {
                "ok": True,
                "demo": self.server.config.demo,
                "provider": {"name": "iCloud Mail", "host": IMAP_HOST, "port": IMAP_PORT},
                "messages": demo_messages() if self.server.config.demo else [],
            },
        )

    def do_GET(self) -> None:  # noqa: N802
        path = urlsplit(self.path).path
        if not self._host_valid():
            self._reject(HTTPStatus.BAD_REQUEST, "invalid host")
        elif path == "/health":
            self._json(HTTPStatus.OK, {"ok": True, "service": "mail-lantern"})
        elif path == "/api/bootstrap":
            self._bootstrap()
        elif path.startswith("/api/"):
            self._reject(HTTPStatus.NOT_FOUND, "not found")
        else:
            self._serve_static()

    def do_HEAD(self) -> None:  # noqa: N802
        self.do_GET()

    def do_POST(self) -> None:  # noqa: N802
        path = urlsplit(self.path).path
        if not self._host_valid():
            self._reject(HTTPStatus.BAD_REQUEST, "invalid host")
            return
        if path != "/api/scan":
            self._reject(HTTPStatus.NOT_FOUND, "not found")
            return
        if not self._authorized():
            self._reject(HTTPStatus.UNAUTHORIZED, "access token required")
            return

        # Consume one bounded body after the cheap Host/token checks. This keeps the
        # connection reusable even when a later policy check rejects the request.
        payload = self._read_json_body()
        if payload is None:
            return
        if not self._origin_valid():
            self._reject(HTTPStatus.FORBIDDEN, "same-origin request required")
            return
        content_type = self.headers.get("Content-Type", "").partition(";")[0].strip().lower()
        if content_type != "application/json":
            self._reject(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "application/json required")
            return
        if not self.server.limiter.allow(self._client_key()):
            self._reject(HTTPStatus.TOO_MANY_REQUESTS, "too many scan requests; try again shortly")
            return
        if not self.server.scan_slots.acquire(blocking=False):
            self._reject(HTTPStatus.SERVICE_UNAVAILABLE, "scanner is busy; try again shortly")
            return
        try:
            if self.server.config.demo:
                messages = demo_messages()
            else:
                try:
                    request = ScanRequest.from_payload(payload)
                except ValueError as exc:
                    self._reject(HTTPStatus.BAD_REQUEST, str(exc))
                    return
                try:
                    messages = self.server.scanner(request)
                except ScanError as exc:
                    self._reject(HTTPStatus.BAD_GATEWAY, str(exc))
                    return
            self._json(HTTPStatus.OK, {"ok": True, "messages": messages, "count": len(messages)})
        except Exception:
            LOGGER.exception("unexpected scan failure")
            self._reject(HTTPStatus.INTERNAL_SERVER_ERROR, "scan failed safely; please try again")
        finally:
            self.server.scan_slots.release()

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._reject(HTTPStatus.METHOD_NOT_ALLOWED, "method not allowed")

    def do_PUT(self) -> None:  # noqa: N802
        self._reject(HTTPStatus.METHOD_NOT_ALLOWED, "method not allowed")

    def do_DELETE(self) -> None:  # noqa: N802
        self._reject(HTTPStatus.METHOD_NOT_ALLOWED, "method not allowed")


class MailLanternServer:
    def __init__(self, config: AppConfig, *, scanner: ScanFunction = scan_icloud) -> None:
        self._server = MailLanternHTTPServer((config.bind_host, config.port), config, scanner)

    @property
    def address(self) -> tuple[str, int]:
        host, port = self._server.server_address[:2]
        return str(host), int(port)

    def serve_forever(self) -> None:
        self._server.serve_forever(poll_interval=0.25)

    def shutdown(self) -> None:
        self._server.shutdown()

    def close(self) -> None:
        self._server.server_close()

    def __enter__(self) -> MailLanternServer:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
