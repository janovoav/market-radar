"""Envío por Telegram.

Se usa HTML como parse_mode (no Markdown): es mucho más tolerante con
caracteres sueltos como * _ ( ) que aparecen todo el tiempo en texto
financiero y que rompen el Markdown de Telegram.
"""
from __future__ import annotations

import html
import os

import requests

LIMIT = 4000  # el límite real es 4096; dejamos margen


def esc(t) -> str:
    return html.escape(str(t or ""), quote=False)


def _src_links(idxs, items) -> str:
    out = []
    for i in idxs or []:
        if isinstance(i, int) and 1 <= i <= len(items):
            out.append(f'<a href="{esc(items[i-1]["url"])}">[{i}]</a>')
    return " " + "".join(out) if out else ""


def _arrow(v) -> str:
    if not isinstance(v, (int, float)):
        return ""
    return "▲" if v > 0 else "▼" if v < 0 else "="


def build_message(brief, items, quotes, movers, regime, cfg, dashboard_url=None) -> str:
    L = [f"<b>{esc(brief.get('headline', 'Briefing'))}</b>"]
    if brief.get("subhead"):
        L.append(esc(brief["subhead"]))
    L.append("")

    L.append(f"<b>Régimen:</b> {esc(regime['label'])} "
             f"<i>({esc('; '.join(regime['signals'][:4]))})</i>")
    L.append("")

    # cinta de precios clave
    keys = ["S&P 500", "Nasdaq 100", "VIX", "UST 10 años", "DXY", "USD/COP",
            "Petróleo WTI", "Oro", "BTC"]
    tape = []
    lookup = {q["name"]: q for q in quotes if q.get("ok")}
    for k in keys:
        q = lookup.get(k)
        if q and q.get("chg_1d") is not None:
            tape.append(f"{k} {q['last']} {_arrow(q['chg_1d'])}{abs(q['chg_1d']):.2f}%")
    if tape:
        L.append("<pre>" + "\n".join(tape) + "</pre>")

    if movers["anomalos"]:
        L.append("<b>⚡ Movimientos inusuales</b>")
        for q in movers["anomalos"][:5]:
            L.append(f"· {esc(q['name'])}: {q['chg_1d']:+.2f}% "
                     f"<i>(z {q['z']:+.1f})</i>")
        L.append("")

    count, cap = 0, cfg["delivery"]["max_bullets_in_push"]
    for sec in brief.get("sections", []):
        sec_items = sec.get("items") or []
        if not sec_items or count >= cap:
            continue
        L.append(f"<b>{esc(sec['title'])}</b>")
        for it in sec_items:
            if count >= cap:
                break
            line = f"· {esc(it.get('fact', ''))}{_src_links(it.get('sources'), items)}"
            L.append(line)
            if it.get("implication"):
                L.append(f"  <i>→ {esc(it['implication'])}</i>")
            count += 1
        L.append("")

    for key, label in (("price_action", "Movimiento de precios"),
                       ("what_changed", "Qué cambió"),
                       ("cross_asset", "Entre activos"),
                       ("colombia", "Colombia")):
        if brief.get(key):
            L.append(f"<b>{label}</b>\n{esc(brief[key])}\n")

    if brief.get("watch_next"):
        L.append("<b>Por vigilar</b>")
        for w in brief["watch_next"][:4]:
            if isinstance(w, dict):
                L.append(f"· {esc(w.get('when',''))} — {esc(w.get('what',''))}")
            else:
                L.append(f"· {esc(w)}")
        L.append("")

    if brief.get("contrarian"):
        L.append(f"<b>Contra-argumento</b>\n<i>{esc(brief['contrarian'])}</i>\n")

    if brief.get("learning_note"):
        L.append(f"<b>Concepto del día</b>\n{esc(brief['learning_note'])}\n")

    meta = brief.get("_meta", {})
    L.append(f"<i>{len(items)} fuentes · US${meta.get('cost_usd', 0)}</i>")
    if dashboard_url:
        L.append(f'<a href="{esc(dashboard_url)}">Ver completo con gráficos →</a>')

    return "\n".join(L)


def build_alert(extremos: list[dict], dashboard_url=None) -> str:
    L = ["<b>⚠️ Movimiento extremo detectado</b>", ""]
    for q in extremos[:6]:
        L.append(f"<b>{esc(q['name'])}</b>: {q['chg_1d']:+.2f}% "
                 f"— {abs(q['z']):.1f} desviaciones estándar "
                 f"(vol. anual {q.get('vol_anual')}%)")
    L.append("\n<i>Un |z| ≥ 3 ocurre en menos del 1% de los días. "
             "Vale la pena entender por qué.</i>")
    if dashboard_url:
        L.append(f'\n<a href="{esc(dashboard_url)}">Abrir dashboard →</a>')
    return "\n".join(L)


def split(text: str, limit: int = LIMIT) -> list[str]:
    """Corta respetando líneas para no partir etiquetas HTML por la mitad."""
    if len(text) <= limit:
        return [text]
    parts, cur = [], ""
    for line in text.split("\n"):
        if len(cur) + len(line) + 1 > limit:
            if cur.strip():
                parts.append(cur.rstrip())
            cur = ""
        cur += line + "\n"
    if cur.strip():
        parts.append(cur.rstrip())
    return parts


def send(text: str, token: str | None = None, chat_id: str | None = None) -> bool:
    token = token or os.environ.get("TELEGRAM_TOKEN")
    chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")
    if not (token and chat_id):
        print("   telegram: sin credenciales, se omite")
        return False
    ok = True
    for chunk in split(text):
        try:
            r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                              timeout=30, json={
                                  "chat_id": chat_id, "text": chunk,
                                  "parse_mode": "HTML",
                                  "disable_web_page_preview": True})
            if not r.ok:
                print(f"   telegram error {r.status_code}: {r.text[:200]}")
                ok = False
        except Exception as exc:  # noqa: BLE001
            print(f"   telegram excepción: {exc}")
            ok = False
    return ok


def test_connection() -> tuple[bool, str]:
    token = os.environ.get("TELEGRAM_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not token:
        return False, "TELEGRAM_TOKEN no está configurado"
    try:
        me = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=15).json()
        if not me.get("ok"):
            return False, f"Token inválido: {me.get('description')}"
        name = me["result"]["username"]
        if not chat:
            return False, f"Bot @{name} responde, pero falta TELEGRAM_CHAT_ID"
        r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage", timeout=15,
                          json={"chat_id": chat,
                                "text": "✅ <b>Market Radar conectado.</b>\n"
                                        "Si ves este mensaje, Telegram quedó listo.",
                                "parse_mode": "HTML"}).json()
        if r.get("ok"):
            return True, f"Bot @{name} envió el mensaje de prueba correctamente"
        return False, f"El bot existe pero no pudo escribirte: {r.get('description')}. " \
                      "¿Le mandaste /start al bot desde tu celular?"
    except Exception as exc:  # noqa: BLE001
        return False, f"Error de red: {exc}"
