"""Session state helpers: settings, engine lifecycle and recent results."""

from __future__ import annotations

import streamlit as st

from copytrader.config import Settings
from copytrader.engine import CopyEngine
from copytrader.models import CopyResult

MAX_RECENT_RESULTS = 50


def init_state() -> None:
    """Initialise the session state once per browser session."""
    if "settings" not in st.session_state:
        st.session_state.settings = Settings.from_env()
    st.session_state.setdefault("engine", None)
    st.session_state.setdefault("engine_errors", [])
    st.session_state.setdefault("last_poll", None)
    st.session_state.setdefault("recent_results", [])
    st.session_state.setdefault("activity_page", 1)


def get_settings() -> Settings:
    return st.session_state.settings


def update_settings(**changes) -> None:
    st.session_state.settings = get_settings().with_updates(**changes)


def get_engine() -> CopyEngine | None:
    return st.session_state.engine


def is_running() -> bool:
    return get_engine() is not None


def start_engine() -> None:
    settings = get_settings()
    errors = settings.validate()
    st.session_state.engine_errors = errors
    if errors:
        return
    st.session_state.engine = CopyEngine.from_settings(settings)
    st.session_state.last_poll = None


def stop_engine() -> None:
    st.session_state.engine = None
    st.session_state.engine_errors = []


def add_results(results: list[CopyResult]) -> None:
    recent = results[::-1] + st.session_state.recent_results
    st.session_state.recent_results = recent[:MAX_RECENT_RESULTS]
