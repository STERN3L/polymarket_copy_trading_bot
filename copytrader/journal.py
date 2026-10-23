"""Append-only CSV journal of every trade processed by the copy engine."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

from copytrader.models import CopyResult

FIELDS = [
    "processed_at",
    "status",
    "market",
    "outcome",
    "side",
    "target_price",
    "target_usdc",
    "copy_price",
    "copy_size",
    "copy_usdc",
    "order_id",
    "transaction_hash",
    "message",
]


class TradeJournal:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def record(self, result: CopyResult) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        is_new = not self.path.exists()
        order = result.order
        row = {
            "processed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "status": result.status.value,
            "market": result.source.title,
            "outcome": result.source.outcome,
            "side": result.source.side,
            "target_price": result.source.price,
            "target_usdc": round(result.source.usdc_size, 2),
            "copy_price": order.price if order else "",
            "copy_size": order.size if order else "",
            "copy_usdc": order.usdc_amount if order else "",
            "order_id": result.order_id,
            "transaction_hash": result.source.transaction_hash,
            "message": result.message,
        }
        with self.path.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            if is_new:
                writer.writeheader()
            writer.writerow(row)

    def read_rows(self) -> list[dict[str, str]]:
        if not self.path.exists():
            return []
        with self.path.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))
