# Security policy

## Supported versions

Security fixes are provided for the latest release on `main`.

## Reporting

Use GitHub **Private Vulnerability Reporting**. Never open a public issue containing an Apple Account email, app-specific password, verification code, real message, access token, server address, filesystem path, or private screenshot.

Include the affected version, deployment shape, a minimal reproduction using `.invalid` domains, and expected impact. Do not send working credentials; maintainers do not need them.

## Security baseline

- Prefer the loopback default and use an SSH tunnel or HTTPS reverse proxy remotely.
- Use a unique access token of at least 24 characters and exact `LANTERN_ALLOWED_HOSTS` values.
- Never use an Apple login password. Create a revocable app-specific password.
- Prevent proxy request-body and Authorization logging.
- Run as an unprivileged user and keep Python, the host CA store, and the reverse proxy patched.
- Treat codes and mailbox identities as sensitive even though the app does not persist them.

The full data and trust boundary is documented in [`docs/PRIVACY.md`](./docs/PRIVACY.md).
