"""High-level client for the ESPNCricinfo hidden JSON API.

The actual HTTP call is dispatched through :mod:`cricscore._native` so a
future Rust extension can transparently take over network + parsing without
any caller changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cricscore import _native
from cricscore.api._python_client import ScorecardFetchError
from cricscore.url_parser import MatchRef

__all__ = ["ESPNCricinfoClient", "ScorecardFetchError"]


@dataclass(frozen=True, slots=True)
class ESPNCricinfoClient:
    """Thin facade around the scorecard fetcher.

    Stateless today — kept as a class so we can later add session reuse,
    caching, retries, and an injected transport without breaking callers.
    """

    timeout: float = 15.0

    @property
    def backend(self) -> str:
        """Either ``"python"`` or ``"rust"`` depending on what's installed."""
        return _native.BACKEND

    def fetch_scorecard(self, match_ref: MatchRef) -> dict[str, Any]:
        """Fetch the raw scorecard JSON for the given match."""
        return _native.fetch_raw_scorecard(
            match_ref.series_id, match_ref.match_id, self.timeout
        )
