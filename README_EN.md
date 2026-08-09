# Mail Lantern · 信灯

[![Release](https://img.shields.io/github/v/release/ferretgeek/MailLantern?display_name=tag&style=flat-square)](https://github.com/ferretgeek/MailLantern/releases)
[![CI](https://img.shields.io/github/actions/workflow/status/ferretgeek/MailLantern/ci.yml?branch=main&style=flat-square&label=CI)](https://github.com/ferretgeek/MailLantern/actions/workflows/ci.yml)
[![CodeQL](https://img.shields.io/github/actions/workflow/status/ferretgeek/MailLantern/codeql.yml?branch=main&style=flat-square&label=CodeQL)](https://github.com/ferretgeek/MailLantern/actions/workflows/codeql.yml)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square)](https://www.python.org/)
[![License](https://img.shields.io/github/license/ferretgeek/MailLantern?style=flat-square)](./LICENSE)

> English · [中文](./README.md)

![Mail Lantern interface preview](./docs/images/social-preview.png)

Bring verification codes into the light, without leaving credentials behind. Mail Lantern reads recent messages through Apple's documented iCloud IMAP endpoint. An app-specific password exists only in memory for one request and is then cleared.

## Interface tour

![Verification-code results in Mail Lantern's synthetic demo](./docs/images/dashboard.png)

![Mail Lantern entry and privacy-boundary design](./docs/images/intro.png)

## Deliberately narrow

- Connects only to `imap.mail.me.com:993` with system-CA TLS verification.
- Opens `INBOX` read-only and fetches a bounded number of recent messages with `BODY.PEEK[]`.
- Filters by time and optional recipient, then finds likely 4–8 digit verification codes.
- Returns the code, subject, time, and masked sender/recipient identities.
- Includes responsive Sky, Jade, Sunset, and `#17191d` Graphite themes plus a privacy mask.

It does not store accounts, passwords, messages, or scan results. Apple login passwords, 2FA, cookies, tokens, private APIs, browser automation, and bulk account operations are out of scope.

## Run locally

Python 3.10+ is required. Runtime code uses only the Python standard library.

```bash
python -m venv .venv
# Windows
.venv\Scripts\python -m pip install .
.venv\Scripts\mail-lantern
# macOS / Linux
.venv/bin/python -m pip install .
.venv/bin/mail-lantern
```

Open the URL printed in the terminal, including its temporary `#token=` fragment. The browser removes the token from the address bar immediately after reading it.

Safe synthetic demo:

```bash
mail-lantern --demo
```

## Before scanning

1. Create an **app-specific password** for your Apple Account. Never enter your Apple login password.
2. Enter your iCloud email. Optionally enter a target alias, such as a Hide My Email address.
3. Choose a bounded message count and time window, then scan.

[Apple Support: Sign in to apps with your Apple Account using app-specific passwords](https://support.apple.com/102654)

## Deployment and security

Local mode binds to `127.0.0.1:8769`. On a server, keep the app on loopback and access it through an SSH tunnel or an HTTPS reverse proxy. Never expose plaintext HTTP to the public internet.

- [Deployment guide](./docs/DEPLOYMENT_EN.md)
- [Privacy boundary](./docs/PRIVACY.md)
- [Architecture](./docs/ARCHITECTURE.md)
- [Security policy](./SECURITY.md)

## Verify

```bash
python -m unittest discover -s tests -v
ruff check .
ruff format --check .
bandit -r src -ll
```

MIT License · [Contributing](./CONTRIBUTING.md)
