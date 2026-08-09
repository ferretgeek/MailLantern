# Changelog

## Unreleased

- Promoted the populated synthetic verification-code results to the profile and social preview, while retaining the full results view and entry composition as complementary README images.

## 1.0.2 — 2026-08-09

- Reissued the reachable Git history after an adversarial scan found credential-shaped test identifiers; the findings were synthetic names, not real secrets.
- Retired the immutable `v1.0.0` and `v1.0.1` tags and moved the clean release line to `v1.0.2`, so fresh full-history and all-tag scans return zero findings.
- Includes the fixed-asset serving, origin validation, bounded request handling, compatibility, UI, and documentation hardening completed during the public audit.

## 1.0.1 — 2026-08-09

- Replace the Python 3.11-only `datetime.UTC` alias with `datetime.timezone.utc`, restoring the documented Python 3.10 compatibility in scanner, demo, and tests.
- Construct the synthetic app-password fixture without a secret-shaped key/value literal so strict cross-platform secret scans remain deterministic.
- Rate-limit before body reads and safely drain one bounded oversized authenticated request before returning `413`, avoiding intermittent Windows connection resets without allowing unbounded request consumption.

## 1.0.0 — 2026-08-09

- Initial stable release.
- Fixed-endpoint iCloud IMAP scanner with verified TLS, read-only `INBOX`, bounded `BODY.PEEK[]` fetches, optional recipient filtering, and reduced results.
- No database or credential persistence; passwords are cleared after each scan and browser tokens remain memory-only.
- Exact Host/Origin checks, CSP, body/response limits, rate limiting, concurrency control, and generic provider errors.
- Sky, Jade, Sunset, and Graphite themes with a privacy mask and responsive desktop/mobile layouts.
- Local, Docker, systemd, SSH-tunnel, and HTTPS reverse-proxy deployment paths.
- Explicit exclusion of Apple login credentials, 2FA, cookies, private APIs, mailbox mutation, and account automation.
