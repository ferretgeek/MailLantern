from __future__ import annotations

import json
import threading
import unittest
import urllib.error
import urllib.request

from mail_lantern.app import MAX_REQUEST_BYTES, MailLanternServer
from mail_lantern.config import AppConfig
from mail_lantern.scanner import ScanError, ScanRequest


class AppTests(unittest.TestCase):
    TOKEN = "test-access-token-that-is-long-enough"

    def setUp(self) -> None:
        self.received: list[ScanRequest] = []

        def scanner(request: ScanRequest) -> list[dict[str, object]]:
            self.received.append(request)
            return [
                {
                    "id": "safe-id",
                    "code": "482917",
                    "subject": "Verification code",
                    "sender": "s•••@e•••.invalid",
                    "recipient": "a•••@e•••.invalid",
                    "receivedAt": "2026-08-08T10:00:00Z",
                }
            ]

        config = AppConfig(
            bind_host="127.0.0.1",
            port=0,
            access_token=self.TOKEN,
            generated_access_token=False,
            allowed_hosts=frozenset({"127.0.0.1", "localhost"}),
            demo=False,
            allow_private_http=False,
        )
        self.app = MailLanternServer(config, scanner=scanner)
        self.port = self.app.address[1]
        self.thread = threading.Thread(target=self.app.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.app.shutdown()
        self.app.close()
        self.thread.join(timeout=2)

    def request(
        self,
        path: str,
        *,
        method: str = "GET",
        payload: dict[str, object] | None = None,
        raw_body: bytes | None = None,
        auth: bool = True,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, bytes, dict[str, str]]:
        request_headers = dict(headers or {})
        if auth:
            request_headers["Authorization"] = f"Bearer {self.TOKEN}"
        body = raw_body
        if payload is not None:
            body = json.dumps(payload).encode()
            request_headers.setdefault("Content-Type", "application/json")
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}",
            data=body,
            headers=request_headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=3) as response:  # noqa: S310
                return response.status, response.read(), dict(response.headers)
        except urllib.error.HTTPError as exc:
            with exc:
                return exc.code, exc.read(), dict(exc.headers)

    def origin_headers(self) -> dict[str, str]:
        return {"Origin": f"http://127.0.0.1:{self.port}", "Sec-Fetch-Site": "same-origin"}

    def valid_payload(self) -> dict[str, object]:
        return {"account": "user@example.com", "appPassword": "x" * 16, "latest": 10, "sinceMinutes": 30}

    def test_health_is_public(self) -> None:
        status, body, _headers = self.request("/health", auth=False)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["service"], "mail-lantern")

    def test_static_page_is_public_with_security_headers(self) -> None:
        status, body, headers = self.request("/", auth=False)
        self.assertEqual(status, 200)
        self.assertIn("iCloud 验证码".encode(), body)
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        self.assertEqual(headers["X-Frame-Options"], "DENY")
        self.assertNotIn("Access-Control-Allow-Origin", headers)

    def test_svg_has_safe_mime_type(self) -> None:
        status, body, headers = self.request("/favicon.svg", auth=False)
        self.assertEqual(status, 200)
        self.assertTrue(headers["Content-Type"].startswith("image/svg+xml"))
        self.assertTrue(body.startswith(b"<svg"))

    def test_bootstrap_requires_exact_bearer(self) -> None:
        status, _body, _headers = self.request("/api/bootstrap", auth=False)
        self.assertEqual(status, 401)
        status, _body, _headers = self.request(
            "/api/bootstrap", auth=False, headers={"Authorization": f"bearer {self.TOKEN}"}
        )
        self.assertEqual(status, 401)

    def test_bootstrap_exposes_only_fixed_provider_metadata(self) -> None:
        status, body, _headers = self.request("/api/bootstrap")
        payload = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(
            payload["provider"],
            {"name": "iCloud Mail", "host": "imap.mail.me.com", "port": 993},
        )
        self.assertEqual(payload["messages"], [])

    def test_scan_passes_validated_request_and_returns_result(self) -> None:
        status, body, _headers = self.request(
            "/api/scan", method="POST", payload=self.valid_payload(), headers=self.origin_headers()
        )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["count"], 1)
        self.assertEqual(self.received[0].account, "user@example.com")

    def test_invalid_host_is_rejected_without_echo(self) -> None:
        status, body, _headers = self.request("/health", auth=False, headers={"Host": "private.example"})
        self.assertEqual(status, 400)
        self.assertNotIn(b"private.example", body)

    def test_cross_origin_scan_is_rejected_after_body_is_consumed(self) -> None:
        for _attempt in range(3):
            status, _body, _headers = self.request(
                "/api/scan",
                method="POST",
                payload=self.valid_payload(),
                headers={"Origin": "http://127.0.0.1:9", "Sec-Fetch-Site": "same-origin"},
            )
            self.assertEqual(status, 403)
        self.assertEqual(self.received, [])

    def test_cross_site_fetch_is_rejected(self) -> None:
        status, _body, _headers = self.request(
            "/api/scan",
            method="POST",
            payload=self.valid_payload(),
            headers={"Sec-Fetch-Site": "cross-site"},
        )
        self.assertEqual(status, 403)

    def test_wrong_content_type_is_rejected_without_connection_reset(self) -> None:
        for _attempt in range(3):
            status, _body, _headers = self.request(
                "/api/scan",
                method="POST",
                raw_body=json.dumps(self.valid_payload()).encode(),
                headers={**self.origin_headers(), "Content-Type": "text/plain"},
            )
            self.assertEqual(status, 415)

    def test_oversize_body_is_rejected(self) -> None:
        for _attempt in range(3):
            status, _body, headers = self.request(
                "/api/scan",
                method="POST",
                raw_body=b"x" * (MAX_REQUEST_BYTES + 1),
                headers={**self.origin_headers(), "Content-Type": "application/json"},
            )
            self.assertEqual(status, 413)
            self.assertEqual(headers["Connection"], "close")

    def test_invalid_json_and_array_are_rejected_case(self) -> None:
        for body in (b"{", b"[]"):
            with self.subTest(body=body):
                status, _response, _headers = self.request(
                    "/api/scan",
                    method="POST",
                    raw_body=body,
                    headers={**self.origin_headers(), "Content-Type": "application/json"},
                )
                self.assertEqual(status, 400)

    def test_invalid_payload_does_not_reach_scanner(self) -> None:
        payload = self.valid_payload() | {"account": "not-email"}
        status, body, _headers = self.request(
            "/api/scan", method="POST", payload=payload, headers=self.origin_headers()
        )
        self.assertEqual(status, 400)
        self.assertIn(b"valid email", body)
        self.assertEqual(self.received, [])

    def test_options_does_not_grant_cors(self) -> None:
        status, _body, headers = self.request("/api/scan", method="OPTIONS", auth=False)
        self.assertEqual(status, 405)
        self.assertNotIn("Access-Control-Allow-Origin", headers)

    def test_path_traversal_is_not_served(self) -> None:
        status, _body, _headers = self.request("/%2e%2e/pyproject.toml", auth=False)
        self.assertEqual(status, 404)

    def test_not_found_does_not_echo_path(self) -> None:
        status, body, _headers = self.request("/api/private-looking-value")
        self.assertEqual(status, 404)
        self.assertNotIn(b"private-looking-value", body)


class DemoAppTests(unittest.TestCase):
    def test_demo_scan_never_calls_real_scanner_or_requires_credentials(self) -> None:
        called = False

        def scanner(_request: ScanRequest) -> list[dict[str, object]]:
            nonlocal called
            called = True
            raise ScanError("must not run")

        config = AppConfig("127.0.0.1", 0, "d" * 32, False, frozenset({"127.0.0.1"}), True, False)
        app = MailLanternServer(config, scanner=scanner)
        thread = threading.Thread(target=app.serve_forever, daemon=True)
        thread.start()
        try:
            port = app.address[1]
            request = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/scan",
                data=b"{}",
                headers={"Authorization": f"Bearer {'d' * 32}", "Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=3) as response:  # noqa: S310
                payload = json.loads(response.read())
            self.assertEqual(payload["count"], 3)
            self.assertFalse(called)
        finally:
            app.shutdown()
            app.close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
