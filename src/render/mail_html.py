"""Correo HTML. Autocontenido: sin JavaScript ni recursos externos, porque
los clientes de correo los bloquean. Los gráficos son SVG en línea."""
from __future__ import annotations

from datetime import datetime

CSS = """
body{margin:0;padding:0;background:#0d0f14;color:#e8eaf0;
     font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;
     font-size:15px;line-height:1.6}
.wrap{max-width:660px;margin:0 auto;padding:28px 20px 60px}
.kicker{font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:#7b8399;margin-bottom:10px}
h1{font-size:24px;line-height:1.3;margin:0 0 8px;font-weight:650}
.sub{color:#aab2c5;margin:0 0 18px}
.badge{display:inline-block;padding:4px 12px;border-radius:999px;font-size:12px;
       background:#1a2133;color:#8fb0ff;border:1px solid #2a3550}
.tape{width:100%;border-collapse:collapse;margin:20px 0;font-size:13px}
.tape td{padding:7px 10px;border-bottom:1px solid #1e2431}
.tape td:first-child{color:#aab2c5}
.tape td:last-child{text-align:right;font-variant-numeric:tabular-nums}
.up{color:#43c98a}.down{color:#f0666c}.flat{color:#7b8399}
h2{font-size:12px;text-transform:uppercase;letter-spacing:.11em;color:#7b8399;
   margin:30px 0 12px;padding-bottom:7px;border-bottom:1px solid #1e2431}
.item{margin-bottom:18px}
.fact{font-weight:600;margin-bottom:4px}
.why{color:#c3cadb;margin-bottom:4px}
.impl{color:#8fb0ff;font-size:14px}
.priced{color:#c9a227;font-size:13px;font-style:italic}
.block{background:#141926;border-left:3px solid #3a55b8;padding:13px 15px;
       margin:12px 0;border-radius:0 8px 8px 0}
.alert{background:#1e1418;border-left:3px solid #f0666c}
a{color:#8fb0ff;text-decoration:none}
.srcs a{font-size:12px;margin-left:2px}
ul{padding-left:20px;margin:8px 0}li{margin-bottom:7px}
.foot{margin-top:38px;padding-top:14px;border-top:1px solid #1e2431;
      color:#616a80;font-size:11px}
.mono{font-variant-numeric:tabular-nums}
"""


def _cls(v):
    if not isinstance(v, (int, float)):
        return "flat"
    return "up" if v > 0 else "down" if v < 0 else "flat"


def _pct(v):
    return f"{v:+.2f}%" if isinstance(v, (int, float)) else "n/d"


def sparkline(series: list[float], width=110, height=26, color="#8fb0ff") -> str:
    """SVG en línea: funciona en Gmail, Apple Mail y Outlook web."""
    if not series or len(series) < 2:
        return ""
    lo, hi = min(series), max(series)
    rng = (hi - lo) or 1
    step = width / (len(series) - 1)
    pts = " ".join(f"{i*step:.1f},{height - ((v-lo)/rng)*height:.1f}"
                   for i, v in enumerate(series))
    stroke = "#43c98a" if series[-1] >= series[0] else "#f0666c"
    return (f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
            f'style="vertical-align:middle"><polyline fill="none" stroke="{stroke}" '
            f'stroke-width="1.6" points="{pts}"/></svg>')


def _srcs(idxs, items):
    out = []
    for i in idxs or []:
        if isinstance(i, int) and 1 <= i <= len(items):
            out.append(f'<a href="{items[i-1]["url"]}">[{i}]</a>')
    return f'<span class="srcs">{" ".join(out)}</span>' if out else ""


