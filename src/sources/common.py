"""Utilidades compartidas por todos los colectores.

Principio: ninguna fuente puede tumbar el pipeline. Un fallo se registra
en ERRORS, se reporta al final de la corrida y aparece en el dashboard.
"""
from __future__ import annotations

import functools
import time

TIMEOUT = 25
HEADERS = {
    "User-Agent": "market-radar/2.0 (uso personal de investigación)",
    "Accept": "*/*",
}

ERRORS: list[dict] = []


def log_error(source: str, exc: object) -> None:
    ERRORS.append({"source": source, "error": f"{type(exc).__name__}: {exc}"
                   if isinstance(exc, Exception) else str(exc)})


def clear_errors() -> None:
    ERRORS.clear()


def retry(times: int = 2, wait: float = 1.5):
    """Reintenta una función ante fallos de red transitorios."""
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*a, **kw):
            last = None
            for attempt in range(times + 1):
                try:
                    return fn(*a, **kw)
                except Exception as exc:  # noqa: BLE001
                    last = exc
                    if attempt < times:
                        time.sleep(wait * (attempt + 1))
            raise last  # type: ignore[misc]
        return wrapper
    return deco


def strip_html(text: str) -> str:
    import re
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text or "")).strip()
