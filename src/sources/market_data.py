"""Macro, cripto, IPOs y calendario. Todas gratuitas."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import requests

from src.sources.common import HEADERS, TIMEOUT, log_error, retry

# ───────────────────────── FRED ─────────────────────────
FRED = "https://api.stlouisfed.org/fred/series/observations"


@retry(times=1)
def _fred_series(series_id: str, key: str, start: str) -> list[dict]:
    r = requests.get(FRED, headers=HEADERS, timeout=TIMEOUT, params={
        "series_id": series_id, "api_key": key, "file_type": "json",
        "observation_start": start, "sort_order": "desc", "limit": 120})
    r.raise_for_status()
    return [o for o in r.json().get("observations", []) if o["value"] not in (".", "")]


def fetch_macro(series: list[dict], api_key: str | None) -> list[dict]:
    if not api_key:
        log_error("fred", "FRED_API_KEY no configurada — bloque macro vacío")
        return []
    start = (datetime.now(timezone.utc) - timedelta(days=400)).strftime("%Y-%m-%d")
    out = []
    for s in series:
        try:
            obs = _fred_series(s["id"], api_key, start)
            if len(obs) < 2:
                continue
            vals = [float(o["value"]) for o in obs]
            last, prev = vals[0], vals[1]
            month = vals[min(21, len(vals) - 1)]
            year = vals[min(250, len(vals) - 1)]
            is_pct = s.get("u") == "%"
            mult = 100 if is_pct else 1
            out.append({
                "id": s["id"], "name": s["n"], "unit": s.get("u", ""),
                "last": round(last, 4), "as_of": obs[0]["date"],
                "chg_1d": round((last - prev) * mult, 1),
                "chg_1m": round((last - month) * mult, 1),
                "chg_1y": round((last - year) * mult, 1),
                "delta_unit": "pb" if is_pct else "",
                "series": [round(v, 4) for v in reversed(vals[:90])],
            })
        except Exception as exc:  # noqa: BLE001
            log_error(f"fred[{s['id']}]", exc)
    return out


# ─────────────────────── CoinGecko ───────────────────────
def fetch_crypto(coins: list[dict]) -> list[dict]:
    if not coins:
        return []
    try:
        ids = ",".join(c["id"] for c in coins)
        r = requests.get("https://api.coingecko.com/api/v3/coins/markets",
                         headers=HEADERS, timeout=TIMEOUT,
                         params={"vs_currency": "usd", "ids": ids,
                                 "price_change_percentage": "24h,7d,30d"})
        r.raise_for_status()
        by_id = {row["id"]: row for row in r.json()}
        out = []
        for c in coins:
            row = by_id.get(c["id"])
            if not row:
                continue
            out.append({
                "ticker": c["id"], "name": c["n"], "bucket": "crypto", "region": "Cripto",
                "ok": True, "last": row.get("current_price"),
                "chg_1d": _r(row.get("price_change_percentage_24h_in_currency")),
                "chg_5d": _r(row.get("price_change_percentage_7d_in_currency")),
                "chg_1m": _r(row.get("price_change_percentage_30d_in_currency")),
                "chg_ytd": None,
                "market_cap": row.get("market_cap"),
                "high_52w": row.get("ath"),
                "pct_from_high": _r(row.get("ath_change_percentage")),
                "series": [], "returns": [],
            })
        return out
    except Exception as exc:  # noqa: BLE001
        log_error("coingecko", exc)
        return []


def _r(v):
    return round(v, 2) if isinstance(v, (int, float)) else None


# ───────────────────────── IPOs ─────────────────────────
def fetch_ipos() -> list[dict]:
    """Calendario de Nasdaq. Endpoint no contractual: si cambia, se reporta y sigue."""
    rows: list[dict] = []
    try:
        month = datetime.now(timezone.utc).strftime("%Y-%m")
        r = requests.get(f"https://api.nasdaq.com/api/ipo/calendar?date={month}",
                         headers={**HEADERS, "Accept": "application/json"}, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json().get("data") or {}
        for bucket, label in (("priced", "colocada"), ("upcoming", "próxima"),
                              ("filed", "registrada")):
            block = data.get(bucket) or {}
            table = block.get("table") or block.get("upcomingTable") or {}
            for row in (table.get("rows") or [])[:12]:
                rows.append({
                    "status": label,
                    "company": row.get("companyName"),
                    "ticker": row.get("proposedTickerSymbol") or row.get("symbol"),
                    "date": row.get("pricedDate") or row.get("expectedPriceDate") or row.get("filedDate"),
                    "size": row.get("dollarValueOfSharesOffered"),
                    "price": row.get("proposedSharePrice"),
                    "exchange": row.get("proposedExchange"),
                })
    except Exception as exc:  # noqa: BLE001
        log_error("nasdaq_ipos", exc)
    return rows


# ────────────────── Calendario económico ──────────────────
def fetch_calendar(days_ahead: int = 7) -> list[dict]:
    """Próximos publicaciones de datos de FRED (fechas oficiales de release)."""
    out: list[dict] = []
    try:
        import os
        key = os.environ.get("FRED_API_KEY")
        if not key:
            return []
        today = datetime.now(timezone.utc).date()
        r = requests.get("https://api.stlouisfed.org/fred/releases/dates",
                         headers=HEADERS, timeout=TIMEOUT,
                         params={"api_key": key, "file_type": "json",
                                 "realtime_start": today.isoformat(),
                                 "realtime_end": (today + timedelta(days=days_ahead)).isoformat(),
                                 "include_release_dates_with_no_data": "true",
                                 "sort_order": "asc", "limit": 60})
        r.raise_for_status()
        keep = ("Consumer Price Index", "Employment Situation", "Gross Domestic Product",
                "Personal Income", "Producer Price", "Retail Sales", "FOMC",
                "Industrial Production", "Housing Starts", "Job Openings")
        for row in r.json().get("release_dates", []):
            name = row.get("release_name", "")
            if any(k.lower() in name.lower() for k in keep):
                out.append({"date": row.get("date"), "event": name})
    except Exception as exc:  # noqa: BLE001
        log_error("fred_calendar", exc)
    return out[:12]