def render(brief, items, quotes, macro, movers, regime, ipos, calendar,
           dashboard_url=None) -> str:
    now = datetime.now().strftime("%d de %B de %Y · %H:%M")
    lookup = {q["name"]: q for q in quotes if q.get("ok")}
    H = [f"<!DOCTYPE html><html><head><meta charset='utf-8'>",
         f"<style>{CSS}</style></head><body><div class='wrap'>"]

    H.append(f"<div class='kicker'>Market Radar · {now}</div>")
    H.append(f"<h1>{brief.get('headline','')}</h1>")
    if brief.get("subhead"):
        H.append(f"<p class='sub'>{brief['subhead']}</p>")
    H.append(f"<span class='badge'>{regime['label']}</span>")
    H.append(f"<p class='sub' style='margin-top:10px'>{'; '.join(regime['signals'])}</p>")
    if brief.get("regime_read"):
        H.append(f"<div class='block'>{brief['regime_read']}</div>")

    # cinta principal con sparklines
    keys = ["S&P 500", "Nasdaq 100", "VIX", "DXY", "USD/COP", "Petróleo WTI", "Oro", "BTC"]
    rows = []
    for k in keys:
        q = lookup.get(k)
        if not q:
            continue
        rows.append(f"<tr><td>{q['name']}</td><td>{sparkline(q.get('series', []))}</td>"
                    f"<td class='mono'>{q['last']}</td>"
                    f"<td class='{_cls(q.get('chg_1d'))} mono'>{_pct(q.get('chg_1d'))}</td></tr>")
    for m in macro[:3]:
        rows.append(f"<tr><td>{m['name']}</td><td>{sparkline(m.get('series', []))}</td>"
                    f"<td class='mono'>{m['last']}{m['unit']}</td>"
                    f"<td class='{_cls(m['chg_1d'])} mono'>{m['chg_1d']:+} {m['delta_unit']}</td></tr>")
    if rows:
        H.append("<table class='tape'>" + "".join(rows) + "</table>")

    if movers["anomalos"]:
        H.append("<h2>Movimientos estadísticamente inusuales</h2>")
        for q in movers["anomalos"][:6]:
            cls = "block alert" if q.get("extremo") else "block"
            H.append(f"<div class='{cls}'><b>{q['name']}</b> "
                     f"<span class='{_cls(q['chg_1d'])}'>{_pct(q['chg_1d'])}</span> "
                     f"— {abs(q['z']):.1f} desviaciones estándar sobre su volatilidad normal "
                     f"({q.get('vol_anual')}% anualizada)</div>")

    for sec in brief.get("sections", []):
        sec_items = sec.get("items") or []
        if not sec_items:
            continue
        H.append(f"<h2>{sec['title']}</h2>")
        for it in sec_items:
            H.append("<div class='item'>")
            H.append(f"<div class='fact'>{it.get('fact','')}{_srcs(it.get('sources'), items)}</div>")
            if it.get("why"):
                H.append(f"<div class='why'>{it['why']}</div>")
            if it.get("implication"):
                H.append(f"<div class='impl'>→ {it['implication']}</div>")
            if it.get("priced_in"):
                H.append(f"<div class='priced'>Ya descontado: {it['priced_in']}</div>")
            H.append("</div>")

    for key, label in (("price_action", "Lectura del movimiento de precios"),
                       ("what_changed", "Qué cambió"),
                       ("cross_asset", "Coherencia entre activos"),
                       ("colombia", "Colombia")):
        if brief.get(key):
            H.append(f"<h2>{label}</h2><p>{brief[key]}</p>")

    if brief.get("watch_next"):
        H.append("<h2>Por vigilar</h2><ul>")
        for w in brief["watch_next"]:
            if isinstance(w, dict):
                H.append(f"<li><b>{w.get('when','')}</b> — {w.get('what','')}"
                         f"<br><span class='why'>{w.get('why','')}</span></li>")
            else:
                H.append(f"<li>{w}</li>")
        H.append("</ul>")

    if brief.get("contrarian"):
        H.append(f"<h2>Contra-argumento</h2><div class='block'>{brief['contrarian']}</div>")

    if brief.get("learning_note"):
        H.append(f"<h2>Concepto del día</h2><div class='block'>{brief['learning_note']}</div>")

    if ipos:
        H.append("<h2>Mercado primario</h2><ul>")
        for x in ipos[:8]:
            H.append(f"<li>{x.get('company','')} ({x.get('ticker','')}) — "
                     f"{x.get('status','')} {x.get('date') or ''} {x.get('size') or ''}</li>")
        H.append("</ul>")

    if calendar:
        H.append("<h2>Calendario</h2><ul>"
                 + "".join(f"<li>{c['date']} — {c['event']}</li>" for c in calendar[:8])
                 + "</ul>")

    H.append("<h2>Fuentes</h2><ul>")
    for i, it in enumerate(items, 1):
        H.append(f"<li>[{i}] <a href='{it['url']}'>{it['title']}</a> "
                 f"<span class='why'>— {it['source']}</span></li>")
    H.append("</ul>")

    meta = brief.get("_meta", {})
    H.append(f"<div class='foot'>Generado automáticamente · modelo {meta.get('model','')} · "
             f"{meta.get('input_tokens',0)} tokens de entrada · costo US${meta.get('cost_usd',0)}")
    if dashboard_url:
        H.append(f" · <a href='{dashboard_url}'>dashboard</a>")
    H.append("</div></div></body></html>")
    return "".join(H)
