"""Copy trading engine: detects new trades of the target wallet and mirrors them.

The engine has no dependency on Streamlit, so it is shared by the web dashboard
and the headless command-line runner.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from copytrader.api.clob import ClobExecutor, DryRunExecutor, OrderExecutor
from copytrader.api.data_api import DataApiClient
from copytrader.config import Settings
from copytrader.journal import TradeJournal
from copytrader.models import Activity, CopyResult, CopyStatus
from copytrader.sizing import SizingParams, build_copy_order

logger = logging.getLogger(__name__)

# Number of recent target trades fetched on each poll.
LOOKBACK = 50
# Trades older than this (relative to the engine start) are never copied.
STALE_AFTER = timedelta(minutes=5)


class CopyEngine:
    def __init__(
        self,
        settings: Settings,
        data_api: DataApiClient,
        executor: OrderExecutor,
        journal: TradeJournal | None = None,
    ) -> None:
        self.settings = settings
        self.data_api = data_api
        self.executor = executor
        self.journal = journal
        self.params = SizingParams(
            ratio_percent=settings.copy_ratio_percent,
            min_order_usdc=settings.min_order_usdc,
            max_order_usdc=settings.max_order_usdc,
            max_slippage_percent=settings.max_slippage_percent,
        )
        self._seen: set[tuple] = set()
        self._started_at: datetime | None = None

    @classmethod
    def from_settings(cls, settings: Settings) -> CopyEngine:
        """Build an engine with the executor matching the `dry_run` setting."""
        executor: OrderExecutor
        if settings.dry_run:
            executor = DryRunExecutor()
        else:
            executor = ClobExecutor(
                private_key=settings.private_key,
                funder_address=settings.funder_address,
                signature_type=settings.signature_type,
            )
        return cls(settings, DataApiClient(), executor, TradeJournal(settings.journal_path))

    @property
    def is_primed(self) -> bool:
        return self._started_at is not None

    def _fetch_trades(self) -> list[Activity]:
        raw = self.data_api.get_activity(self.settings.target_wallet, limit=LOOKBACK, activity_type="TRADE")
        return [Activity.from_api(item) for item in raw]

    def prime(self) -> None:
        """Mark the target's existing trades as seen so that only future trades are copied."""
        trades = self._fetch_trades()
        self._seen.update(trade.key for trade in trades)
        self._started_at = datetime.now(timezone.utc)
        logger.info("Engine primed with %d existing trades of %s", len(trades), self.settings.target_wallet)

    def poll(self) -> list[CopyResult]:
        """Check for new target trades and copy them. Primes the engine on the first call."""
        if not self.is_primed:
            self.prime()
            return []

        new_trades = [t for t in self._fetch_trades() if t.is_trade and t.key not in self._seen]
        results = []
        # The API returns the most recent trades first: replay them in chronological order.
        for trade in reversed(new_trades):
            self._seen.add(trade.key)
            if trade.timestamp < self._started_at - STALE_AFTER:
                logger.debug("Ignoring stale trade %s", trade.transaction_hash)
                continue
            results.append(self._copy(trade))
        return results

    def _copy(self, trade: Activity) -> CopyResult:
        order, reason = build_copy_order(trade, self.params)
        if order is None:
            result = CopyResult(trade, CopyStatus.SKIPPED, reason)
        else:
            try:
                order_id = self.executor.place(order)
                status = CopyStatus.SIMULATED if self.executor.dry_run else CopyStatus.EXECUTED
                result = CopyResult(
                    trade,
                    status,
                    f"{order.side} {order.size} shares @ {order.price} ({order.usdc_amount} USDC)",
                    order,
                    order_id,
                )
            except Exception as exc:  # noqa: BLE001 - any SDK/network error must not stop the engine
                logger.exception("Failed to copy trade %s", trade.transaction_hash)
                result = CopyResult(trade, CopyStatus.FAILED, str(exc), order)

        logger.info("[%s] %s | %s", result.status.value, trade.title, result.message)
        if self.journal is not None:
            self.journal.record(result)
        return result
