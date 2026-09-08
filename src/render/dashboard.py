"""Genera los JSON que consume la PWA y mantiene el archivo histórico."""
from __future__ import annotations

import json
import os
from datetime import datetime

MAX_ARCHIVE = 240   # ~6 meses de dos briefings diarios


def write(brief, items, quotes, macro, movers, regime, curve, ipos, calendar,
          errors, outdir: str) -> dict:
    os.makedirs(outdir, exist_ok=True)
    now = datetime.now()
    stamp = now.strftime("%Y%m%d-%H%M")

    payload = {
        "generated_at": now.isoformat(timespec="minutes"),
        "brief": brief,
        "regime": regime,
        "movers": {k: [_slim(q) for q in v] for k, v in movers.items()},
        "quotes": [_slim(q, keep_series=True) for q in quotes if q.get("ok")],
        "macro": macro,
        "curve": curve,
        "ipos": ipos,
        "calendar": calendar,
        "items": [{k: v for k, v in it.items() if k != "score_why"} for it in items],
        "errors": errors,
    }

    _dump(os.path.join(outdir, "latest.json"), payload)
    _dump(os.path.join(outdir, f"{stamp}.json"), payload, compact=True)

    index_path = os.path.join(outdir, "index.json")
    archive = []
    if os.path.exists(index_path):
        try:
            with open(index_path, encoding="utf-8") as fh:
                archive = json.load(fh)
        except json.JSONDecodeError:
            archive = []
    archive.insert(0, {
        "file": f"{stamp}.json",
        "at": payload["generated_at"],
        "headline": brief.get("headline", ""),
        "regime": regime["label"],
    })
    # limpia archivos viejos del disco además del índice
    for old in archive[MAX_ARCHIVE:]:
        path = os.path.join(outdir, old["file"])
        if os.path.exists(path):
            os.remove(path)
    _dump(index_path, archive[:MAX_ARCHIVE])
    return payload


def _slim(q: dict, keep_series: bool = False) -> dict:
    drop = {"returns"} if keep_series else {"returns", "series"}
    return {k: v for k, v in q.items() if k not in drop}


def _dump(path: str, obj, compact: bool = False) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=None if compact else 1)
