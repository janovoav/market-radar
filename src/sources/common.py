"""Utilidades compartidas por todos los colectores.

Principio: ninguna fuente puede tumbar el pipeline. Un fallo se registra
en ERRORS, se reporta al final de la corrida y aparece en el dashboard.
"""
from __future__ import annotations

import functools
import time

TIMEOUT = 25
# Muchos sitios (Fed, FMI, Economist) devuelven 403 a User-Agents que no
# parecen un navegador. La SEC, además, exige un correo de contacto.
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/122.0 Safari/537.36",
    "Accept": "application/rss+xml,application/xml,text/xml,application/atom+xml,*/*",
    "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
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
