from __future__ import annotations

import datetime as dt
import hashlib
import html
import imaplib
import re
import ssl
from contextlib import suppress
from dataclasses import dataclass
from email import message_from_bytes
from email.header import decode_header
from email.message import Message
from email.utils import getaddresses, parsedate_to_datetime

from .security import clean_text, mask_email, normalize_email

IMAP_HOST = "imap.mail.me.com"
IMAP_PORT = 993
CODE_RE = re.compile(r"(?<!\d)(\d{4,8})(?!\d)")
TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")
KEYWORDS = (
    "verification",
    "verify",
    "security code",
    "one-time",
    "passcode",
    "otp",
    "验证码",
    "校验码",
    "动态码",
)


class ScanError(RuntimeError):
    """A safe, user-facing mailbox scan failure."""


@dataclass(frozen=True, slots=True)
class ScanRequest:
    account: str
    app_password: str
    expected_recipient: str
    latest: int = 30
    since_minutes: int = 180

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> ScanRequest:
        account = normalize_email(payload.get("account"))
        expected_raw = clean_text(payload.get("expectedRecipient"), limit=320)
        expected = normalize_email(expected_raw) if expected_raw else ""
        password = clean_text(payload.get("appPassword"), limit=128).replace(" ", "")
        if not 12 <= len(password) <= 128:
            raise ValueError("App-specific password must contain 12 to 128 characters")
        try:
            latest = int(payload.get("latest", 30))
            since = int(payload.get("sinceMinutes", 180))
        except (TypeError, ValueError) as exc:
            raise ValueError("scan limits must be integers") from exc
        if not 1 <= latest <= 50:
            raise ValueError("latest must be between 1 and 50")
        if not 5 <= since <= 1440:
            raise ValueError("sinceMinutes must be between 5 and 1440")
        return cls(account, password, expected, latest, since)


def _decode_header(value: str | None) -> str:
    chunks: list[str] = []
    for part, charset in decode_header(value or ""):
        if isinstance(part, bytes):
            for encoding in (charset, "utf-8", "latin-1"):
                if not encoding:
                    continue
                try:
                    chunks.append(part.decode(encoding, errors="replace"))
                    break
                except (LookupError, UnicodeDecodeError):
                    continue
        else:
            chunks.append(part)
    return clean_text("".join(chunks), limit=240)


def _message_text(message: Message) -> str:
    parts: list[str] = []
    iterator = message.walk() if message.is_multipart() else (message,)
    for part in iterator:
        if part.get_content_maintype() == "multipart" or part.get_filename():
            continue
        if part.get_content_type() not in {"text/plain", "text/html"}:
            continue
        payload = part.get_payload(decode=True)
        if not isinstance(payload, bytes):
            continue
        charset = part.get_content_charset() or "utf-8"
        try:
            text = payload.decode(charset, errors="replace")
        except LookupError:
            text = payload.decode("utf-8", errors="replace")
        if part.get_content_type() == "text/html":
            text = TAG_RE.sub(" ", html.unescape(text))
        parts.append(text)
        if sum(map(len, parts)) >= 200_000:
            break
    return SPACE_RE.sub(" ", " ".join(parts))[:200_000]


def _recipients(message: Message) -> set[str]:
    headers = ("To", "Cc", "Delivered-To", "X-Original-To", "Envelope-To")
    values = [value for name in headers for value in message.get_all(name, [])]
    recipients: set[str] = set()
    for _name, address in getaddresses(values):
        try:
            recipients.add(normalize_email(address))
        except ValueError:
            continue
    return recipients


def extract_code(subject: str, body: str) -> str:
    combined = f"{subject}\n{body}"
    candidates: list[tuple[int, int, str]] = []
    lower = combined.lower()
    for match in CODE_RE.finditer(combined):
        value = match.group(1)
        if len(value) == 4 and value.startswith(("19", "20")):
            continue
        left = max(match.start() - 90, 0)
        right = min(match.end() + 90, len(combined))
        context = lower[left:right]
        score = 10 if any(keyword in context for keyword in KEYWORDS) else 0
        score += 2 if len(value) == 6 else 0
        candidates.append((score, -match.start(), value))
    return max(candidates, default=(0, 0, ""))[2]


