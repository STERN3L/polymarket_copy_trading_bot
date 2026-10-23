from copytrader.models import Activity
from copytrader.sizing import SizingParams, build_copy_order

PARAMS = SizingParams(ratio_percent=10, min_order_usdc=1, max_order_usdc=50, max_slippage_percent=2)


def test_buy_order_applies_ratio_and_slippage(trade_factory):
    order, _ = build_copy_order(Activity.from_api(trade_factory(side="BUY", price=0.5, usdc=100)), PARAMS)
    assert order.side == "BUY"
    assert order.price == 0.51
    assert order.size == round(10 / 0.51, 2)


def test_sell_order_lowers_price(trade_factory):
    order, _ = build_copy_order(Activity.from_api(trade_factory(side="SELL", price=0.5, usdc=100)), PARAMS)
    assert order.price == 0.49


def test_order_is_capped_at_max(trade_factory):
    order, _ = build_copy_order(Activity.from_api(trade_factory(price=0.5, usdc=10_000)), PARAMS)
    assert order.usdc_amount <= 50


def test_order_below_minimum_is_skipped(trade_factory):
    order, reason = build_copy_order(Activity.from_api(trade_factory(usdc=5)), PARAMS)
    assert order is None
    assert "below the minimum" in reason


def test_price_is_clamped(trade_factory):
    order, _ = build_copy_order(Activity.from_api(trade_factory(side="BUY", price=0.985, usdc=100)), PARAMS)
    assert order.price == 0.99


def test_invalid_price_is_skipped(trade_factory):
    order, _ = build_copy_order(Activity.from_api(trade_factory(price=0)), PARAMS)
    assert order is None
