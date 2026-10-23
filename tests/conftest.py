import time

import pytest


def make_trade(tx="0xabc", side="BUY", price=0.5, usdc=100.0, size=None, ts=None, asset="123", type_="TRADE"):
    """Build a raw Data API activity item."""
    return {
        "transactionHash": tx,
        "timestamp": int(ts if ts is not None else time.time()),
        "type": type_,
        "side": side,
        "asset": asset,
        "title": "Will it rain tomorrow?",
        "outcome": "Yes",
        "price": price,
        "size": size if size is not None else (usdc / price if price else 0.0),
        "usdcSize": usdc,
    }


@pytest.fixture
def trade_factory():
    return make_trade
