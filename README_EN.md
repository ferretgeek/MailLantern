# iCloud code finder

[中文](./README.md) · English

[![Release](https://img.shields.io/github/v/release/ferretgeek/icloud-code-finder?display_name=tag&style=flat-square)](https://github.com/ferretgeek/icloud-code-finder/releases)
[![CI](https://img.shields.io/github/actions/workflow/status/ferretgeek/icloud-code-finder/ci.yml?branch=main&style=flat-square&label=CI)](https://github.com/ferretgeek/icloud-code-finder/actions/workflows/ci.yml)
[![CodeQL](https://img.shields.io/github/actions/workflow/status/ferretgeek/icloud-code-finder/codeql.yml?branch=main&style=flat-square&label=CodeQL)](https://github.com/ferretgeek/icloud-code-finder/actions/workflows/codeql.yml)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square)](https://www.python.org/)
[![License](https://img.shields.io/github/license/ferretgeek/icloud-code-finder?style=flat-square)](./LICENSE)

![Interface preview](./docs/images/social-preview.png)

> Pull verification codes straight out of recent iCloud mail. App-specific password, read-only, forgotten immediately.

## Why this exists

The thirty seconds spent waiting for a code is the annoying part: switch to Mail, pull to refresh, open the message, long-press the six digits, copy, switch back. If you use Hide My Email you may also have to work out which alias it went to first.

This compresses that into one action: enter the address, pick a time range, scan, and the codes are listed.

**It stores nothing.** The app-specific password exists only in memory for one request and is cleared afterwards; messages, results, and addresses never touch disk. Senders and recipients are masked on screen by default.

## Interface

![Verification-code results in the synthetic demo](./docs/images/dashboard.png)

![Entry point and privacy boundaries](./docs/images/intro.png)

## It deliberately does only this

- Connects to a fixed `imap.mail.me.com:993` with TLS validated against the system CA store.
- Opens `INBOX` **read-only**: reads `RFC822.SIZE` and limited headers first, then fetches recent messages via a `BODY.PEEK[]` range capped at 1 MiB; oversized or corrupt messages are skipped individually.
- Filters by time and target recipient address, and detects 4–8 digit codes.
- Returns the code, subject, and timestamp, with **masked** sender and recipient.
- Ships Clear Sky, Jade, Sunset, and deep-gray global themes, privacy masking, and a responsive interface.

It **never** stores addresses, passwords, messages, or results, and **never** uses your Apple password, 2FA, cookies, tokens, private APIs, browser automation, or bulk account operations.

## Running locally

Requires Python 3.10+ and uses only the Python standard library at runtime.

```bash
python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\python -m pip install .
.venv\Scripts\mail-lantern
```

macOS / Linux:

```bash
.venv/bin/python -m pip install .
.venv/bin/mail-lantern
```

Open the URL printed in the terminal, which carries a temporary `#token=` fragment. The browser reads it and removes it from the address bar immediately.

To look at fictional data only:

```bash
mail-lantern --demo
```

## Before you start

1. Create an **app-specific password** in your Apple account settings — **never enter your Apple sign-in password.**
2. Enter your iCloud address. To look at one Hide My Email address or alias, enter that as the target recipient.
3. Choose a message count and time range, then scan.

Reference: [Apple — using app-specific passwords](https://support.apple.com/102654)

## Worth noting technically

**Fetching happens in two steps, to avoid downloading large attachments.** It reads `RFC822.SIZE` and limited headers first to decide whether a message is worth fetching, then retrieves a `BODY.PEEK[]` range capped at 1 MiB. `PEEK` means **messages are never marked as read** — the unread state on your phone doesn't change because you scanned.

**Oversized and corrupt messages are skipped individually.** One malformed message doesn't fail the whole scan; it's recorded as skipped and the scan continues.

**It works without JavaScript, and still doesn't leak.** Even with JavaScript disabled, the form only uses POST — **the address and password never appear in a URL**, so they can't reach browser history, a Referer header, or server logs.

**The access token travels in a URL fragment.** Browsers never send fragments to the server, and the frontend strips it from the address bar immediately.

**The destination is hard-coded.** It connects only to Apple's published iCloud IMAP host. A tool that will take your app-specific password to an arbitrary host is a phishing tool.

## Deployment and security

Locally it binds `127.0.0.1:8769` only.

Server deployments **must** keep the application on the loopback address and be reached through an SSH tunnel or HTTPS reverse proxy. **Never expose plaintext HTTP to the internet.**

## What it doesn't do

- No sending, deleting, marking as read, or modifying anything in the mailbox.
- No Apple sign-in password, no 2FA / cookie / token sign-in.
- No undocumented Apple APIs, no browser automation, no bulk account operations.
- No storage of addresses, passwords, messages, or results.

## Verification

```bash
python -m unittest discover -s tests -v
ruff check .
ruff format --check .
bandit -r src -ll
```

## More documentation

[Deployment](./docs/DEPLOYMENT_EN.md) · [Privacy](./docs/PRIVACY.md) · [Architecture](./docs/ARCHITECTURE.md) · [Release audit](./docs/发布审计.md) · [Changelog](./CHANGELOG.md) · [Contributing](./CONTRIBUTING.md) · [Security policy](./SECURITY.md)

## License and disclaimer

MIT License — see [LICENSE](./LICENSE).

Independent community project with no affiliation with, authorization from, or endorsement by Apple. Use it only with your own mailbox.
