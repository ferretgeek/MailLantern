# Privacy boundary / 隐私边界

Mail Lantern is designed for one trusted user on one trusted device or private server. It has no database, analytics, telemetry, ad SDK, third-party frontend asset, account system, or cloud relay.

## Processed briefly

- iCloud email and optional target recipient;
- app-specific password;
- the bounded set of recent MIME messages fetched from `INBOX`;
- extracted verification code, subject, timestamp, and masked sender/recipient.

These values exist only while the request and result page are alive. The server does not persist them. The browser persists only the selected visual theme. Clearing the page removes in-memory results; closing the process removes the generated access token.

## Never requested

- Apple Account login password or 2FA code;
- cookies, sessions, recovery codes, trust tokens, or private API credentials;
- a batch account list, local credential file, or identity-registration material.

## Network destinations

Application code fixes mailbox traffic to `imap.mail.me.com:993`. The interface makes same-origin requests only. Documentation links may navigate to Apple Support or GitHub only after the user activates them.

## Safe operation

- Create a dedicated app-specific password and revoke it from Apple Account settings when it is no longer needed.
- Run locally when possible. For a server, use a host you control, HTTPS, a strong unique access token, and an exact Host allowlist.
- Avoid reverse-proxy request-body logging. Do not share browser screenshots containing real codes or addresses.
- Treat a verification code as sensitive even though sender and recipient identities are masked.

## Public fixtures

Tests, screenshots, examples, and demo mode use reserved `.invalid` domains and synthetic codes. No real address, password, account, host, IP, path, or mailbox content belongs in this repository.

For a vulnerability, follow [`SECURITY.md`](../SECURITY.md) and do not place sensitive evidence in a public issue.
