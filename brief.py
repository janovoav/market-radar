"""Capa de síntesis con la API de Claude.

REGLA DE ORO DEL DISEÑO: el modelo no produce cifras.
Precios, variaciones, z-scores y régimen se calculan en Python y se le
entregan hechos. Él interpreta, jerarquiza y conecta causas — nada más.
Cada afirmación sobre una noticia debe apuntar al índice de su fuente.
"""
from __future__ import annotations

import json
import os

import requests

from src.sources.common import log_error

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"

PRICES_USD_PER_MTOK = {          # (input, output)
    "claude-haiku-4-5-20251001": (1.0, 5.0),
    "claude-haiku-4-5": (1.0, 5.0),
    "claude-sonnet-5": (2.0, 10.0),
    "claude-opus-5": (5.0, 25.0),
}

SYSTEM = """Eres el analista jefe de una mesa de inversión de una sola persona.
Escribes el briefing que tu lector revisa antes de tomar decisiones con capital real.

{mandate}

═══ REGLAS INVIOLABLES ═══

1. NUNCA inventes una cifra. Todos los precios, variaciones, z-scores y niveles
   ya vienen calculados en los bloques DATOS. Cítalos textualmente o no los uses.
   Si quieres afirmar algo numérico que no está en los datos, no lo afirmes.

2. Toda afirmación derivada de una noticia lleva el índice de su fuente: [3].
   Si no puedes anclarla a un índice del listado, no la escribas.

3. Cada punto sigue la cadena completa:
      QUÉ PASÓ (hecho verificable)
      → POR QUÉ IMPORTA (el mecanismo económico, no el adjetivo)
      → IMPLICACIÓN (qué activo, en qué dirección, bajo qué condición)
   Un titular sin mecanismo no se publica. Si no entiendes el mecanismo, omite
   la noticia; es preferible un briefing corto a uno relleno.

4. Distingue siempre HECHO de INTERPRETACIÓN. Marca la interpretación como tal
   ("lectura:", "si esto se sostiene..."). Nunca las mezcles en la misma frase.

5. Di explícitamente cuándo algo YA ESTABA DESCONTADO por el mercado. El valor
   del briefing está en la sorpresa frente al consenso, no en el evento.

6. Nunca des una recomendación de comprar o vender. Das implicaciones y la
   condición que te haría cambiar de opinión.

7. Español de Colombia, registro técnico y sobrio. Prohibidos los verbos de
   prensa ("se desplomó", "se disparó", "histórico"). Cuantifica o calla.

8. Si el día fue irrelevante, dilo en el titular y escribe poco. Un briefing
   honesto y corto vale más que uno inflado.

═══ FORMATO DE SALIDA ═══
Responde ÚNICAMENTE con este JSON. Sin markdown, sin ``` y sin preámbulo.

{{
  "headline": "una frase: lo único que un inversionista necesita saber de hoy",
  "subhead": "una o dos frases que amplían el titular con el dato que lo sostiene",
  "regime_read": "tu lectura del régimen. Parte de la clasificación cuantitativa que recibiste; si la matizas, explica por qué",
  "sections": [
    {{
      "title": "Macro, tasas y bancos centrales",
      "items": [
        {{
          "fact": "qué pasó, con la cifra exacta de los datos si aplica",
          "why": "el mecanismo: por qué esto mueve precios",
          "implication": "qué activo se ve afectado y en qué dirección",
          "priced_in": "si ya estaba descontado, dilo aquí; si no, deja el campo vacío",
          "sources": [1, 4]
        }}
      ]
    }}
  ],
  "price_action": "Explica los movimientos de precio del día que MERECEN explicación: los anómalos y los grandes. Conecta con las noticias donde haya relación causal plausible, y di explícitamente cuándo un movimiento NO tiene explicación en el flujo de noticias.",
  "what_changed": "Qué es distinto hoy frente a la narrativa que el mercado traía. Si nada cambió, escríbelo tal cual.",
  "cross_asset": "Coherencias o contradicciones entre clases de activos. Ejemplo: acciones suben pero el crédito se amplía. Las contradicciones suelen ser la parte más informativa del día.",
  "colombia": "Lectura específica de Colombia: COP, TES, riesgo país, local. Vacío si no hubo nada relevante.",
  "watch_next": [
    {{"when": "fecha o ventana", "what": "evento o dato concreto", "why": "qué se juega en ese dato"}}
  ],
  "contrarian": "El argumento más fuerte que iría en contra de la lectura dominante de hoy",
  "learning_note": "Un concepto técnico que aparezca hoy en el flujo, explicado en 2-3 frases, útil para alguien preparando AMV/CFA"
}}

SECCIONES DISPONIBLES (usa solo las que tengan contenido real, en este orden):
"Macro, tasas y bancos centrales", "Renta variable", "Renta fija y crédito",
"Divisas", "Commodities", "Cripto", "Colombia y LatAm",
"Geopolítica y política", "Corporativo, IPOs y M&A", "Regulación"

Máximo 4 ítems por sección. Omite las secciones vacías en lugar de rellenarlas."""


