from __future__ import annotations

import unittest
from unittest.mock import patch

from mail_lantern.security import (
    SlidingWindowLimiter,
    bearer_matches,
    clean_text,
    host_allowed,
    mask_email,
    normalize_email,
    same_origin,
)


class SecurityTests(unittest.TestCase):
    def test_email_is_normalized(self) -> None:
        self.assertEqual(normalize_email("  Leaf.Path@Example.COM "), "leaf.path@example.com")

    def test_invalid_email_is_rejected(self) -> None:
        for value in ("missing-at", "a@@example.com", "a@example", "a..b@example.com"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_email(value)

    def test_text_is_bounded_and_control_characters_removed(self) -> None:
        self.assertEqual(clean_text(" a\x00b\n ", limit=2), "ab")
        with self.assertRaisesRegex(ValueError, "2"):
            clean_text("abc", limit=2)

    def test_email_mask_hides_local_and_domain(self) -> None:
        masked = mask_email("leaf.path@example.com")
        self.assertNotIn("leaf.path", masked)
        self.assertNotIn("example", masked)
        self.assertTrue(masked.endswith(".com"))

    def test_bearer_auth_is_exact(self) -> None:
        self.assertTrue(bearer_matches("Bearer " + "x" * 32, "x" * 32))
        self.assertFalse(bearer_matches("bearer " + "x" * 32, "x" * 32))
        self.assertFalse(bearer_matches(None, "x" * 32))

    def test_host_allowlist_handles_ports_and_ipv6(self) -> None:
        allowed = frozenset({"localhost", "::1"})
        self.assertTrue(host_allowed("localhost:8769", allowed))
        self.assertTrue(host_allowed("[::1]:8769", allowed))
        self.assertFalse(host_allowed("localhost.example", allowed))

    def test_host_header_rejects_injection(self) -> None:
        allowed = frozenset({"localhost"})
        for value in (None, "localhost/evil", "user@localhost", "localhost\r\nx: y"):
            self.assertFalse(host_allowed(value, allowed))

    def test_same_origin_requires_exact_authority(self) -> None:
        self.assertTrue(same_origin("http://localhost:8769", "localhost:8769"))
        self.assertFalse(same_origin("http://localhost:9999", "localhost:8769"))
        self.assertFalse(same_origin("https://example.com", "example.com:443"))

    def test_missing_origin_is_allowed_for_non_browser_clients(self) -> None:
        self.assertTrue(same_origin(None, "localhost:8769"))

    def test_origin_with_credentials_is_rejected_case(self) -> None:
        credentialed_origin = "https://" + "user" + ":" + "pass" + "@example.com"
        self.assertFalse(same_origin(credentialed_origin, "example.com"))

    def test_sliding_window_rate_limit(self) -> None:
        limiter = SlidingWindowLimiter(limit=2, window_seconds=10)
        with patch("mail_lantern.security.time.monotonic", side_effect=[1.0, 2.0, 3.0, 12.1]):
            self.assertTrue(limiter.allow("client"))
            self.assertTrue(limiter.allow("client"))
            self.assertFalse(limiter.allow("client"))
            self.assertTrue(limiter.allow("client"))


if __name__ == "__main__":
    unittest.main()
