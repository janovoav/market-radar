"""Precios de mercado.

Fuente principal: Yahoo Finance (endpoint público de gráficos). Responde bien
desde servidores de datacenter, que es donde corre GitHub Actions.
Respaldo: Stooq, que funciona desde IP residencial pero bloquea datacenters.

Cada activo se intenta con Yahoo y, si falla, con Stooq. Ninguna excepción
sube: un activo caído deja `ok: False` y el pipeline continúa.
"""
from __future__ import annotations

import csv
import datetime as _dt
import io
from concurrent.futures import ThreadPoolExecutor

import requests

from src.sources.common import log_error, retry

TIMEOUT = 25

# Yahoo rechaza User-Agents que no parezcan navegador.
BROWSER = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/122.0 Safari/537.36",
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "en-US,en;q=0.9",
}

YAHOO = "https://query{host}.finance.yahoo.com/v8/finance/chart/{t}"


# ───────────────────────── Yahoo Finance ─────────────────────────
@retry(times=1, wait=1.0)
def _yahoo(ticker: str, rng: str = "1y") -> list[tuple[str, float]]:
    """Devuelve [(fecha, cierre)] del más viejo al más nuevo."""
    last_exc: Exception | None = None
    for host in (1, 2):   # query1 y query2 son espejos
        try:
            r = requests.get(YAHOO.format(host=host, t=ticker), headers=BROWSER,
                             timeout=TIMEOUT,
                             params={"range": rng, "interval": "1d",
                                     "includePrePost": "false"})
            r.raise_for_status()
            result = ((r.json().get("chart") or {}).get("result")) or []
            if not result:
                raise RuntimeError("respuesta sin datos")
            res = result[0]
            stamps = res.get("timestamp") or []
            quote_block = ((res.get("indicators") or {}).get("quote") or [{}])[0]
            closes = quote_block.get("close") or []
            rows = []
            for ts, close in zip(stamps, closes):
                if close is None:
                    continue
                rows.append((_dt.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d"),
                             float(close)))
            if len(rows) < 3:
                raise RuntimeError(f"solo {len(rows)} observaciones")
            return rows
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
    raise last_exc  # type: ignore[misc]


# ───────────────────────────── Stooq ─────────────────────────────
@retry(times=1, wait=1.0)
def _stooq(ticker: str) -> list[tuple[str, float]]:
    r = requests.get(f"https://stooq.com/q/d/l/?s={ticker}&i=d",
                     headers=BROWSER, timeout=TIMEOUT)
    r.raise_for_status()
    head = r.text[:200].lower()
    if "<html" in head or "exceeded" in head:
        raise RuntimeError("Stooq bloqueado o ticker inválido")
    rows = []
    for row in csv.DictReader(io.StringIO(r.text)):
        val = row.get("Close")
        if val in (None, "", "N/D"):
            continue
        try:
            rows.append((row["Date"], float(val)))
        except ValueError:
            continue
    if len(rows) < 3:
        raise RuntimeError("serie demasiado corta")
    return rows


# ───────────────────────── cálculo común ─────────────────────────
def _metrics(rows: list[tuple[str, float]], history_days: int) -> dict:
    rows = rows[-history_days:]
    closes = [c for _, c in rows]
    last, prev = closes[-1], closes[-2]

    def pct(a: float, b: float) -> float | None:
        return round((a / b - 1) * 100, 2) if b else None

    i5 = -6 if len(closes) >= 6 else 0
    i21 = -22 if len(closes) >= 22 else 0
    year = rows[-1][0][:4]
    ytd_base = next((c for d, c in rows if d[:4] == year), closes[0])
    rets = [(closes[i] / closes[i - 1] - 1) * 100
            for i in range(1, len(closes)) if closes[i - 1]]

    return {
        "ok": True,
        "last": round(last, 4),
        "as_of": rows[-1][0],
        "chg_1d": pct(last, prev),
        "chg_5d": pct(last, closes[i5]),
        "chg_1m": pct(last, closes[i21]),
        "chg_ytd": pct(last, ytd_base),
        "high_52w": round(max(closes), 4),
        "low_52w": round(min(closes), 4),
        "pct_from_high": pct(last, max(closes)),
        "returns": rets,
        "series": [round(c, 4) for c in closes[-90:]],
    }


def quote(asset: dict, history_days: int = 260) -> dict:
    """Nunca lanza excepción: un activo caído deja ok=False."""
    base = {"ticker": asset["t"], "name": asset["n"], "region": asset.get("r", ""),
            "bucket": asset.get("bucket", ""), "last": None, "series": [],
            "ok": False, "source": None}

    errores = []
    for nombre, fn, tk in (("yahoo", _yahoo, asset["t"]),
                           ("stooq", _stooq, asset.get("stooq"))):
        if not tk:
            continue
        try:
            base.update(_metrics(fn(tk), history_days))
            base["source"] = nombre
            return base
        except Exception as exc:  # noqa: BLE001
            errores.append(f"{nombre}: {type(exc).__name__}")

    log_error(f"precio[{asset['n']}]", " | ".join(errores) or "sin fuentes")
    return base


def fetch_universe(assets: list[dict], workers: int = 8) -> list[dict]:
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(quote, assets))
