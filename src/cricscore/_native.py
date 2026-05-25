"""Native-acceleration shim.

This module is the **single contract** between CricScore's Python code and any
future native (Rust) acceleration. Every operation that is a plausible
candidate for being rewritten in Rust later is routed through this module so
the rest of the codebase never needs to know which implementation is running.

Pattern 1 from the project plan: a Rust extension module built with PyO3 +
maturin under ``rust/`` (does not exist yet) will be packaged as
``cricscore._native_rs``. If importable, it transparently replaces the
Python fallbacks below.

Migration path at Phase 6
-------------------------
1.  ``mkdir rust && cd rust && maturin init --bindings pyo3``.
2.  Set ``module-name = "cricscore._native_rs"`` in ``rust/pyproject.toml``.
3.  Implement the functions listed in :data:`PUBLIC_API` with matching
    signatures and JSON-compatible return types.
4.  ``maturin develop --release`` inside the venv installs the extension,
    after which :data:`BACKEND` will report ``"rust"`` automatically.
5.  No callers need to change. This module already routes them.

Functions exposed here must accept and return plain JSON-compatible Python
values (``dict``, ``list``, ``str``, ``int``, ``float``, ``bool``, ``None``)
so the Rust/Python boundary stays cheap and bindings-free for callers.
"""

from __future__ import annotations

from typing import Any

try:  # pragma: no cover - import-time branch
    from cricscore import _native_rs as _impl  # type: ignore[attr-defined]

    BACKEND: str = "rust"
except ImportError:  # pragma: no cover - fallback path is exercised by tests
    _impl = None
    BACKEND = "python"


#: Public functions the native module is expected to provide. Keep this list
#: in lockstep with the Python fallbacks defined below.
PUBLIC_API: tuple[str, ...] = (
    "fetch_raw_scorecard",
)


def fetch_raw_scorecard(series_id: int, match_id: int, timeout: float = 15.0) -> dict[str, Any]:
    """Fetch the raw ESPNCricinfo scorecard JSON for a match.

    Routes to the Rust implementation if available, otherwise calls the
    pure-Python curl_cffi-based fallback.
    """
    if _impl is not None and hasattr(_impl, "fetch_raw_scorecard"):
        return _impl.fetch_raw_scorecard(series_id, match_id, timeout)  # type: ignore[no-any-return]

    # Local import keeps optional native consumers from pulling curl_cffi.
    from cricscore.api._python_client import python_fetch_raw_scorecard

    return python_fetch_raw_scorecard(series_id, match_id, timeout)
