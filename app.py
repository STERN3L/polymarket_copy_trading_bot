"""Streamlit entry point: `streamlit run app.py`."""

import streamlit as st

from copytrader import __version__
from copytrader.ui import state
from copytrader.ui.components import render_header, short_address
from copytrader.ui.pages import dashboard, monitoring, settings

st.set_page_config(page_title="Polymarket Copy Trader", page_icon="🤖", layout="wide")


def main() -> None:
    state.init_state()

    page = st.navigation(
        [
            st.Page(dashboard.render, title="Dashboard", icon="📊", url_path="dashboard", default=True),
            st.Page(monitoring.render, title="Target wallet", icon="👀", url_path="target"),
            st.Page(settings.render, title="Settings", icon="⚙️", url_path="settings"),
        ]
    )

    current = state.get_settings()
    st.sidebar.caption(f"Target: `{short_address(current.target_wallet)}`")
    st.sidebar.caption(f"Mode: {'dry-run' if current.dry_run else 'LIVE'}")
    st.sidebar.caption(f"v{__version__} · Built with Streamlit")

    render_header()
    page.run()


main()
