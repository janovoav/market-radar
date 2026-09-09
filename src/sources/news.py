"""Noticias vía RSS/Atom."""
from __future__ import annotations

import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

import feedparser
import requests

from src.sources.common import HEADERS, TIMEOUT, log_error, strip_html


def _fetch_one(feed: dict, cutoff: datetime) -> list[dict]:
    out: list[dict] = []
    try:
        # La SEC exige un User-Agent que identifique al usuario con un correo.
        headers = dict(HEADERS)
        if "sec.gov" in feed["u"]:
            headers["User-Agent"] = "Market Radar juanchonovoavillarreal@gmail.com"
        r = requests.get(feed["u"], headers=headers, timeout=TIMEOUT)
        r.raise_for_status()
        parsed = feedparser.parse(r.content)
        for entry in parsed.entries[:70]:
            ts = None
            for key in ("published_parsed", "updated_parsed"):
                val = getattr(entry, key, None)
                if val:
                    ts = datetime.fromtimestamp(time.mktime(val), tz=timezone.utc)
                    break
            if ts and ts < cutoff:
                continue
            title = strip_html(getattr(entry, "title", ""))
            if not title:
                continue
            out.append({
                "title": title,
                "url": getattr(entry, "link", "") or "",
                "summary": strip_html(getattr(entry, "summary", ""))[:700],
                "published": ts.isoformat() if ts else None,
                "source": feed["n"],
                "tier": int(feed.get("tier", 2)),
                "topic": feed.get("topic", "general"),
            })
    except Exception as exc:  # noqa: BLE001
        log_error(f"feed[{feed['n']}]", exc)
    return out


def _norm(title: str) -> str:
    key = re.sub(r"[^a-z0-9áéíóúñ ]", "", title.lower())
    return " ".join(key.split()[:9])


def dedupe(items: list[dict]) -> list[dict]:
    """Colapsa la misma historia; conserva la fuente de mejor tier y cuenta
    en cuántas fuentes apareció (señal de importancia)."""
    best: dict[str, dict] = {}
    for it in items:
        key = _norm(it["title"])
        if not key:
            continue
        prev = best.get(key)
        if prev is None:
            it["n_sources"] = 1
            best[key] = it
        else:
            merged_count = prev.get("n_sources", 1) + 1
            winner = it if it["tier"] < prev["tier"] else prev
            loser = prev if winner is it else it
            winner["n_sources"] = merged_count
            others = set(winner.get("also_in", []))
            others.add(loser["source"])
            winner["also_in"] = sorted(others)
            best[key] = winner
    return list(best.values())


def fetch(feeds: list[dict], lookback_hours: int = 24) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    items: list[dict] = []
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = [pool.submit(_fetch_one, f, cutoff) for f in feeds]
        for fut in as_completed(futures):
            items.extend(fut.result())
    return dedupe(items)


def check(feeds: list[dict]) -> list[dict]:
    """Diagnóstico: qué feeds responden y con cuántas entradas."""
    results = []
    for f in feeds:
        row = {"name": f["n"], "url": f["u"]}
        try:
            r = requests.get(f["u"], headers=HEADERS, timeout=TIMEOUT)
            n = len(feedparser.parse(r.content).entries)
            row.update({"status": "OK" if n else "VACÍO", "http": r.status_code, "entries": n})
        except Exception as exc:  # noqa: BLE001
            row.update({"status": "FALLA", "http": None, "entries": 0,
                        "error": f"{type(exc).__name__}: {exc}"})
        results.append(row)
    return results
