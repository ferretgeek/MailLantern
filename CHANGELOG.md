# Changelog

## 1.0.0 — 2026-08-09

- Initial stable release.
- Fixed-endpoint iCloud IMAP scanner with verified TLS, read-only `INBOX`, bounded `BODY.PEEK[]` fetches, optional recipient filtering, and reduced results.
- No database or credential persistence; passwords are cleared after each scan and browser tokens remain memory-only.
- Exact Host/Origin checks, CSP, body/response limits, rate limiting, concurrency control, and generic provider errors.
- Sky, Jade, Sunset, and Graphite themes with a privacy mask and responsive desktop/mobile layouts.
- Local, Docker, systemd, SSH-tunnel, and HTTPS reverse-proxy deployment paths.
- Explicit exclusion of Apple login credentials, 2FA, cookies, private APIs, mailbox mutation, and account automation.
