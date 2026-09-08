"""
Pruebas del pipeline completo. No usan red ni la API: todo corre con los
datos simulados de fixtures.py.

    python -m tests.test_pipeline

Si esto pasa, el sistema está sano estructuralmente. Lo único que no puede
verificar es que las URL de las fuentes sigan vivas — para eso está
`python -m src.run check`.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

from src import brief as brief_mod
from src import config as cfg_mod
from src.analyze import quant, relevance
from src.deliver import telegram
from src.render import dashboard, mail_html
from src.sources import news
from tests.fixtures import demo_bundle, demo_items, demo_macro, demo_quotes

PASS, FAIL = [], []


def check(name: str, condition: bool, detail: str = "") -> None:
    (PASS if condition else FAIL).append(name)
    icon = "✓" if condition else "✗"
    print(f"  {icon} {name}" + (f"  — {detail}" if detail and not condition else ""))


def section(title: str) -> None:
    print(f"\n{title}")


def main() -> int:
    print("═" * 64)
    print("PRUEBAS DE MARKET RADAR")
    print("═" * 64)

    # ── 1. Configuración ──
    section("1. Configuración")
    cfg = cfg_mod.load()
    check("config.yaml carga sin errores", isinstance(cfg, dict))
    assets = cfg_mod.all_assets(cfg)
    check(f"universo aplanado ({len(assets)} activos)", len(assets) > 50)
    check("todos los activos tienen ticker y nombre",
          all("t" in a and "n" in a for a in assets))
    tickers = [a["t"] for a in assets]
    check("no hay tickers duplicados", len(tickers) == len(set(tickers)),
          f"duplicados: {[t for t in set(tickers) if tickers.count(t) > 1]}")
    urls = [f["u"] for f in cfg["feeds"]]
    check("no hay feeds duplicados", len(urls) == len(set(urls)))
    check("pesos de tier son numéricos",
          all(isinstance(v, float) for v in cfg["scoring"]["tier_weight"].values()))

    # ── 2. Deduplicación de noticias ──
    section("2. Deduplicación de noticias")
    dupes = [
        {"title": "Fed holds rates steady in September meeting", "url": "a", "summary": "",
         "published": None, "source": "Reuters", "tier": 1, "topic": "macro"},
        {"title": "Fed holds rates steady in September meeting!", "url": "b", "summary": "",
         "published": None, "source": "CNBC", "tier": 2, "topic": "macro"},
        {"title": "Oil rises on OPEC decision", "url": "c", "summary": "",
         "published": None, "source": "WSJ", "tier": 1, "topic": "commodities"},
    ]
    deduped = news.dedupe(dupes)
    check("colapsa titulares casi idénticos", len(deduped) == 2, f"quedaron {len(deduped)}")
    fed = next((d for d in deduped if "Fed" in d["title"]), None)
    check("conserva la fuente de mejor tier", fed and fed["source"] == "Reuters")
    check("cuenta el número de fuentes", fed and fed.get("n_sources") == 2)

    # ── 3. Scoring ──
    section("3. Relevancia")
    items = demo_items()
    ranked = relevance.rank(items, cfg)
    check("devuelve items puntuados", all("score" in i for i in ranked))
    check("orden descendente por score",
          all(ranked[i]["score"] >= ranked[i+1]["score"] for i in range(len(ranked)-1)))
    check("respeta el mínimo de score",
          all(i["score"] >= cfg["scoring"]["min_score"] for i in ranked))
    check("respeta el máximo de items", len(ranked) <= cfg["scoring"]["max_items_to_model"])

    noise = [{"title": "Best stocks to buy according to expertos", "summary": "opinion",
              "url": "x", "published": None, "source": "Blog", "tier": 3, "topic": "markets"}]
    check("penaliza el ruido", relevance.rank(noise, cfg) == [])

    fomc = [{"title": "FOMC rate decision: Fed cuts by 25bp", "summary": "cpi inflation",
             "url": "y", "published": None, "source": "Fed", "tier": 1, "topic": "macro"}]
    check("premia lo relevante", relevance.rank(fomc, cfg)[0]["score"] > 15)

    # ── 4. Cuantitativo ──
    section("4. Análisis cuantitativo")
    quotes = quant.enrich(demo_quotes(), cfg)
    macro = demo_macro()
    check("calcula z-score", all(q.get("z") is not None for q in quotes if q.get("ok")))
    check("calcula volatilidad anualizada",
          all(q.get("vol_anual") is not None for q in quotes if q.get("ok")))
    movers = quant.top_movers(quotes, cfg)
    for key in ("subidas", "bajadas", "anomalos", "extremos", "mayor_magnitud"):
        check(f"movers['{key}'] existe", key in movers)
    check("las subidas son positivas", all(q["chg_1d"] >= 0 for q in movers["subidas"][:3]))
    check("las bajadas son negativas", all(q["chg_1d"] <= 0 for q in movers["bajadas"][:3]))
    check("detecta anómalos por |z|>=2",
          all(abs(q["z"]) >= cfg["movers"]["z_alert"] for q in movers["anomalos"]))
    check("los extremos son subconjunto de los anómalos",
          all(q in movers["anomalos"] for q in movers["extremos"]))

    regime = quant.classify_regime(quotes, macro)
    check("clasifica el régimen",
          regime["label"] in ("risk-on", "risk-off", "mixto", "sin dirección"))
    check("el régimen trae señales explicables", len(regime["signals"]) >= 3)
    check("los datos demo dan risk-off", regime["label"] == "risk-off",
          f"dio {regime['label']} con score {regime['score']}")

    curve = quant.curve_summary(macro)
    check("resume la curva", "10y" in curve and "pendiente_10y2y" in curve)
    check("descompone el 10 años", "descomposicion_10y" in curve)

    # ── 5. Payload al modelo ──
    section("5. Payload del modelo")
    payload = brief_mod.build_payload(ranked, quotes, macro, movers, regime, curve, [], [])
    check("incluye el bloque de régimen", "RÉGIMEN" in payload)
    check("incluye movimientos anómalos", "ANÓMALOS" in payload)
    check("incluye cifras verificadas", "6482.31" in payload)
    check("indexa las noticias", "[1]" in payload and f"[{len(ranked)}]" in payload)
    check("tamaño razonable (<60k chars)", len(payload) < 60000, f"{len(payload)} chars")
    print(f"     payload: {len(payload)} caracteres ≈ {len(payload)//4} tokens "
          f"≈ US${len(payload)/4/1e6*2:.4f} de entrada con Sonnet 5")

    # ── 6. Parseo de la respuesta ──
    section("6. Parseo de la respuesta del modelo")
    ok_json = '{"headline":"a","sections":[]}'
    check("parsea JSON limpio", brief_mod.parse_json_response(ok_json)["headline"] == "a")
    check("parsea JSON envuelto en ```",
          brief_mod.parse_json_response('```json\n' + ok_json + '\n```')["headline"] == "a")
    check("parsea JSON con texto alrededor",
          brief_mod.parse_json_response('Aquí tienes:\n' + ok_json)["headline"] == "a")
    broken = brief_mod.parse_json_response("esto no es json")
    check("no explota con respuesta inválida", "headline" in broken and "_raw" in broken)
    check("valida el esquema",
          brief_mod.validate({"sections": []}) == ["falta la clave 'headline'"])
    cost = brief_mod.estimate_cost("claude-sonnet-5",
                                   {"input_tokens": 1_000_000, "output_tokens": 100_000})
    check("calcula costo correctamente", abs(cost - 3.0) < 1e-6, f"dio {cost}, esperaba 3.0")

    # ── 7. Render Telegram ──
    section("7. Mensaje de Telegram")
    d = demo_bundle()
    msg = telegram.build_message(d["brief"], d["items"], d["quotes"], d["movers"],
                                 d["regime"], cfg, "https://ej.github.io/mr/")
    check("incluye el titular", d["brief"]["headline"][:30] in msg)
    check("incluye links a fuentes", 'href="https://ejemplo.com/noticia-1"' in msg)
    check("incluye la cinta de precios", "<pre>" in msg)
    check("escapa caracteres HTML peligrosos", "<script" not in msg)
    parts = telegram.split(msg)
    check("divide mensajes largos correctamente", all(len(p) <= 4000 for p in parts),
          f"partes: {[len(p) for p in parts]}")
    check("no pierde contenido al dividir",
          abs(sum(len(p) for p in parts) - len(msg)) < len(parts) * 2)
    print(f"     mensaje: {len(msg)} caracteres en {len(parts)} parte(s)")

    alert = telegram.build_alert(d["movers"]["extremos"] or d["movers"]["anomalos"][:2])
    check("genera alerta de extremos", "desviaciones estándar" in alert)

    # ── 8. Render correo ──
    section("8. Correo HTML")
    html = mail_html.render(d["brief"], d["items"], d["quotes"], d["macro"],
                            d["movers"], d["regime"], d["ipos"], d["calendar"],
                            "https://ej.github.io/mr/")
    check("HTML bien formado", html.startswith("<!DOCTYPE html>") and html.endswith("</html>"))
    check("incluye sparklines SVG", "<svg" in html and "polyline" in html)
    check("incluye la lista de fuentes", "https://ejemplo.com/noticia-1" in html)
    check("no depende de recursos externos", "http://" not in html.replace("http://www.w3", ""))
    spark = mail_html.sparkline([1, 2, 3, 2, 4])
    check("sparkline genera puntos", "points=" in spark)
    check("sparkline maneja series vacías", mail_html.sparkline([]) == "")
    print(f"     correo: {len(html)} caracteres")

    # ── 9. Dashboard ──
    section("9. Datos del dashboard")
    with tempfile.TemporaryDirectory() as tmp:
        payload_out = dashboard.write(d["brief"], d["items"], d["quotes"], d["macro"],
                                      d["movers"], d["regime"], d["curve"], d["ipos"],
                                      d["calendar"], [], tmp)
        check("escribe latest.json", os.path.exists(os.path.join(tmp, "latest.json")))
        check("escribe index.json", os.path.exists(os.path.join(tmp, "index.json")))
        with open(os.path.join(tmp, "latest.json"), encoding="utf-8") as fh:
            loaded = json.load(fh)
        check("el JSON es válido y completo",
              all(k in loaded for k in ("brief", "quotes", "macro", "items", "regime")))
        check("las cotizaciones conservan la serie para graficar",
              any(q.get("series") for q in loaded["quotes"]))
        check("no serializa los retornos crudos (peso innecesario)",
              all("returns" not in q for q in loaded["quotes"]))
        # segunda corrida: el índice debe crecer
        dashboard.write(d["brief"], d["items"], d["quotes"], d["macro"], d["movers"],
                        d["regime"], d["curve"], d["ipos"], d["calendar"], [], tmp)
        with open(os.path.join(tmp, "index.json"), encoding="utf-8") as fh:
            check("el archivo histórico acumula", len(json.load(fh)) == 2)
        size_kb = os.path.getsize(os.path.join(tmp, "latest.json")) / 1024
        check("tamaño del JSON razonable (<600 KB)", size_kb < 600, f"{size_kb:.0f} KB")
        print(f"     latest.json: {size_kb:.0f} KB")

    # ── 10. Robustez ──
    section("10. Robustez ante datos faltantes")
    broken_quotes = [{"name": "Roto", "ok": False, "last": None, "bucket": "indices"}]
    check("enrich tolera activos sin datos",
          quant.enrich(broken_quotes, cfg) is not None)
    check("top_movers tolera lista vacía",
          quant.top_movers([], cfg)["subidas"] == [])
    check("classify_regime tolera datos vacíos",
          quant.classify_regime([], [])["label"] in ("sin dirección", "mixto"))
    check("curve_summary tolera macro vacío", quant.curve_summary([]) == {})
    empty_brief = {"headline": "Nada", "sections": []}
    check("telegram tolera brief mínimo",
          len(telegram.build_message(empty_brief, [], [], {"anomalos": []},
                                     {"label": "mixto", "signals": []}, cfg)) > 0)

    # ── Resumen ──
    print("\n" + "═" * 64)
    total = len(PASS) + len(FAIL)
    if FAIL:
        print(f"✗ {len(FAIL)} de {total} pruebas FALLARON:")
        for f in FAIL:
            print(f"    · {f}")
        return 1
    print(f"✓ Las {total} pruebas pasaron. El sistema está sano.")
    print("═" * 64)
    return 0


if __name__ == "__main__":
    sys.exit(main())
