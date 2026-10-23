"""Settings page: wallets, copy sizing and risk limits."""

from __future__ import annotations

import streamlit as st

from copytrader.config import is_valid_address
from copytrader.ui import state

SIGNATURE_TYPE_LABELS = {
    0: "0 · EOA (private key wallet used directly)",
    1: "1 · Email / Magic login (Polymarket proxy)",
    2: "2 · Browser wallet, e.g. MetaMask (Polymarket proxy)",
}


def render() -> None:
    settings = state.get_settings()
    running = state.is_running()

    st.header("⚙️ Settings")
    st.caption(
        "Values are pre-filled from your `.env` file. Changes made here only last for the current "
        "browser session; edit `.env` to make them permanent."
    )
    if running:
        st.warning("Stop the copy engine to edit the settings.", icon="🔒")

    with st.form("settings_form", border=True):
        st.subheader("Wallets")
        target_wallet = st.text_input(
            "Wallet to copy",
            value=settings.target_wallet,
            placeholder="0x…",
            help="Polymarket address (proxy wallet) of the trader you want to mirror.",
            disabled=running,
        )
        funder_address = st.text_input(
            "Your Polymarket wallet",
            value=settings.funder_address,
            placeholder="0x…",
            help="The address shown on your Polymarket profile, which holds your USDC.",
            disabled=running,
        )
        signature_type = st.selectbox(
            "Signature type",
            options=list(SIGNATURE_TYPE_LABELS),
            index=list(SIGNATURE_TYPE_LABELS).index(settings.signature_type)
            if settings.signature_type in SIGNATURE_TYPE_LABELS
            else 2,
            format_func=SIGNATURE_TYPE_LABELS.get,
            disabled=running,
        )

        st.subheader("Copy sizing")
        st.latex(
            r"\text{Your order} = \min\left(\text{Target order} \times \frac{\text{Ratio}}{100},"
            r"\ \text{Max order}\right)"
        )
        col1, col2 = st.columns(2)
        ratio = col1.number_input(
            "Copy ratio (%)",
            min_value=0.1,
            max_value=1000.0,
            value=float(settings.copy_ratio_percent),
            step=0.5,
            format="%.2f",
            disabled=running,
        )
        slippage = col2.number_input(
            "Max slippage (%)",
            min_value=0.0,
            max_value=50.0,
            value=float(settings.max_slippage_percent),
            step=0.5,
            help="Your limit price is the target's price plus (buy) or minus (sell) this tolerance.",
            disabled=running,
        )
        col3, col4, col5 = st.columns(3)
        min_order = col3.number_input(
            "Min order (USDC)",
            min_value=0.0,
            value=float(settings.min_order_usdc),
            step=1.0,
            help="Smaller copies are skipped.",
            disabled=running,
        )
        max_order = col4.number_input(
            "Max order (USDC)",
            min_value=0.01,
            value=float(settings.max_order_usdc),
            step=10.0,
            help="Larger copies are capped to this amount.",
            disabled=running,
        )
        poll_interval = col5.number_input(
            "Polling interval (s)",
            min_value=5,
            max_value=3600,
            value=int(settings.poll_interval_seconds),
            step=5,
            disabled=running,
        )

        st.subheader("Execution mode")
        dry_run = st.toggle(
            "Dry-run (simulate orders, nothing is sent)",
            value=settings.dry_run,
            disabled=running,
        )
        if settings.has_private_key:
            st.success("Private key loaded from the environment (`POLYMARKET_PRIVATE_KEY`).", icon="🔑")
        else:
            st.info(
                "No private key loaded. Set `POLYMARKET_PRIVATE_KEY` in `.env` to enable live trading. "
                "The key is never entered or displayed in the web interface.",
                icon="🔑",
            )

        if st.form_submit_button("Save settings", icon="💾", type="primary", disabled=running):
            state.update_settings(
                target_wallet=target_wallet.strip(),
                funder_address=funder_address.strip(),
                signature_type=signature_type,
                copy_ratio_percent=ratio,
                max_slippage_percent=slippage,
                min_order_usdc=min_order,
                max_order_usdc=max_order,
                poll_interval_seconds=int(poll_interval),
                dry_run=dry_run,
            )
            st.session_state.activity_page = 1
            errors = state.get_settings().validate()
            if errors:
                for error in errors:
                    st.error(error)
            else:
                st.toast("Settings saved.", icon="💾")

    _render_example(state.get_settings())


def _render_example(settings) -> None:
    target = 1000.0
    copy = min(target * settings.copy_ratio_percent / 100, settings.max_order_usdc)
    verdict = "skipped (below minimum)" if copy < settings.min_order_usdc else f"**{copy:,.2f} USDC**"
    wallet_ok = "✅" if is_valid_address(settings.target_wallet) else "❌"
    st.info(
        f"Example: when the target places a {target:,.0f} USDC order, your copy is {verdict}.  \n"
        f"Target wallet configured: {wallet_ok}"
    )