def build_payload(items, quotes, macro, movers, regime, curve, ipos, calendar) -> str:
    """Arma el mensaje del usuario: primero los datos duros, luego las noticias."""
    L: list[str] = []

    L.append("═══ RÉGIMEN (clasificación cuantitativa, calculada con reglas fijas) ═══")
    L.append(f"Etiqueta: {regime['label']}  ·  score: {regime['score']}")
    L.append("Señales: " + "; ".join(regime["signals"]))

    L.append("\n═══ MOVIMIENTOS ANÓMALOS (z-score vs. volatilidad de 60 días) ═══")
    L.append("Un |z| >= 2 significa que el movimiento es estadísticamente inusual "
             "para ESE activo. Estos son los que merecen explicación:")
    if movers["anomalos"]:
        for q in movers["anomalos"]:
            L.append(f"  {q['name']}: {q['chg_1d']:+.2f}% (z={q['z']:+.1f}, "
                     f"vol.anual {q.get('vol_anual')}%) [{q['bucket']}]")
    else:
        L.append("  Ninguno. El día fue estadísticamente normal en todo el universo.")

    L.append("\n─ Mayores subidas ─")
    for q in movers["subidas"]:
        L.append(f"  {q['name']}: {q['chg_1d']:+.2f}% (z={q.get('z')})")
    L.append("─ Mayores bajadas ─")
    for q in movers["bajadas"]:
        L.append(f"  {q['name']}: {q['chg_1d']:+.2f}% (z={q.get('z')})")

    L.append("\n═══ MERCADOS (cifras verificadas — úsalas tal cual) ═══")
    by_bucket: dict[str, list] = {}
    for q in quotes:
        if q.get("ok") and q.get("last") is not None:
            by_bucket.setdefault(q["bucket"], []).append(q)
    labels = {"indices": "Índices", "etfs_regionales": "ETFs regionales",
              "etfs_sectoriales": "Sectores", "renta_fija": "Renta fija",
              "commodities": "Commodities", "fx": "Divisas",
              "acciones_vigiladas": "Acciones", "crypto": "Cripto"}
    for bucket, rows in by_bucket.items():
        L.append(f"\n— {labels.get(bucket, bucket)} —")
        for q in rows:
            L.append(f"  {q['name']}: {q['last']} | 1d {_f(q.get('chg_1d'))} | "
                     f"5d {_f(q.get('chg_5d'))} | 1m {_f(q.get('chg_1m'))} | "
                     f"YTD {_f(q.get('chg_ytd'))} | desde máx 52s {_f(q.get('pct_from_high'))}")

    if macro:
        L.append("\n═══ MACRO Y TASAS (FRED) ═══")
        for m in macro:
            L.append(f"  {m['name']}: {m['last']}{m['unit']} | 1d {m['chg_1d']:+} {m['delta_unit']} | "
                     f"1m {m['chg_1m']:+} {m['delta_unit']} | 1a {m['chg_1y']:+} {m['delta_unit']} "
                     f"(al {m['as_of']})")

    if curve:
        L.append("\n─ Estructura de la curva ─")
        L.append(f"  {json.dumps(curve, ensure_ascii=False)}")

    if ipos:
        L.append("\n═══ MERCADO PRIMARIO (IPOs, Nasdaq) ═══")
        for x in ipos[:10]:
            L.append(f"  [{x['status']}] {x.get('company')} ({x.get('ticker')}) "
                     f"{x.get('date') or ''} {x.get('size') or ''} {x.get('exchange') or ''}")

    if calendar:
        L.append("\n═══ CALENDARIO PRÓXIMO ═══")
        for c in calendar:
            L.append(f"  {c['date']}: {c['event']}")

    L.append("\n═══ NOTICIAS (cita por índice: [n]) ═══")
    for i, it in enumerate(items, 1):
        extra = f" ·confirmada en {it['n_sources']} fuentes" if it.get("n_sources", 1) > 1 else ""
        L.append(f"[{i}] ({it['source']} · {it.get('topic')}{extra}) {it['title']}")
        if it.get("summary"):
            L.append(f"     {it['summary'][:280]}")

    return "\n".join(L)


