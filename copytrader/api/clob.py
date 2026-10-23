"""Order execution through the Polymarket CLOB (requires a private key)."""

from __future__ import annotations

from typing import Protocol

from copytrader.config import CLOB_HOST
from copytrader.models import CopyOrder


class OrderExecutor(Protocol):
    """Anything able to place a `CopyOrder` and return an order identifier."""

    dry_run: bool

    def place(self, order: CopyOrder) -> str: ...


class DryRunExecutor:
    """Executor that never sends anything: used for paper trading and tests."""

    dry_run = True

    def place(self, order: CopyOrder) -> str:
        return "dry-run"


class ClobExecutor:
    """Places GTC limit orders on the Polymarket CLOB using `py-clob-client`."""

    dry_run = False

    def __init__(
        self,
        private_key: str,
        funder_address: str,
        signature_type: int = 2,
        host: str = CLOB_HOST,
    ) -> None:
        self._private_key = private_key
        self._funder_address = funder_address
        self._signature_type = signature_type
        self._host = host
        self._client = None

    def _get_client(self):
        if self._client is None:
            # Imported lazily so that dry-run mode and tests do not require the CLOB SDK.
            from py_clob_client.client import ClobClient
            from py_clob_client.constants import POLYGON

            client = ClobClient(
                self._host,
                key=self._private_key,
                chain_id=POLYGON,
                signature_type=self._signature_type,
                funder=self._funder_address,
            )
            client.set_api_creds(client.create_or_derive_api_creds())
            self._client = client
        return self._client

    def place(self, order: CopyOrder) -> str:
        from py_clob_client.clob_types import OrderArgs, OrderType

        client = self._get_client()
        signed = client.create_order(
            OrderArgs(token_id=order.token_id, price=order.price, size=order.size, side=order.side)
        )
        response = client.post_order(signed, OrderType.GTC) or {}
        if response.get("success") is False or response.get("errorMsg"):
            raise RuntimeError(response.get("errorMsg") or f"Order rejected: {response}")
        return str(response.get("orderID", ""))
