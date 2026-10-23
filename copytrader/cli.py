"""Headless runner: `python -m copytrader` polls and copies trades without the web UI."""

from __future__ import annotations

import argparse
import logging
import sys
import time

from copytrader import __version__
from copytrader.api.data_api import DataApiError
from copytrader.config import Settings
from copytrader.engine import CopyEngine


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="copytrader", description="Polymarket copy trading bot (headless mode).")
    parser.add_argument("--env-file", default=None, help="Path to a .env file (default: ./.env).")
    parser.add_argument("--target", help="Wallet to copy (overrides TARGET_WALLET).")
    parser.add_argument("--ratio", type=float, help="Copy ratio in percent (overrides COPY_RATIO_PERCENT).")
    parser.add_argument("--interval", type=int, help="Polling interval in seconds (overrides POLL_INTERVAL_SECONDS).")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--live", action="store_true", help="Send real orders (overrides DRY_RUN=true).")
    mode.add_argument("--dry-run", action="store_true", help="Simulate orders only (overrides DRY_RUN=false).")
    parser.add_argument("--once", action="store_true", help="Run a single polling cycle and exit.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser.parse_args(argv)


def build_settings(args: argparse.Namespace) -> Settings:
    settings = Settings.from_env(args.env_file)
    overrides = {}
    if args.target:
        overrides["target_wallet"] = args.target
    if args.ratio is not None:
        overrides["copy_ratio_percent"] = args.ratio
    if args.interval is not None:
        overrides["poll_interval_seconds"] = args.interval
    if args.live:
        overrides["dry_run"] = False
    elif args.dry_run:
        overrides["dry_run"] = True
    return settings.with_updates(**overrides)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )
    log = logging.getLogger("copytrader")

    settings = build_settings(args)
    errors = settings.validate()
    if errors:
        for error in errors:
            log.error(error)
        return 2

    log.info(
        "Copying %s at %.2f%% (%s mode, polling every %ss)",
        settings.target_wallet,
        settings.copy_ratio_percent,
        "DRY-RUN" if settings.dry_run else "LIVE",
        settings.poll_interval_seconds,
    )
    engine = CopyEngine.from_settings(settings)

    try:
        while True:
            try:
                engine.poll()
            except DataApiError as exc:
                log.warning("Polling failed, will retry: %s", exc)
            if args.once:
                return 0
            time.sleep(settings.poll_interval_seconds)
    except KeyboardInterrupt:
        log.info("Stopped by user.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