def _f(v) -> str:
    return f"{v:+.2f}%" if isinstance(v, (int, float)) else "n/d"


REQUIRED_KEYS = ["headline", "sections"]


def validate(brief: dict) -> list[str]:
    """Verifica que la respuesta del modelo tenga la forma esperada."""
    problems = []
    for k in REQUIRED_KEYS:
        if k not in brief:
            problems.append(f"falta la clave '{k}'")
    for sec in brief.get("sections", []):
        if "title" not in sec:
            problems.append("sección sin título")
        for it in sec.get("items", []):
            if not it.get("fact"):
                problems.append(f"ítem sin 'fact' en {sec.get('title')}")
    return problems


def generate(payload: str, cfg: dict, model: str, api_key: str | None = None) -> dict:
    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("Falta ANTHROPIC_API_KEY. Revisa el paso 4 de la guía.")

    body = {
        "model": model,
        "max_tokens": cfg["model"]["max_tokens"],
        "temperature": cfg["model"].get("temperature", 0.3),
        "system": SYSTEM.format(mandate=cfg["owner"]["mandate"]),
        "messages": [{"role": "user", "content": payload}],
    }
    r = requests.post(API_URL, timeout=300, json=body, headers={
        "x-api-key": key, "anthropic-version": API_VERSION,
        "content-type": "application/json"})

    if r.status_code != 200:
        raise RuntimeError(f"API respondió {r.status_code}: {r.text[:400]}")

    data = r.json()
    text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    brief = parse_json_response(text)

    usage = data.get("usage", {})
    brief["_meta"] = {
        "model": model,
        "input_tokens": usage.get("input_tokens", 0),
        "output_tokens": usage.get("output_tokens", 0),
        "cost_usd": estimate_cost(model, usage),
    }
    problems = validate(brief)
    if problems:
        log_error("brief_schema", "; ".join(problems))
        brief["_meta"]["schema_warnings"] = problems
    return brief


def parse_json_response(text: str) -> dict:
    """Tolerante a que el modelo envuelva el JSON en ``` pese a las instrucciones."""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        t = t.rsplit("```", 1)[0]
    t = t.strip().removeprefix("json").strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        start, end = t.find("{"), t.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(t[start:end + 1])
            except json.JSONDecodeError:
                pass
    return {"headline": "No se pudo interpretar la respuesta del modelo",
            "subhead": "El texto crudo quedó guardado para revisión.",
            "sections": [], "_raw": text[:4000]}


def estimate_cost(model: str, usage: dict) -> float:
    pin, pout = PRICES_USD_PER_MTOK.get(model, (2.0, 10.0))
    return round(usage.get("input_tokens", 0) / 1e6 * pin
                 + usage.get("output_tokens", 0) / 1e6 * pout, 5)
