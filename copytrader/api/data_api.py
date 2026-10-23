"""Read-only client for the public Polymarket Data API (no authentication required)."""

from __future__ import annotations

from typing import Any

import requests

from copytrader.config import DATA_API_URL


class DataApiError(RuntimeError):
    """Raised when the Data API cannot be reached or returns an invalid response."""


class DataApiClient:
    def __init__(
        self,
        base_url: str = DATA_API_URL,
        timeout: float = 10.0,
        session: requests.Session | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()

    def _get(self, path: str, params: dict[str, Any]) -> Any:
        url = f"{self.base_url}{path}"
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            raise DataApiError(f"GET {path} failed: {exc}") from exc

    def get_activity(
        self,
        user: str,
        limit: int = 100,
        offset: int = 0,
        activity_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return the wallet's activity, most recent first."""
        params: dict[str, Any] = {
            "user": user,
            "limit": limit,
            "offset": offset,
            "sortBy": "TIMESTAMP",
            "sortDirection": "DESC",
        }
        if activity_type:
            params["type"] = activity_type
        return self._get("/activity", params) or []

    def get_positions(self, user: str, limit: int = 500) -> list[dict[str, Any]]:
        """Return the wallet's current positions."""
        return self._get("/positions", {"user": user, "limit": limit, "sizeThreshold": 0}) or []

    def get_portfolio_value(self, user: str) -> float:
        """Return the total current value (USDC) of the wallet's positions."""
        data = self._get("/value", {"user": user})
        if isinstance(data, list) and data:
            return float(data[0].get("value") or 0.0)
        return 0.0
