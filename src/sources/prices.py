"""Precios de mercado desde Stooq (CSV público, sin API key).

Devuelve además la serie histórica recortada, que se usa para:
  · calcular z-scores de movimientos anómalos
  · dibujar los sparklines del dashboard
"""
from __future__ import annotations

import csv
import io
from concurrent.futures import ThreadPoolExecutor

import requests

from src.sources.common import HEADERS, TIMEOUT, log_error, retry

STOOQ = "https://stooq.com/q/d/l/?s={t}&i=d"


@retry(times=2)
def _download(ticker: str) -> list[tuple[str, float]]:
    r = requests.get(STOOQ.format(t=ticker), headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    text = r.text
    if "Exceeded" in text[:200] or "<html" in text[:200].lower():
        raise RuntimeError("Stooq devolvió HTML (ticker inválido o límite alcanzado)")
    rows = []
    for row in csv.DictReader(io.StringIO(text)):
        raw = row.get("Close")
        if raw in (None, "", "N/D"):
            continue
        try:
            rows.append((row["Date"], float(raw)))
        except ValueError:
            continue
    return rows


def quote(asset: dict, history_days: int = 260) -> dict:
    """Cotización + estadísticas + serie para graficar. Nunca lanza excepción."""
    base = {"ticker": asset["t"], "name": asset["n"], "region": asset.get("r", ""),
            "bucket": asset.get("bucket", ""), "last": None, "series": [], "ok": False}
    try:
        rows = _download(asset["t"])
        if len(rows) < 3:
            log_error(f"precio[{asset['t']}]", "serie demasiado corta")
            return base

        rows = rows[-history_days:]
        closes = [c for _, c in rows]
        last, prev = closes[-1], closes[-2]

        def pct(a: float, b: float) -> float | None:
            return round((a / b - 1) * 100, 2) if b else None

        idx5 = -6 if len(closes) >= 6 else 0
        idx21 = -22 if len(closes) >= 22 else 0
        year = rows[-1][0][:4]
        ytd_base = next((c for d, c in rows if d[:4] == year), closes[0])

        # retornos diarios para volatilidad
        rets = [(closes[i] / closes[i - 1] - 1) * 100
                for i in range(1, len(closes)) if closes[i - 1]]

        base.update({
            "ok": True,
            "last": round(last, 4),
            "as_of": rows[-1][0],
            "chg_1d": pct(last, prev),
            "chg_5d": pct(last, closes[idx5]),
            "chg_1m": pct(last, closes[idx21]),
            "chg_ytd": pct(last, ytd_base),
            "high_52w": round(max(closes), 4),
            "low_52w": round(min(closes), 4),
            "pct_from_high": pct(last, max(closes)),
            "returns": rets,
            "series": [round(c, 4) for c in closes[-90:]],
        })
    except Exception as exc:  # noqa: BLE001
        log_error(f"precio[{asset['t']}]", exc)
    return base


def fetch_universe(assets: list[dict], workers: int = 10) -> list[dict]:
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(quote, assets))
