# Deployment guide

## Option 1: local (recommended)

```bash
python -m venv .venv
# Windows
.venv\Scripts\python -m pip install .
.venv\Scripts\mail-lantern
# macOS / Linux
.venv/bin/python -m pip install .
.venv/bin/mail-lantern
```

Open the printed `http://127.0.0.1:8769/#token=...` URL. The fragment is removed immediately and is never written to browser storage. Stop with `Ctrl+C`.

Use `mail-lantern --demo` for reserved synthetic messages without contacting iCloud.

## Option 2: server plus SSH tunnel

Keep the default loopback bind on the server:

```bash
python3 -m venv /opt/mail-lantern/.venv
/opt/mail-lantern/.venv/bin/pip install /opt/mail-lantern
export LANTERN_ACCESS_TOKEN="$(/opt/mail-lantern/.venv/bin/mail-lantern token)"
/opt/mail-lantern/.venv/bin/mail-lantern
```

Forward it from your workstation:

```bash
ssh -N -L 8769:127.0.0.1:8769 user@example.invalid
```

Visit `http://127.0.0.1:8769/` and enter the server-generated token. Replace the reserved example host with your own.

## Option 3: Docker Compose

Create an uncommitted `.env`:

```dotenv
LANTERN_ACCESS_TOKEN=replace-with-at-least-24-random-characters
LANTERN_ALLOWED_HOSTS=localhost,127.0.0.1
```

```bash
docker compose up -d --build
docker compose ps
```

The Compose file binds only to host loopback, uses a read-only container, drops Linux capabilities, and disables privilege escalation. Outbound TCP 993 to Apple IMAP is required.

## HTTPS reverse proxy

Keep the app on `127.0.0.1:8769` and configure a strong token and exact public hostname:

```dotenv
LANTERN_BIND_HOST=127.0.0.1
LANTERN_PORT=8769
LANTERN_ACCESS_TOKEN=replace-with-a-random-secret
LANTERN_ALLOWED_HOSTS=lantern.example.invalid
```

Adapt [`deploy/nginx.conf.example`](../deploy/nginx.conf.example) and [`deploy/mail-lantern.service`](../deploy/mail-lantern.service). Replace all `.invalid` examples, certificate paths, users, and installation paths.

## Environment

| Variable | Default | Purpose |
| --- | --- | --- |
| `LANTERN_BIND_HOST` | `127.0.0.1` | Listen address |
| `LANTERN_PORT` | `8769` | Listen port |
| `LANTERN_ACCESS_TOKEN` | ephemeral on loopback | At least 24 characters; explicit off-loopback |
| `LANTERN_ALLOWED_HOSTS` | safe local values | Comma-separated exact browser hosts |
| `LANTERN_DEMO` | `0` | `1` returns synthetic messages only |
| `LANTERN_ALLOW_PRIVATE_HTTP` | `0` | Explicit isolated-LAN exception; public access still requires HTTPS |

## Production check

```bash
curl -fsS http://127.0.0.1:8769/health
```

Verify that only HTTPS is public, HTTP redirects to HTTPS, the proxy never logs request bodies or Authorization, the Host allowlist is exact, the token is unique and random, the service user is unprivileged, and outbound TCP 993 is available.

## Upgrade, backup, and restore

The application has no mailbox database: iCloud addresses, app-specific passwords, messages, and codes exist only for one bounded request; the browser persists only the theme. There is no business data to back up. Preserve only systemd/Compose, proxy, and secret configuration through encrypted infrastructure tooling, never inside source archives.

Keep the previous source/image, test the candidate on another loopback port, check `/health`, then use demo mode and a dedicated low-risk mailbox before switching. Rollback restores the paired old code/image and configuration. If an access token or iCloud app-specific password was exposed, revoke and regenerate it; restoring files does not undo disclosure.

## Uninstall and troubleshooting

- Stop/disable the unit or run `docker compose down`, then remove the environment/image and secrets.
- Clearing browser site data removes only the theme; there is no recoverable local mail history.
- For `401`, re-enter the access token. The page deliberately does not persist it.
- For Host/Origin rejection, correct the exact allowlist and forwarded Host; keep the validation enabled.
- For IMAP login failure, verify the iCloud app-specific password, account state, and outbound TCP 993 without logging credentials.
- For missing codes, verify time range, target mailbox, and selected folders; heuristic extraction still requires human confirmation.
- Reproduce remote failures through the SSH tunnel first. Never troubleshoot by exposing the bind address or disabling HTTPS/authentication.
