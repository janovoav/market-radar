"""Filtro de relevancia previo al modelo.

Reduce ~500 titulares a ~55. Es determinista: mismo input, mismo output.
Si el brief trae ruido, se corrige un peso en config.yaml — nunca el prompt.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone


def score_item(item: dict, cfg: dict) -> tuple[float, list[str]]:
    sc = cfg["scoring"]
    text = f"{item.get('title','')} {item.get('summary','')}".lower()

    reasons = []
    base = sc["tier_weight"].get(item.get("tier", 2), 1.0)
    total = base

    for kw, w in sc["keywords"].items():
        if kw in text:
            total += float(w)
            reasons.append(f"+{w} {kw}")
    for kw, w in sc.get("demote", {}).items():
        if kw in text:
            total += float(w)
            reasons.append(f"{w} {kw}")

    if item.get("n_sources", 1) > 1:
        bonus = sc.get("cross_source_bonus", 2.0) * (item["n_sources"] - 1)
        total += bonus
        reasons.append(f"+{bonus:.1f} confirmada en {item['n_sources']} fuentes")

    if item.get("published"):
        try:
            age_h = (datetime.now(timezone.utc)
                     - datetime.fromisoformat(item["published"])).total_seconds() / 3600
            decay = math.pow(0.5, max(age_h, 0) / sc["recency_half_life_hours"])
            total *= decay
            reasons.append(f"×{decay:.2f} antigüedad {age_h:.0f}h")
        except (ValueError, TypeError):
            pass

    return round(total, 2), reasons


def rank(items: list[dict], cfg: dict) -> list[dict]:
    for it in items:
        it["score"], it["score_why"] = score_item(it, cfg)

    keep = [i for i in items if i["score"] >= cfg["scoring"]["min_score"]]
    keep.sort(key=lambda x: x["score"], reverse=True)

    limit = cfg["scoring"]["max_items_to_model"]
    selected, chosen_ids = [], set()

    # cuotas por tema: garantizan presencia, no posición
    for topic, quota in cfg["scoring"].get("topic_quotas", {}).items():
        for it in [x for x in keep if x.get("topic") == topic][:quota]:
            if id(it) not in chosen_ids:
                selected.append(it)
                chosen_ids.add(id(it))

    for it in keep:
        if len(selected) >= limit:
            break
        if id(it) not in chosen_ids:
            selected.append(it)
            chosen_ids.add(id(it))

    selected.sort(key=lambda x: x["score"], reverse=True)
    return selected[:limit]
