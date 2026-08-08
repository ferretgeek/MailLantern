# Mail Lantern project rules

- Read the workspace root `README.md` and this file before changing the project.
- Preserve the product boundary: fixed `imap.mail.me.com:993`, verified TLS, read-only `INBOX`, bounded `BODY.PEEK[]` scans, and no persistent data layer.
- Never add Apple login passwords, 2FA, cookies, session/trust tokens, private APIs, mailbox writes, browser automation, account registration, alias generation, batch identities, credential files, telemetry, or external frontend assets.
- Credentials and browser access tokens remain memory-only. Only the visual theme may be persisted. Use reserved `.invalid` identities in tests, docs, screenshots, logs, and examples.
- Keep exact Host/Origin checks, safe generic errors, request/resource limits, top-right privacy/theme controls, four global themes, `#17191d` Graphite, responsive UI, and SVG/PNG/ICO favicons.
- Update Chinese and English docs together. Any public change also requires the workspace root README and profile repository to be checked and synchronized.
- Before release, run tests, Ruff, Bandit, pip-audit, detect-secrets, Gitleaks on tree and history, fresh-clone packaging checks, real browser QA, link/image checks, and GitHub online verification.
