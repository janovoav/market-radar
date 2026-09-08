"""
Market Radar — orquestador.

  python -m src.run run          corrida completa (recolecta, analiza, envía)
  python -m src.run run --weekly ventana de 7 días y modelo escalado
  python -m src.run run --dry    recolecta y analiza, pero NO llama al modelo
  python -m src.run run --local  genera el briefing real pero no lo envía
  python -m src.run check        diagnóstico: qué fuentes y credenciales funcionan
  python -m src.run demo         genera un briefing de ejemplo sin gastar un peso
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

from src import brief as brief_mod
from src import config as cfg_mod
from src.analyze import quant, relevance
from src.deliver import mail, telegram
from src.render import dashboard, mail_html
from src.sources import market_data, news
from src.sources import prices as prices_mod
from src.sources.common import ERRORS, clear_errors

ROOT = cfg_mod.ROOT
DATA_DIR = os.path.join(ROOT, "docs", "data")


# ═══════════════════════════ CORRIDA ═══════════════════════════
def collect_all(cfg: dict, lookback_hours: int) -> dict:
    print("→ Noticias…", end=" ", flush=True)
    t = time.time()
    raw_news = news.fetch(cfg["feeds"], lookback_hours)
    print(f"{len(raw_news)} titulares únicos ({time.time()-t:.0f}s)")

    print("→ Precios…", end=" ", flush=True)
    t = time.time()
    assets = cfg_mod.all_assets(cfg)
    quotes = prices_mod.fetch_universe(assets)
    ok = sum(1 for q in quotes if q.get("ok"))
    print(f"{ok}/{len(assets)} activos ({time.time()-t:.0f}s)")

    print("→ Cripto, macro, IPOs, calendario…", end=" ", flush=True)
    quotes += market_data.fetch_crypto(cfg["universe"].get("crypto", []))
    macro = market_data.fetch_macro(cfg["fred_series"], os.environ.get("FRED_API_KEY"))
    ipos = market_data.fetch_ipos()
    calendar = market_data.fetch_calendar()
    print(f"{len(macro)} series macro, {len(ipos)} IPOs, {len(calendar)} eventos")

    return {"news": raw_news, "quotes": quotes, "macro": macro,
            "ipos": ipos, "calendar": calendar}


def analyze_all(data: dict, cfg: dict) -> dict:
    quotes = quant.enrich(data["quotes"], cfg)
    movers = quant.top_movers(quotes, cfg)
    regime = quant.classify_regime(quotes, data["macro"])
    curve = quant.curve_summary(data["macro"])
    items = relevance.rank(data["news"], cfg)
    print(f"→ Análisis: régimen {regime['label']} (score {regime['score']}), "
          f"{len(movers['anomalos'])} movimientos anómalos, "
          f"{len(items)} noticias seleccionadas")
    return {"quotes": quotes, "movers": movers, "regime": regime,
            "curve": curve, "items": items}


def cmd_run(args) -> int:
    clear_errors()
    cfg = cfg_mod.load()
    t0 = time.time()

    data = collect_all(cfg, 168 if args.weekly else args.lookback)
    an = analyze_all(data, cfg)

    payload = brief_mod.build_payload(
        an["items"], an["quotes"], data["macro"], an["movers"],
        an["regime"], an["curve"], data["ipos"], data["calendar"])

    if args.dry:
        print("\n" + "=" * 70)
        print(payload)
        print("=" * 70)
        print(f"\nTamaño del payload: {len(payload)} caracteres "
              f"(~{len(payload)//4} tokens, costo estimado de entrada "
              f"US${len(payload)/4/1e6*2:.4f} con Sonnet 5)")
        _print_errors()
        return 0

    model = cfg["model"]["weekly"] if args.weekly else cfg["model"]["daily"]
    print(f"→ Generando briefing con {model}…")
    b = brief_mod.generate(payload, cfg, model)
    meta = b.get("_meta", {})
    print(f"   «{b.get('headline','')}»")
    print(f"   {meta.get('input_tokens')} tok entrada, {meta.get('output_tokens')} tok salida "
          f"→ US${meta.get('cost_usd')}")

    dash_url = os.environ.get("DASHBOARD_URL")

    if cfg["delivery"]["dashboard"]:
        dashboard.write(b, an["items"], an["quotes"], data["macro"], an["movers"],
                        an["regime"], an["curve"], data["ipos"], data["calendar"],
                        ERRORS, DATA_DIR)
        print(f"   dashboard: docs/data/latest.json escrito")

    if args.local:
        print("\n--- modo local: no se envía nada ---")
        print(json.dumps(b, ensure_ascii=False, indent=2)[:2500])
        _print_errors()
        return 0

    if cfg["delivery"]["telegram"]:
        msg = telegram.build_message(b, an["items"], an["quotes"], an["movers"],
                                     an["regime"], cfg, dash_url)
        print(f"   telegram: {'enviado' if telegram.send(msg) else 'FALLÓ'}")
        if cfg["delivery"].get("send_movers_alert") and an["movers"]["extremos"]:
            telegram.send(telegram.build_alert(an["movers"]["extremos"], dash_url))
            print(f"   telegram: alerta de {len(an['movers']['extremos'])} movimientos extremos")

    if cfg["delivery"]["email"]:
        html = mail_html.render(b, an["items"], an["quotes"], data["macro"],
                                an["movers"], an["regime"], data["ipos"],
                                data["calendar"], dash_url)
        prefix = "Market Radar semanal" if args.weekly else "Market Radar"
        sent = mail.send(f"{prefix} · {b.get('headline','')[:90]}", html)
        print(f"   email: {'enviado' if sent else 'FALLÓ'}")

    print(f"\n✓ Corrida completa en {time.time()-t0:.0f}s")
    _print_errors()
    return 0


def _print_errors() -> None:
    if not ERRORS:
        print("Sin errores de fuentes.")
        return
    print(f"\n{len(ERRORS)} fuente(s) con problemas (el pipeline continuó):")
    for e in ERRORS[:20]:
        print(f"   · {e['source']}: {e['error'][:110]}")


# ═══════════════════════════ CHECK ═══════════════════════════
def cmd_check(args) -> int:
    cfg = cfg_mod.load()
    print("═" * 62)
    print("DIAGNÓSTICO DE MARKET RADAR")
    print("═" * 62)

    print("\n1. CREDENCIALES")
    creds = [("ANTHROPIC_API_KEY", True), ("FRED_API_KEY", False),
             ("TELEGRAM_TOKEN", False), ("TELEGRAM_CHAT_ID", False),
             ("SMTP_USER", False), ("SMTP_PASS", False), ("EMAIL_TO", False),
             ("DASHBOARD_URL", False)]
    for name, required in creds:
        val = os.environ.get(name)
        mark = "✓" if val else ("✗ FALTA (obligatoria)" if required else "– sin configurar")
        shown = f"{val[:6]}…{val[-4:]}" if val and len(val) > 12 else (val or "")
        print(f"   {mark:26} {name} {shown}")

    print("\n2. TELEGRAM")
    ok, msg = telegram.test_connection()
    print(f"   {'✓' if ok else '✗'} {msg}")

    if args.email:
        print("\n3. CORREO")
        ok, msg = mail.test_connection()
        print(f"   {'✓' if ok else '✗'} {msg}")
    else:
        print("\n3. CORREO — omitido (usa --email para enviar una prueba real)")

    print("\n4. FUENTES DE NOTICIAS")
    results = news.check(cfg["feeds"])
    good = [r for r in results if r["status"] == "OK"]
    for r in results:
        icon = "✓" if r["status"] == "OK" else "○" if r["status"] == "VACÍO" else "✗"
        detail = f"{r['entries']} entradas" if r["status"] == "OK" else r.get("error", r["status"])
        print(f"   {icon} {r['name']:26} {detail[:70]}")
    print(f"\n   {len(good)}/{len(results)} feeds funcionando")
    if len(good) < len(results) * 0.6:
        print("   ⚠ Menos del 60% responde. Revisa tu conexión antes de culpar a las fuentes.")

    print("\n5. PRECIOS (muestra)")
    sample = cfg_mod.all_assets(cfg)[:6]
    for q in prices_mod.fetch_universe(sample):
        icon = "✓" if q["ok"] else "✗"
        val = f"{q['last']} ({q.get('chg_1d')}%)" if q["ok"] else "sin datos"
        print(f"   {icon} {q['name']:24} {val}")

    print("\n" + "═" * 62)
    return 0


# ═══════════════════════════ DEMO ═══════════════════════════
def cmd_demo(args) -> int:
    """Genera un briefing de ejemplo con datos simulados. No usa la API,
    no cuesta nada, y sirve para ver exactamente cómo se verá todo."""
    from tests.fixtures import demo_bundle
    cfg = cfg_mod.load()
    d = demo_bundle()

    dashboard.write(d["brief"], d["items"], d["quotes"], d["macro"], d["movers"],
                    d["regime"], d["curve"], d["ipos"], d["calendar"], [], DATA_DIR)

    html = mail_html.render(d["brief"], d["items"], d["quotes"], d["macro"],
                            d["movers"], d["regime"], d["ipos"], d["calendar"],
                            "https://usuario.github.io/market-radar/")
    out = os.path.join(ROOT, "demo_email.html")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(html)

    msg = telegram.build_message(d["brief"], d["items"], d["quotes"], d["movers"],
                                 d["regime"], cfg, "https://usuario.github.io/market-radar/")
    out_tg = os.path.join(ROOT, "demo_telegram.txt")
    with open(out_tg, "w", encoding="utf-8") as fh:
        fh.write(msg)

    print("Demo generado sin usar la API:")
    print(f"   · {out}          → ábrelo en el navegador (así se verá el correo)")
    print(f"   · {out_tg}       → así se verá el mensaje de Telegram")
    print(f"   · docs/data/latest.json  → abre docs/index.html para ver el dashboard")
    if os.environ.get("TELEGRAM_TOKEN") and args.send:
        telegram.send(msg)
        print("   · enviado a Telegram")
    return 0


# ═══════════════════════════ CLI ═══════════════════════════
def main() -> int:
    ap = argparse.ArgumentParser(prog="market-radar")
    sub = ap.add_subparsers(dest="cmd")

    p_run = sub.add_parser("run", help="corrida completa")
    p_run.add_argument("--weekly", action="store_true", help="ventana 7d + modelo escalado")
    p_run.add_argument("--dry", action="store_true", help="no llama al modelo")
    p_run.add_argument("--local", action="store_true", help="genera pero no envía")
    p_run.add_argument("--lookback", type=int, default=24)
    p_run.set_defaults(func=cmd_run)

    p_check = sub.add_parser("check", help="diagnóstico de fuentes y credenciales")
    p_check.add_argument("--email", action="store_true", help="envía correo de prueba")
    p_check.set_defaults(func=cmd_check)

    p_demo = sub.add_parser("demo", help="briefing de ejemplo sin costo")
    p_demo.add_argument("--send", action="store_true", help="además envíalo a Telegram")
    p_demo.set_defaults(func=cmd_demo)

    args = ap.parse_args()
    if not args.cmd:
        ap.print_help()
        return 1
    try:
        return args.func(args)
    except cfg_mod.ConfigError as exc:
        print(f"\n✗ Error de configuración: {exc}")
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"\n✗ Error inesperado: {type(exc).__name__}: {exc}")
        import traceback
        traceback.print_exc()
        return 3


if __name__ == "__main__":
    sys.exit(main())
