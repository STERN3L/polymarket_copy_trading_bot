"""Domain models shared by the API layer, the copy engine and the UI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class CopyStatus(str, Enum):
    EXECUTED = "EXECUTED"
    SIMULATED = "SIMULATED"
    SKIPPED = "SKIPPED"
    FAILED = "FAILED"


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class Activity:
    """A single on-chain activity of a wallet, as returned by the Polymarket Data API."""

    transaction_hash: str
    timestamp: datetime
    type: str
    side: str
    asset: str
    title: str
    outcome: str
    price: float
    size: float
    usdc_size: float

    @classmethod
    def from_api(cls, raw: dict[str, Any]) -> Activity:
        return cls(
            transaction_hash=str(raw.get("transactionHash") or ""),
            timestamp=datetime.fromtimestamp(int(raw.get("timestamp") or 0), tz=timezone.utc),
            type=str(raw.get("type") or "").upper(),
            side=str(raw.get("side") or "").upper(),
            asset=str(raw.get("asset") or ""),
            title=str(raw.get("title") or ""),
            outcome=str(raw.get("outcome") or ""),
            price=_to_float(raw.get("price")),
            size=_to_float(raw.get("size")),
            usdc_size=_to_float(raw.get("usdcSize")),
        )

    @property
    def is_trade(self) -> bool:
        return self.type == "TRADE"

    @property
    def key(self) -> tuple[str, str, str, float]:
        """Unique identity of the activity (one transaction can contain several fills)."""
        return (self.transaction_hash, self.asset, self.side, self.size)


@dataclass(frozen=True)
class CopyOrder:
    """An order sized and priced to mirror a target trade."""

    token_id: str
    side: str
    price: float
    size: float

    @property
    def usdc_amount(self) -> float:
        return round(self.price * self.size, 2)


@dataclass(frozen=True)
class CopyResult:
    """Outcome of processing a single target trade."""

    source: Activity
    status: CopyStatus
    message: str
    order: CopyOrder | None = None
    order_id: str = ""
