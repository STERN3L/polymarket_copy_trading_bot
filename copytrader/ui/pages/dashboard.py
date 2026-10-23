"""Dashboard page: your portfolio and the journal of copied trades."""

from __future__ import annotations

import contextlib

import plotly.express as px
import streamlit as st

from copytrader.api.data_api import DataApiError
from copytrader.config import is_valid_address
from copytrader.ui import data, state
from copytrader.ui.styles import style_action, style_outcome, style_pnl, style_status


def render() -> None:
    settings = state.get_settings()
    journal = data.load_journal(settings.journal_path)

    st.header("📊 Dashboard")
    _render_metrics(settings.funder_address, journal)
    st.divider()

    st.subheader("Copied trades")
    if journal.empty:
        st.info("No trade has been copied yet. Start the engine to begin mirroring the target wallet.")
    else:
        _render_volume_chart(journal)
        _render_journal(journal)

    st.divider()
    st.subheader("Open positions")
    _render_positions(settings.funder_address)


def _render_metrics(wallet: str, journal) -> None:
    portfolio_value = None
    if is_valid_address(wallet):
        with contextlib.suppress(DataApiError):
            portfolio_value = data.load_portfolio_value(wallet)

    copied = journal[journal["status"].isin(["EXECUTED", "SIMULATED"])] if not journal.empty else journal
    failed = int((journal["status"] == "FAILED").sum()) if not journal.empty else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Positions value", f"{portfolio_value:,.2f} $" if portfolio_value is not None else "—", border=True)
    col2.metric("Trades copied", len(copied), border=True)
    col3.metric("Copied volume", f"{copied['copy_usdc'].sum():,.2f} $" if not copied.empty else "0.00 $", border=True)
    col4.metric("Failed orders", failed, border=True)


def _render_volume_chart(journal) -> None:
    copied = journal[journal["status"].isin(["EXECUTED", "SIMULATED"])].sort_values("processed_at")
    if copied.empty:
        return
    copied = copied.assign(cumulative=copied["copy_usdc"].cumsum())
    fig = px.line(copied, x="processed_at", y="cumulative", markers=True, title="Cumulative copied volume (USDC)")
    fig.update_layout(xaxis_title=None, yaxis_title="USDC", margin=dict(t=50, b=20, l=20, r=20))
    st.plotly_chart(fig)


def _render_journal(journal) -> None:
    table = journal.rename(
        columns={
            "processed_at": "Time",
            "status": "Status",
            "market": "Market",
            "outcome": "Outcome",
            "side": "Action",
            "target_usdc": "Target (USDC)",
            "copy_price": "Price",
            "copy_size": "Shares",
            "copy_usdc": "Copied (USDC)",
            "message": "Details",
        }
    )[["Time", "Status", "Action", "Market", "Outcome", "Target (USDC)", "Price", "Shares", "Copied (USDC)", "Details"]]

    styled = (
        table.style.map(style_status, subset=["Status"])
        .map(style_action, subset=["Action"])
        .map(style_outcome, subset=["Outcome"])
        .format(
            {
                "Time": lambda t: t.strftime("%Y-%m-%d %H:%M:%S"),
                "Target (USDC)": "{:.2f} $",
                "Price": "{:.2f}",
                "Shares": "{:.2f}",
                "Copied (USDC)": "{:.2f} $",
            },
            na_rep="—",
        )
    )
    st.dataframe(styled, hide_index=True, height=400)


def _render_positions(wallet: str) -> None:
    if not is_valid_address(wallet):
        st.info("Set your Polymarket wallet address in **Settings** to see your positions.")
        return
    try:
        positions = data.load_positions(wallet)
    except DataApiError as exc:
        st.error(f"Could not load positions: {exc}")
        return
    if positions.empty:
        st.info("No open position.")
        return

    styled = positions.style.format(precision=2, na_rep="—")
    if "Outcome" in positions.columns:
        styled = styled.map(style_outcome, subset=["Outcome"])
    pnl_columns = [c for c in ("PnL (USDC)", "PnL (%)") if c in positions.columns]
    if pnl_columns:
        styled = styled.map(style_pnl, subset=pnl_columns)
    st.dataframe(styled, hide_index=True)
