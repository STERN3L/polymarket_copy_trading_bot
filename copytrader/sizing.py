"""Turn a target trade into a correctly sized and priced copy order."""

from __future__ import annotations

from dataclasses import dataclass

from copytrader.models import Activity, CopyOrder

MIN_PRICE = 0.01
MAX_PRICE = 0.99


@dataclass(frozen=True)
class SizingParams:
    ratio_percent: float
    min_order_usdc: float
    max_order_usdc: float
    max_slippage_percent: float


def build_copy_order(trade: Activity, params: SizingParams) -> tuple[CopyOrder | None, str]:
    """Return the order mirroring `trade`, or `(None, reason)` if it must be skipped.

    The USDC amount is `target amount * ratio`, capped at `max_order_usdc`. The limit price
    is the target's fill price shifted by the allowed slippage (up for buys, down for sells),
    so the copy still fills when the market moved slightly after the target's trade.
    """
    if trade.side not in ("BUY", "SELL"):
        return None, f"unsupported side {trade.side!r}"
    if not trade.asset:
        return None, "missing token id"
    if not 0 < trade.price < 1:
        return None, f"invalid price {trade.price}"

    usdc_amount = min(trade.usdc_size * params.ratio_percent / 100.0, params.max_order_usdc)
    if usdc_amount < params.min_order_usdc:
        return None, f"amount {usdc_amount:.2f} USDC is below the minimum of {params.min_order_usdc:.2f} USDC"

    slippage = params.max_slippage_percent / 100.0
    raw_price = trade.price * (1 + slippage) if trade.side == "BUY" else trade.price * (1 - slippage)
    price = round(min(max(raw_price, MIN_PRICE), MAX_PRICE), 2)

    size = round(usdc_amount / price, 2)
    if size <= 0:
        return None, "computed size is zero"

    return CopyOrder(token_id=trade.asset, side=trade.side, price=price, size=size), "ok"
