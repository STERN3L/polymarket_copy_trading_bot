"""Cached data loaders that turn API responses into display-ready DataFrames."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from copytrader.api.data_api import DataApiClient
from copytrader.journal import TradeJournal

CACHE_TTL_SECONDS = 15

_client = DataApiClient()


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def load_activity(wallet: str, page: int, page_size: int) -> pd.DataFrame:
    """Return one page of the wallet's activity (all types), most recent first."""
    raw = _client.get_activity(wallet, limit=page_size, offset=(page - 1) * page_size)
    if not raw:
        return pd.DataFrame()

    df = pd.DataFrame(raw)
    for column in ("timestamp", "type", "side", "title", "outcome", "price", "size", "usdcSize"):
        if column not in df.columns:
            df[column] = None

    # Trades are labelled by their side (BUY/SELL), other activities by their type (REDEEM, SPLIT, ...).
    action = df["side"].where(df["type"] == "TRADE", df["type"]).fillna(df["type"])
    return pd.DataFrame(
        {
            "Time": pd.to_datetime(df["timestamp"], unit="s", utc=True),
            "Action": action.str.upper(),
            "Market": df["title"],
            "Outcome": df["outcome"],
            "Price": pd.to_numeric(df["price"], errors="coerce"),
            "Shares": pd.to_numeric(df["size"], errors="coerce"),
            "Amount (USDC)": pd.to_numeric(df["usdcSize"], errors="coerce"),
        }
    )


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def load_positions(wallet: str) -> pd.DataFrame:
    """Return the wallet's open positions."""
    raw = _client.get_positions(wallet)
    if not raw:
        return pd.DataFrame()

    df = pd.DataFrame(raw)
    columns = {
        "title": "Market",
        "outcome": "Outcome",
        "size": "Shares",
        "avgPrice": "Avg price",
        "curPrice": "Current price",
        "initialValue": "Cost (USDC)",
        "currentValue": "Value (USDC)",
        "cashPnl": "PnL (USDC)",
        "percentPnl": "PnL (%)",
    }
    df = df[[c for c in columns if c in df.columns]].rename(columns=columns)
    if "Value (USDC)" in df.columns:
        df = df.sort_values("Value (USDC)", ascending=False)
    return df


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def load_portfolio_value(wallet: str) -> float:
    return _client.get_portfolio_value(wallet)


def load_journal(path: Path) -> pd.DataFrame:
    """Return the copy journal, most recent first (not cached: it changes on every copy)."""
    rows = TradeJournal(path).read_rows()
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["processed_at"] = pd.to_datetime(df["processed_at"], utc=True)
    for column in ("target_price", "target_usdc", "copy_price", "copy_size", "copy_usdc"):
        df[column] = pd.to_numeric(df[column], errors="coerce")
    return df.sort_values("processed_at", ascending=False)
