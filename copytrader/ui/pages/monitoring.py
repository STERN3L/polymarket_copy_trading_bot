"""Target wallet page: live activity feed (BUY, SELL, REDEEM, ...) of the copied wallet."""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from copytrader.api.data_api import DataApiError
from copytrader.config import is_valid_address
from copytrader.ui import data, state
from copytrader.ui.styles import style_action, style_outcome

PAGE_SIZE = 25


def render() -> None:
    settings = state.get_settings()
    st.header("👀 Target wallet")

    wallet = settings.target_wallet
    if not is_valid_address(wallet):
        st.error("Set the wallet to copy in **Settings** first.")
        return

    st.markdown(f"Activity of [`{wallet}`](https://polymarket.com/profile/{wallet})")
    st.fragment(run_every=settings.poll_interval_seconds)(_activity_feed)(wallet, settings.poll_interval_seconds)


def _activity_feed(wallet: str, refresh_seconds: int) -> None:
    """Activity table, refreshed automatically every `refresh_seconds`."""
    page = st.session_state.activity_page
    st.caption(f"🔄 Auto-refresh every {refresh_seconds}s · last update {datetime.now():%H:%M:%S}")

    try:
        activity = data.load_activity(wallet, page, PAGE_SIZE)
    except DataApiError as exc:
        st.error(f"Could not load activity: {exc}")
        return

    if activity.empty:
        st.warning("No activity found for this page.")
    else:
        styled = (
            activity.style.map(style_action, subset=["Action"])
            .map(style_outcome, subset=["Outcome"])
            .format(
                {
                    "Time": lambda t: t.strftime("%Y-%m-%d %H:%M:%S"),
                    "Price": "{:.3f} $",
                    "Shares": "{:.2f}",
                    "Amount (USDC)": "{:.2f} $",
                },
                na_rep="—",
            )
        )
        st.dataframe(styled, hide_index=True, height=35 * (len(activity) + 1) + 3)

    # The Data API does not return a total count: a full page means there may be a next one.
    col_prev, col_info, col_next = st.columns([1, 4, 1])
    with col_prev:
        if st.button("⬅️ Previous", disabled=page <= 1, width="stretch"):
            st.session_state.activity_page -= 1
            st.rerun(scope="fragment")
    with col_info:
        st.markdown(f"<div style='text-align:center'>Page <b>{page}</b></div>", unsafe_allow_html=True)
    with col_next:
        if st.button("Next ➡️", disabled=len(activity) < PAGE_SIZE, width="stretch"):
            st.session_state.activity_page += 1
            st.rerun(scope="fragment")
