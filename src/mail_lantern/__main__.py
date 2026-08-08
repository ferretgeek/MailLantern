from __future__ import annotations

import argparse
import secrets
import sys

from . import __version__
from .app import MailLanternServer
from .config import AppConfig, ConfigError


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mail-lantern", description="Mail Lantern local-first iCloud code finder"
    )
    parser.add_argument("command", nargs="?", choices=("serve", "token"), default="serve")
    parser.add_argument("--demo", action="store_true", help="show reserved synthetic messages")
    parser.add_argument("--version", action="version", version=__version__)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "token":
        print(secrets.token_urlsafe(36))
        return 0
    try:
        config = AppConfig.from_env(demo_override=True if args.demo else None)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    display_host = "127.0.0.1" if config.bind_host in {"0.0.0.0", "::"} else config.bind_host  # nosec B104
    fragment = f"#token={config.access_token}" if config.generated_access_token else ""
    print(f"Mail Lantern {__version__} — http://{display_host}:{config.port}/{fragment}")
    if config.generated_access_token:
        print("The generated access token exists only for this process and URL fragment.")
    try:
        MailLanternServer(config).serve_forever()
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
