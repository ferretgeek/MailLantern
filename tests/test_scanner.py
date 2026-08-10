from __future__ import annotations

import datetime as dt
import imaplib
import unittest
from email.message import EmailMessage
from unittest.mock import patch

from mail_lantern.scanner import (
    IMAP_HOST,
    IMAP_PORT,
    ScanError,
    ScanRequest,
    _public_message,
    demo_messages,
    extract_code,
    scan_icloud,
)


def sample_message(
    *,
    subject: str = "Your verification code is 482917",
    body: str = "Use 482917 to continue.",
    recipient: str = "alias@example.invalid",
    sender: str = "security@example.invalid",
    minutes_ago: int = 1,
) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = recipient
    when = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=minutes_ago)
    message["Date"] = when.strftime("%a, %d %b %Y %H:%M:%S +0000")
    message.set_content(body)
    return message


class FakeIMAP:
    message = sample_message().as_bytes()
    login_error = False
    last_host = ""
    last_port = 0
    readonly = False
    fetch_command: tuple[object, ...] = ()
    fetch_commands: list[tuple[object, ...]] = []
    reported_size: int | None = None

    def __init__(self, host: str, port: int, **_kwargs: object) -> None:
        type(self).last_host = host
        type(self).last_port = port

    def login(self, _account: str, _password: str) -> None:
        if type(self).login_error:
            raise imaplib.IMAP4.error("raw provider detail")

    def select(self, mailbox: str, *, readonly: bool = False) -> tuple[str, list[bytes]]:
        self.assert_mailbox = mailbox
        type(self).readonly = readonly
        return "OK", [b"1"]

    def uid(self, command: str, *args: object) -> tuple[str, list[object]]:
        if command == "search":
            return "OK", [b"1"]
        type(self).fetch_command = (command, *args)
        type(self).fetch_commands.append((command, *args))
        query = str(args[-1]) if args else ""
        if "RFC822.SIZE" in query:
            size = type(self).reported_size or len(type(self).message)
            return "OK", [(f"1 (RFC822.SIZE {size} BODY[] {{{len(type(self).message)}}})".encode(), type(self).message)]
        return "OK", [(b"1 (BODY[] {1})", type(self).message)]

    def logout(self) -> None:
        return None


class ScannerTests(unittest.TestCase):
    def tearDown(self) -> None:
        FakeIMAP.login_error = False
        FakeIMAP.message = sample_message().as_bytes()
        FakeIMAP.fetch_commands = []
        FakeIMAP.reported_size = None

    def test_payload_is_normalized_and_spaces_removed_from_password(self) -> None:
        payload: dict[str, object] = {
            "account": "USER@EXAMPLE.COM",
            "latest": "10",
            "sinceMinutes": "30",
        }
        payload["app" + "Password"] = " ".join(("abcd", "efgh", "ijkl"))
        request = ScanRequest.from_payload(payload)
        self.assertEqual(request.account, "user@example.com")
        self.assertEqual(request.app_password, "abcdefghijkl")
        self.assertEqual((request.latest, request.since_minutes), (10, 30))

    def test_payload_bounds_are_enforced(self) -> None:
        base = {"account": "user@example.com", "appPassword": "x" * 16}
        for field, value in (("latest", 51), ("sinceMinutes", 4)):
            with self.subTest(field=field), self.assertRaises(ValueError):
                ScanRequest.from_payload({**base, field: value})

    def test_expected_recipient_must_be_email(self) -> None:
        with self.assertRaises(ValueError):
            ScanRequest.from_payload(
                {"account": "user@example.com", "appPassword": "x" * 16, "expectedRecipient": "nope"}
            )

    def test_code_extraction_prefers_keyword_context(self) -> None:
        self.assertEqual(extract_code("Invoice 8142", "Verification code: 731204"), "731204")

    def test_likely_year_is_ignored(self) -> None:
        self.assertEqual(extract_code("Welcome 2026", "No security value here"), "")

    def test_html_message_is_parsed_and_identifiers_are_masked(self) -> None:
        message = EmailMessage()
        message["Subject"] = "验证邮件"
        message["From"] = "Private Sender <sender@example.invalid>"
        message["To"] = "alias@example.invalid"
        message["Date"] = "Fri, 08 Aug 2026 10:00:00 +0000"
        message.set_content("Fallback")
        message.add_alternative("<p>您的验证码是 <b>638241</b></p>", subtype="html")
        item = _public_message("42", message, "alias@example.invalid")
        self.assertIsNotNone(item)
        serialized = str(item)
        self.assertIn("638241", serialized)
        self.assertNotIn("sender@example", serialized)
        self.assertNotIn("alias@example", serialized)

    def test_recipient_filter_discards_other_aliases(self) -> None:
        item = _public_message("42", sample_message(), "other@example.invalid")
        self.assertIsNone(item)

    def test_scan_uses_only_fixed_official_endpoint_and_readonly_fetch(self) -> None:
        request = ScanRequest("user@example.com", "x" * 16, "alias@example.invalid", 30, 180)
        with patch("mail_lantern.scanner.imaplib.IMAP4_SSL", FakeIMAP):
            results = scan_icloud(request)
        self.assertEqual((FakeIMAP.last_host, FakeIMAP.last_port), (IMAP_HOST, IMAP_PORT))
        self.assertTrue(FakeIMAP.readonly)
        self.assertIn("BODY.PEEK[]<0.", str(FakeIMAP.fetch_command))
        self.assertTrue(any("RFC822.SIZE" in str(command) for command in FakeIMAP.fetch_commands))
        self.assertEqual(len(results), 1)

    def test_oversized_message_is_skipped_before_body_fetch(self) -> None:
        FakeIMAP.reported_size = 1024 * 1024 + 1
        request = ScanRequest("user@example.com", "x" * 16, "", 30, 180)
        with patch("mail_lantern.scanner.imaplib.IMAP4_SSL", FakeIMAP):
            self.assertEqual(scan_icloud(request), [])
        self.assertEqual(len(FakeIMAP.fetch_commands), 1)

    def test_long_subject_is_truncated_without_aborting_message(self) -> None:
        message = sample_message(subject=("A" * 400) + " verification code 482917")
        item = _public_message("42", message, "alias@example.invalid")
        self.assertIsNotNone(item)
        self.assertLessEqual(len(str(item["subject"])), 240)

    def test_old_messages_are_not_returned(self) -> None:
        FakeIMAP.message = sample_message(minutes_ago=500).as_bytes()
        request = ScanRequest("user@example.com", "x" * 16, "", 30, 30)
        with patch("mail_lantern.scanner.imaplib.IMAP4_SSL", FakeIMAP):
            self.assertEqual(scan_icloud(request), [])

    def test_provider_login_error_is_redacted(self) -> None:
        FakeIMAP.login_error = True
        request = ScanRequest("user@example.com", "x" * 16, "", 30, 180)
        with (
            patch("mail_lantern.scanner.imaplib.IMAP4_SSL", FakeIMAP),
            self.assertRaises(ScanError) as caught,
        ):
            scan_icloud(request)
        self.assertNotIn("raw provider detail", str(caught.exception))

    def test_demo_uses_reserved_domains_and_unique_ids(self) -> None:
        messages = demo_messages()
        self.assertEqual(len(messages), 3)
        self.assertEqual(len({item["id"] for item in messages}), 3)
        self.assertTrue(all(".invalid" in str(item) for item in messages))


if __name__ == "__main__":
    unittest.main()
