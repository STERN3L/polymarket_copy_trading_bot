"""Colour helpers used to style tables."""

from __future__ import annotations

import pandas as pd

GREEN = "#28a745"
RED = "#dc3545"
BLUE = "#007bff"
ORANGE = "#fd7e14"
GREY = "#6c757d"

_ACTION_COLORS = {"BUY": GREEN, "SELL": RED, "REDEEM": BLUE}
_STATUS_COLORS = {"EXECUTED": GREEN, "SIMULATED": BLUE, "SKIPPED": GREY, "FAILED": RED}
_POSITIVE_OUTCOMES = {"UP", "YES", "LONG", "OVER"}


def _badge(color: str) -> str:
    return f"color: white; background-color: {color}; font-weight: bold; text-align: center;"


def style_action(value: object) -> str:
    return _badge(_ACTION_COLORS.get(str(value).upper(), GREY))


def style_status(value: object) -> str:
    return _badge(_STATUS_COLORS.get(str(value).upper(), GREY))


def style_outcome(value: object) -> str:
    if value is None or pd.isna(value) or str(value) == "":
        return f"color: {GREY};"
    color = GREEN if str(value).upper() in _POSITIVE_OUTCOMES else RED
    return f"color: {color}; font-weight: bold;"


def style_pnl(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return f"color: {GREEN if float(value) >= 0 else RED};"
