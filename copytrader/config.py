"""Application settings loaded from environment variables (and an optional `.env` file)."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field, replace
from pathlib import Path

from dotenv import load_dotenv

DATA_API_URL = "https://data-api.polymarket.com"
CLOB_HOST = "https://clob.polymarket.com"

_ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")

# Polymarket signature types: 0 = EOA, 1 = email/Magic proxy, 2 = browser wallet proxy (Gnosis Safe).
SIGNATURE_TYPES = (0, 1, 2)


def is_valid_address(value: str | None) -> bool:
    """Return True if `value` looks like an EVM address (0x + 40 hex characters)."""
    return bool(value and _ADDRESS_RE.match(value.strip()))


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"Environment variable {name} must be a number, got {raw!r}") from exc


def _env_int(name: str, default: int) -> int:
    return int(_env_float(name, default))


@dataclass(frozen=True)
class Settings:
    """Runtime configuration of the bot."""

    target_wallet: str = ""
    funder_address: str = ""
    private_key: str = field(default="", repr=False)
    signature_type: int = 2
    copy_ratio_percent: float = 10.0
    min_order_usdc: float = 1.0
    max_order_usdc: float = 100.0
    max_slippage_percent: float = 2.0
    poll_interval_seconds: int = 30
    dry_run: bool = True
    journal_path: Path = Path("data/copy_trades.csv")

    @classmethod
    def from_env(cls, env_file: str | os.PathLike | None = None) -> Settings:
        """Build settings from environment variables, loading `.env` first if present."""
        load_dotenv(env_file)
        return cls(
            target_wallet=os.getenv("TARGET_WALLET", "").strip(),
            funder_address=os.getenv("POLYMARKET_FUNDER_ADDRESS", "").strip(),
            private_key=os.getenv("POLYMARKET_PRIVATE_KEY", "").strip(),
            signature_type=_env_int("POLYMARKET_SIGNATURE_TYPE", 2),
            copy_ratio_percent=_env_float("COPY_RATIO_PERCENT", 10.0),
            min_order_usdc=_env_float("MIN_ORDER_USDC", 1.0),
            max_order_usdc=_env_float("MAX_ORDER_USDC", 100.0),
            max_slippage_percent=_env_float("MAX_SLIPPAGE_PERCENT", 2.0),
            poll_interval_seconds=_env_int("POLL_INTERVAL_SECONDS", 30),
            dry_run=_env_bool("DRY_RUN", True),
            journal_path=Path(os.getenv("JOURNAL_PATH", "data/copy_trades.csv")),
        )

    def with_updates(self, **changes) -> Settings:
        """Return a copy of the settings with the given fields replaced."""
        return replace(self, **changes)

    @property
    def has_private_key(self) -> bool:
        return bool(self.private_key)

    def validate(self) -> list[str]:
        """Return a list of human-readable configuration errors (empty if valid)."""
        errors = []
        if not is_valid_address(self.target_wallet):
            errors.append("TARGET_WALLET must be a valid 0x address.")
        if not 0 < self.copy_ratio_percent <= 1000:
            errors.append("COPY_RATIO_PERCENT must be in (0, 1000].")
        if self.min_order_usdc < 0 or self.max_order_usdc <= 0:
            errors.append("MIN_ORDER_USDC must be >= 0 and MAX_ORDER_USDC must be > 0.")
        elif self.min_order_usdc > self.max_order_usdc:
            errors.append("MIN_ORDER_USDC cannot be greater than MAX_ORDER_USDC.")
        if not 0 <= self.max_slippage_percent < 100:
            errors.append("MAX_SLIPPAGE_PERCENT must be in [0, 100).")
        if self.poll_interval_seconds < 5:
            errors.append("POLL_INTERVAL_SECONDS must be at least 5 seconds.")
        if not self.dry_run:
            if not self.has_private_key:
                errors.append("POLYMARKET_PRIVATE_KEY is required when DRY_RUN is disabled.")
            if not is_valid_address(self.funder_address):
                errors.append("POLYMARKET_FUNDER_ADDRESS must be a valid 0x address when DRY_RUN is disabled.")
            if self.signature_type not in SIGNATURE_TYPES:
                errors.append("POLYMARKET_SIGNATURE_TYPE must be 0, 1 or 2.")
        return errors
