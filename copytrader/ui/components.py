"""Reusable UI blocks: header with engine controls and the background polling loop."""

from __future__ import annotations

from datetime import datetime, timedelta

import streamlit as st

from copytrader.api.data_api import DataApiError
from copytrader.models import CopyStatus
from copytrader.ui import state

_TOAST_ICONS = {
    CopyStatus.EXECUTED: "✅",
    CopyStatus.SIMULATED: "🧪",
    CopyStatus.SKIPPED: "⏭️",
    CopyStatus.FAILED: "❌",
}


def short_address(address: str) -> str:
    return f"{address[:6]}…{address[-4:]}" if len(address) > 12 else address or "not set"


def render_header() -> None:
    settings = state.get_settings()
    col_title, col_control = st.columns([5, 2], vertical_alignment="center")

    with col_title:
        st.title("🤖 Polymarket Copy Trader")

    with col_control:
        if state.is_running():
            st.button("Stop engine", icon="🛑", on_click=state.stop_engine, width="stretch")
        else:
            label = "Start engine (dry-run)" if settings.dry_run else "Start engine (LIVE)"
            st.button(label, icon="🚀", type="primary", on_click=state.start_engine, width="stretch")

    for error in st.session_state.engine_errors:
        st.error(error, icon="⚠️")

    interval = settings.poll_interval_seconds if state.is_running() else None
    st.fragment(run_every=interval)(_engine_cycle)()


def _engine_cycle() -> None:
    """Poll the target wallet when due, then display the engine status.

    Runs as a Streamlit fragment that re-executes every polling interval while
    the engine is running, without reloading the rest of the page.
    """
    engine = state.get_engine()
    if engine is None:
        st.info("Copy engine stopped. Configure the bot in **Settings**, then start the engine.", icon="🛑")
        return

    settings = engine.settings
    now = datetime.now()
    last_poll = st.session_state.last_poll
    if last_poll is None or now - last_poll >= timedelta(seconds=settings.poll_interval_seconds - 1):
        st.session_state.last_poll = now
        try:
            results = engine.poll()
        except DataApiError as exc:
            st.warning(f"Could not reach the Polymarket Data API, retrying next cycle: {exc}", icon="📡")
            results = []
        state.add_results(results)
        for result in results:
            st.toast(
                f"{result.status.value}: {result.source.title} — {result.message}",
                icon=_TOAST_ICONS[result.status],
            )

    mode = "🧪 DRY-RUN" if settings.dry_run else "🔴 LIVE"
    st.success(
        f"**{mode}** · Watching `{short_address(settings.target_wallet)}` at **{settings.copy_ratio_percent:g}%** · "
        f"last check {st.session_state.last_poll:%H:%M:%S} · every {settings.poll_interval_seconds}s",
        icon="✅",
    )
