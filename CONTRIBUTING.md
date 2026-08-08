# Contributing

Small, focused pull requests are welcome.

1. Preserve the fixed official endpoint, read-only mailbox access, memory-only credential lifecycle, bounded scans, exact Host/Origin controls, and synthetic fixtures.
2. Keep Apple login passwords, 2FA, cookies, private APIs, mailbox writes, account automation, credential files, analytics, and external frontend assets out of scope.
3. Maintain all four global themes, the `#17191d` Graphite background, top-right controls, responsive layouts, and SVG/PNG/ICO favicons.
4. Run:

   ```bash
   python -m unittest discover -s tests -v
   ruff check .
   ruff format --check .
   bandit -r src -ll
   ```

5. Update Chinese and English docs together. Report security-sensitive findings through GitHub Private Vulnerability Reporting.
