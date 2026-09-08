"""Análisis cuantitativo previo al modelo.

Todo lo de este módulo es determinista y verificable. Lo que sale de aquí
es HECHO, no opinión: el modelo lo recibe ya calculado y no puede alterarlo.
"""
from __future__ import annotations

import statistics


# ═══════════════════════ MOVIMIENTOS ANÓMALOS ═══════════════════════
def z_score(quote: dict, lookback: int) -> float | None:
    """Cuántas desviaciones estándar se movió hoy frente a su propia
    volatilidad reciente. Un 2% en el S&P es enorme; en bitcoin es rutina.
    El z-score hace comparables activos con volatilidades muy distintas."""
    rets = quote.get("returns") or []
    if len(rets) < 20 or quote.get("chg_1d") is None:
        return None
    window = rets[-lookback:]
    sd = statistics.pstdev(window)
    if sd < 1e-9:
        return None
    return round(quote["chg_1d"] / sd, 2)


def annualized_vol(quote: dict, lookback: int = 60) -> float | None:
    rets = quote.get("returns") or []
    if len(rets) < 20:
        return None
    return round(statistics.pstdev(rets[-lookback:]) * (252 ** 0.5), 1)


def enrich(quotes: list[dict], cfg: dict) -> list[dict]:
    lookback = cfg["movers"]["lookback_days"]
    for q in quotes:
        if not q.get("ok"):
            continue
        q["z"] = z_score(q, lookback)
        q["vol_anual"] = annualized_vol(q, lookback)
        q["anomalo"] = bool(q.get("z") is not None and abs(q["z"]) >= cfg["movers"]["z_alert"])
        q["extremo"] = bool(q.get("z") is not None and abs(q["z"]) >= cfg["movers"]["z_strong"])
    return quotes


def top_movers(quotes: list[dict], cfg: dict) -> dict:
    """Mayores movimientos por magnitud absoluta y por anomalía estadística."""
    valid = [q for q in quotes if q.get("ok") and q.get("chg_1d") is not None]
    by_pct = sorted(valid, key=lambda q: abs(q["chg_1d"]), reverse=True)
    by_z = sorted([q for q in valid if q.get("z") is not None],
                  key=lambda q: abs(q["z"]), reverse=True)
    n = cfg["movers"]["top_n"]
    return {
        "subidas": [q for q in sorted(valid, key=lambda x: x["chg_1d"], reverse=True)[:5]],
        "bajadas": [q for q in sorted(valid, key=lambda x: x["chg_1d"])[:5]],
        "mayor_magnitud": by_pct[:n],
        "anomalos": [q for q in by_z if q.get("anomalo")][:n],
        "extremos": [q for q in by_z if q.get("extremo")],
    }


# ═══════════════════════════ RÉGIMEN ═══════════════════════════
def classify_regime(quotes: list[dict], macro: list[dict]) -> dict:
    """Clasifica el día como risk-on / risk-off con una regla explícita,
    no con la intuición del modelo. El modelo puede matizarla, pero parte
    de un número que cualquiera puede recalcular."""
    idx = {q["name"]: q for q in quotes if q.get("ok")}
    mac = {m["name"]: m for m in macro}
    signals, score = [], 0.0

    def add(cond: bool | None, weight: float, text_on: str, text_off: str):
        nonlocal score
        if cond is None:
            return
        score += weight if cond else -weight
        signals.append(text_on if cond else text_off)

    spx = idx.get("S&P 500", {}).get("chg_1d")
    if spx is not None:
        add(spx > 0, 1.0, f"S&P {spx:+.2f}%", f"S&P {spx:+.2f}%")

    vix = idx.get("VIX", {}).get("chg_1d")
    if vix is not None:
        add(vix < 0, 1.0, f"VIX {vix:+.1f}% (cede)", f"VIX {vix:+.1f}% (sube)")

    hy = mac.get("Spread HY EEUU", {}).get("chg_1d")
    if hy is not None:
        add(hy < 0, 1.2, f"spread HY {hy:+.0f} pb (comprime)", f"spread HY {hy:+.0f} pb (amplía)")

    gold = idx.get("Oro", {}).get("chg_1d")
    if gold is not None:
        add(gold < 0, 0.6, f"oro {gold:+.2f}%", f"oro {gold:+.2f}% (refugio)")

    dxy = idx.get("DXY", {}).get("chg_1d")
    if dxy is not None:
        add(dxy < 0, 0.8, f"dólar {dxy:+.2f}% (débil)", f"dólar {dxy:+.2f}% (fuerte)")

    eem = idx.get("Emergentes (EEM)", {}).get("chg_1d")
    if eem is not None:
        add(eem > 0, 0.8, f"emergentes {eem:+.2f}%", f"emergentes {eem:+.2f}%")

    label = ("risk-on" if score >= 2 else "risk-off" if score <= -2
             else "mixto" if abs(score) > 0.5 else "sin dirección")
    return {"label": label, "score": round(score, 2), "signals": signals}


# ═══════════════════════ ESTRUCTURA DE TASAS ═══════════════════════
def curve_summary(macro: list[dict]) -> dict:
    m = {x["name"]: x for x in macro}
    out = {}
    for key, label in (("UST 2 años", "2y"), ("UST 10 años", "10y"), ("UST 30 años", "30y")):
        if key in m:
            out[label] = {"nivel": m[key]["last"], "1d_pb": m[key]["chg_1d"],
                          "1m_pb": m[key]["chg_1m"]}
    if "Pendiente 10y-2y" in m:
        s = m["Pendiente 10y-2y"]
        out["pendiente_10y2y"] = {"nivel": s["last"], "1d_pb": s["chg_1d"],
                                  "invertida": s["last"] < 0}
    if "Breakeven 10y" in m and "Tasa real 10y" in m:
        out["descomposicion_10y"] = {
            "real": m["Tasa real 10y"]["last"],
            "inflacion_implicita": m["Breakeven 10y"]["last"],
            "movimiento_1d_real_pb": m["Tasa real 10y"]["chg_1d"],
            "movimiento_1d_breakeven_pb": m["Breakeven 10y"]["chg_1d"],
        }
    return out