def _received_at(message: Message) -> dt.datetime:
    try:
        value = parsedate_to_datetime(message.get("Date", ""))
    except (TypeError, ValueError, OverflowError):
        value = None
    if value is None:
        return dt.datetime.now(dt.timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=dt.timezone.utc)
    return value.astimezone(dt.timezone.utc)


def _public_message(uid: str, message: Message, expected: str) -> dict[str, object] | None:
    recipients = _recipients(message)
    if expected and expected not in recipients:
        return None
    subject = _decode_header(message.get("Subject"))
    code = extract_code(subject, _message_text(message))
    if not code:
        return None
    sender_addresses = getaddresses(message.get_all("From", []))
    try:
        sender = normalize_email(sender_addresses[0][1]) if sender_addresses else ""
    except ValueError:
        sender = ""
    received = _received_at(message)
    stable = hashlib.sha256(f"{uid}|{received.isoformat()}|{subject}".encode()).hexdigest()[:12]
    shown_recipient = expected or (sorted(recipients)[0] if recipients else "")
    return {
        "id": stable,
        "code": code,
        "subject": subject or "未命名验证邮件",
        "sender": mask_email(sender) if sender else "未知发件人",
        "recipient": mask_email(shown_recipient) if shown_recipient else "未识别收件地址",
        "receivedAt": received.isoformat().replace("+00:00", "Z"),
    }


def _message_bytes(fetch_data: object) -> bytes | None:
    if not isinstance(fetch_data, list):
        return None
    for item in fetch_data:
        if isinstance(item, tuple) and len(item) >= 2 and isinstance(item[1], bytes):
            return item[1]
    return None


def scan_icloud(request: ScanRequest) -> list[dict[str, object]]:
    context = ssl.create_default_context()
    connection: imaplib.IMAP4_SSL | None = None
    try:
        connection = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT, ssl_context=context, timeout=12)
        connection.login(request.account, request.app_password)
        status, _ = connection.select("INBOX", readonly=True)
        if status != "OK":
            raise ScanError("无法以只读方式打开 INBOX")
        status, data = connection.uid("search", None, "ALL")
        if status != "OK" or not data or not isinstance(data[0], bytes):
            raise ScanError("邮箱没有返回可扫描的邮件列表")
        uids = data[0].split()[-request.latest :]
        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=request.since_minutes)
        results: list[dict[str, object]] = []
        for raw_uid in reversed(uids):
            uid = raw_uid.decode("ascii", errors="ignore")
            status, fetched = connection.uid("fetch", raw_uid, "(BODY.PEEK[])")
            raw_message = _message_bytes(fetched)
            if status != "OK" or not raw_message:
                continue
            message = message_from_bytes(raw_message)
            if _received_at(message) < cutoff:
                continue
            item = _public_message(uid, message, request.expected_recipient)
            if item:
                results.append(item)
        return results[:20]
    except imaplib.IMAP4.error as exc:
        raise ScanError("iCloud 拒绝了登录；请检查邮箱与 App 专用密码") from exc
    except (OSError, TimeoutError, ssl.SSLError) as exc:
        raise ScanError("无法安全连接 iCloud IMAP；请检查网络后重试") from exc
    finally:
        if connection is not None:
            with suppress(imaplib.IMAP4.error, OSError):
                connection.logout()


def demo_messages() -> list[dict[str, object]]:
    now = dt.datetime.now(dt.timezone.utc)
    return [
        {
            "id": "demo-lantern-01",
            "code": "482917",
            "subject": "Your verification code",
            "sender": "n•••••@e••••.invalid",
            "recipient": "q•••••@e••••.invalid",
            "receivedAt": (now - dt.timedelta(minutes=2)).isoformat().replace("+00:00", "Z"),
        },
        {
            "id": "demo-lantern-02",
            "code": "731204",
            "subject": "Security code for your sign-in",
            "sender": "s•••••@e••••.invalid",
            "recipient": "p•••••@e••••.invalid",
            "receivedAt": (now - dt.timedelta(minutes=11)).isoformat().replace("+00:00", "Z"),
        },
        {
            "id": "demo-lantern-03",
            "code": "905638",
            "subject": "Confirm this email address",
            "sender": "h•••••@e••••.invalid",
            "recipient": "f•••••@e••••.invalid",
            "receivedAt": (now - dt.timedelta(minutes=28)).isoformat().replace("+00:00", "Z"),
        },
    ]
