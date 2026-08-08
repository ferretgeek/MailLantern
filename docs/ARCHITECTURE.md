# Architecture and trust boundary

```text
Browser
  │ same-origin HTTPS/loopback HTTP + memory-only bearer token
  ▼
Mail Lantern HTTP server
  │ one bounded request; no database, cache, analytics, or logs with payloads
  ▼
Python imaplib + verified TLS
  │ fixed destination: imap.mail.me.com:993
  ▼
iCloud INBOX (read-only)
```

## Components

- `app.py` serves bundled assets and two authenticated API routes. It enforces exact Host and Origin checks, CSP, body/response limits, a per-client sliding-window limit, and four concurrent scan slots.
- `scanner.py` validates the request, establishes a verified IMAP-over-TLS connection, opens `INBOX` read-only, bounds the UID window, fetches with `BODY.PEEK[]`, and returns at most 20 reduced records.
- `security.py` handles bounded text, email validation/masking, constant-time bearer comparison, and request-boundary checks.
- `static/` is dependency-free HTML, CSS, and JavaScript. Only theme preference enters `localStorage`; credentials, tokens, messages, and results do not.

## Data lifecycle

The account and app-specific password travel in one same-origin request. They exist in browser form state, the bounded request body, a `ScanRequest`, and the active IMAP connection. The password field is cleared in a `finally` block. The server has no persistence layer, and its access log records only client IP and request line—not headers or bodies.

Returned records contain the verification code, bounded subject, timestamp, a stable non-secret hash-derived ID, and masked sender/recipient addresses. MIME bodies are capped at 200 KiB and are never returned.

## Threat model

Controls address DNS rebinding, cross-site request attempts, token guessing, oversized payloads, scanner saturation, MIME/resource exhaustion, path traversal, accidental credential persistence, and error-detail leakage. The project does not protect a compromised browser, host, Python runtime, TLS trust store, Apple Account, or reverse proxy. A server operator can inspect process memory; deploy only on a host you trust.

## Non-goals

Apple authentication automation, login passwords, 2FA handling, cookies, private APIs, alias creation, mailbox mutation, full-message browsing, credential vaulting, and multi-user tenancy are intentionally excluded.
