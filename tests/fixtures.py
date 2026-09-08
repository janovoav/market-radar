"""Datos simulados realistas. Se usan en `demo` y en los tests, para poder
verificar todo el sistema sin red y sin gastar en la API."""
from __future__ import annotations

import math
import random


def _series(start: float, n: int = 90, drift: float = 0.0004, vol: float = 0.01, seed: int = 1):
    rng = random.Random(seed)
    out, v = [], start
    for _ in range(n):
        v *= (1 + drift + rng.gauss(0, vol))
        out.append(round(v, 4))
    return out


def _quote(name, bucket, last, chg_1d, region="", vol=0.01, seed=1, z=None):
    ser = _series(last * 0.93, 90, vol=vol, seed=seed)
    ser[-1] = last
    rets = [(ser[i] / ser[i - 1] - 1) * 100 for i in range(1, len(ser))]
    return {
        "ticker": name.lower()[:6], "name": name, "bucket": bucket, "region": region,
        "ok": True, "last": last, "as_of": "2026-09-08",
        "chg_1d": chg_1d, "chg_5d": round(chg_1d * 1.7, 2),
        "chg_1m": round(chg_1d * 2.4, 2), "chg_ytd": round(chg_1d * 8, 2),
        "high_52w": round(max(ser) * 1.02, 2), "low_52w": round(min(ser) * 0.98, 2),
        "pct_from_high": round(-abs(chg_1d) * 2.2, 2),
        "returns": rets, "series": ser,
        "z": z if z is not None else round(chg_1d / (vol * 100), 2),
        "vol_anual": round(vol * 100 * math.sqrt(252), 1),
        "anomalo": abs(z if z is not None else chg_1d / (vol * 100)) >= 2,
        "extremo": abs(z if z is not None else chg_1d / (vol * 100)) >= 3,
    }


def demo_quotes():
    return [
        _quote("S&P 500", "indices", 6482.31, -1.42, "EEUU", 0.008, 1, z=-1.9),
        _quote("Nasdaq 100", "indices", 23150.8, -2.10, "EEUU", 0.011, 2, z=-2.1),
        _quote("VIX", "indices", 21.4, 18.6, "Volatilidad", 0.06, 3, z=3.2),
        _quote("DAX", "indices", 19840.2, -0.62, "Alemania", 0.009, 4, z=-0.7),
        _quote("Emergentes (EEM)", "etfs_regionales", 48.9, -1.05, "EM", 0.010, 5, z=-1.1),
        _quote("Colombia (GXG)", "etfs_regionales", 28.4, -1.85, "Colombia", 0.013, 6, z=-1.4),
        _quote("Semiconductores", "etfs_sectoriales", 288.5, -3.40, "Sector", 0.016, 7, z=-2.4),
        _quote("Energía", "etfs_sectoriales", 92.1, 1.20, "Sector", 0.011, 8, z=1.1),
        _quote("UST 20y+ (TLT)", "renta_fija", 88.6, -0.95, "Duración", 0.007, 9, z=-1.5),
        _quote("Corp HY (HYG)", "renta_fija", 79.2, -0.42, "HY", 0.004, 10, z=-1.2),
        _quote("Petróleo WTI", "commodities", 68.4, 2.85, "Energía", 0.018, 11, z=1.7),
        _quote("Oro", "commodities", 3412.5, 0.95, "Metal", 0.009, 12, z=1.1),
        _quote("Cobre", "commodities", 4.31, -1.60, "Metal", 0.013, 13, z=-1.3),
        _quote("Café", "commodities", 3.15, 4.20, "Agrícola", 0.020, 14, z=2.2),
        _quote("USD/COP", "fx", 4012.5, 0.82, "Colombia", 0.006, 15, z=1.4),
        _quote("DXY", "fx", 99.8, 0.35, "Dólar", 0.004, 16, z=0.9),
        _quote("EUR/USD", "fx", 1.0912, -0.28, "G10", 0.004, 17, z=-0.7),
        _quote("USD/BRL", "fx", 5.42, 0.61, "LatAm", 0.007, 18, z=0.9),
        _quote("NVIDIA", "acciones_vigiladas", 168.4, -4.80, "Mega cap", 0.020, 19, z=-2.5),
        _quote("Ecopetrol", "acciones_vigiladas", 9.82, 1.45, "Colombia", 0.014, 20, z=1.0),
        _quote("BTC", "crypto", 108420.0, -3.60, "Cripto", 0.028, 21, z=-1.3),
        _quote("ETH", "crypto", 4180.5, -4.90, "Cripto", 0.033, 22, z=-1.5),
    ]


def demo_macro():
    return [
        {"id": "DGS10", "name": "UST 10 años", "unit": "%", "last": 4.28, "as_of": "2026-09-05",
         "chg_1d": 7.0, "chg_1m": -14.0, "chg_1y": 32.0, "delta_unit": "pb",
         "series": _series(4.1, 90, drift=0.0002, vol=0.008, seed=31)},
        {"id": "DGS2", "name": "UST 2 años", "unit": "%", "last": 3.71, "as_of": "2026-09-05",
         "chg_1d": 4.0, "chg_1m": -9.0, "chg_1y": -18.0, "delta_unit": "pb",
         "series": _series(3.6, 90, vol=0.007, seed=32)},
        {"id": "T10Y2Y", "name": "Pendiente 10y-2y", "unit": "%", "last": 0.57,
         "as_of": "2026-09-05", "chg_1d": 3.0, "chg_1m": -5.0, "chg_1y": 50.0,
         "delta_unit": "pb", "series": _series(0.5, 90, vol=0.02, seed=33)},
        {"id": "T10YIE", "name": "Breakeven 10y", "unit": "%", "last": 2.34,
         "as_of": "2026-09-05", "chg_1d": 2.0, "chg_1m": 4.0, "chg_1y": 11.0,
         "delta_unit": "pb", "series": _series(2.3, 90, vol=0.005, seed=34)},
        {"id": "DFII10", "name": "Tasa real 10y", "unit": "%", "last": 1.94,
         "as_of": "2026-09-05", "chg_1d": 5.0, "chg_1m": -18.0, "chg_1y": 21.0,
         "delta_unit": "pb", "series": _series(1.9, 90, vol=0.008, seed=35)},
        {"id": "BAMLH0A0HYM2", "name": "Spread HY EEUU", "unit": "%", "last": 3.12,
         "as_of": "2026-09-05", "chg_1d": 9.0, "chg_1m": 22.0, "chg_1y": -14.0,
         "delta_unit": "pb", "series": _series(3.0, 90, vol=0.012, seed=36)},
    ]


def demo_items():
    base = [
        ("La Fed mantiene tasas y Powell condiciona el recorte de diciembre a dos IPC seguidos por debajo de 2,6%",
         "Fed · comunicados", 1, "macro"),
        ("Nóminas no agrícolas suben 142.000 frente a 165.000 esperadas; revisión a la baja de los dos meses previos",
         "WSJ · Economía", 1, "macro"),
        ("NVIDIA cae tras reportar márgenes por debajo de guía pese a superar en ingresos",
         "Reuters (GNews)", 1, "markets"),
        ("Banco de la República mantiene la tasa en 8,50% con votación dividida 4-3",
         "Banrep (GNews)", 1, "colombia"),
        ("Ministerio de Hacienda amplía el cupo de emisión de TES para el cierre fiscal de 2026",
         "Valora Analitik", 2, "colombia"),
        ("OPEP+ aplaza el aumento de producción hasta el primer trimestre",
         "Geopolítica", 2, "geopolitica"),
        ("Café arábica sube por heladas en el sur de Brasil",
         "Commodities", 2, "commodities"),
        ("Flujos netos de ETF de bitcoin al contado se vuelven negativos por cuarta sesión",
         "Cripto", 2, "crypto"),
        ("Fintech latinoamericana presenta el S-1 para salir al Nasdaq buscando US$600 millones",
         "SEC · registros S-1", 1, "ipos"),
        ("El Tesoro coloca 10 años con demanda débil: ratio bid-to-cover en mínimo de 18 meses",
         "Bloomberg (GNews)", 1, "markets"),
        ("Spreads de alto rendimiento se amplían 9 pb, el mayor movimiento diario desde abril",
         "MarketWatch", 2, "markets"),
        ("Moody's revisa a estable la perspectiva de la banca colombiana",
         "La República", 2, "colombia"),
    ]
    return [{
        "title": t, "url": f"https://ejemplo.com/noticia-{i+1}",
        "summary": "Resumen de ejemplo con el contexto de la noticia para efectos de demostración.",
        "published": None, "source": s, "tier": tier, "topic": topic,
        "n_sources": 2 if i % 4 == 0 else 1, "score": round(18 - i * 1.1, 2),
    } for i, (t, s, tier, topic) in enumerate(base)]


DEMO_BRIEF = {
    "headline": "El mercado descuenta menos recortes y el ajuste llega por la tasa real, no por la inflación esperada",
    "subhead": "El 10 años sube 7 pb con el breakeven casi quieto (+2 pb): el movimiento es de tasa real. "
               "Semiconductores y cripto absorben el golpe; el crédito HY se amplía 9 pb, que es la señal a vigilar.",
    "regime_read": "La clasificación cuantitativa marca risk-off y los datos la sostienen: VIX +18,6% (z 3,2), "
                   "spread HY +9 pb y dólar al alza. Lo matizo en un punto: el oro sube 0,95% al tiempo que la "
                   "tasa real sube 5 pb, combinación poco habitual que sugiere cobertura por evento más que "
                   "rotación defensiva clásica.",
    "sections": [
        {"title": "Macro, tasas y bancos centrales", "items": [
            {"fact": "La Fed mantuvo tasas y condicionó el recorte de diciembre a dos lecturas de IPC seguidas por debajo de 2,6%.",
             "why": "Convierte una decisión discrecional en una regla observable: el mercado ahora puede repreciar la probabilidad de recorte con cada dato, en vez de con cada discurso.",
             "implication": "Sube la sensibilidad de la curva corta a los datos de inflación. Las dos próximas publicaciones de IPC pesan más que cualquier intervención verbal.",
             "priced_in": "El mantenimiento estaba plenamente descontado; la condición explícita no lo estaba.",
             "sources": [1]},
            {"fact": "Nóminas en 142.000 frente a 165.000 esperadas, con revisión a la baja de los dos meses anteriores.",
             "why": "La revisión importa más que el dato: sugiere que el mercado laboral venía más débil de lo que se creía cuando se tomaron decisiones previas.",
             "implication": "Argumento a favor de la parte corta de la curva, pero el 2 años solo cedió 4 pb: el mercado le está dando más peso a la inflación que al empleo.",
             "priced_in": "", "sources": [2]},
            {"fact": "La colocación de 10 años del Tesoro salió con bid-to-cover en mínimo de 18 meses.",
             "why": "Demanda débil en el primario obliga a los dealers a absorber inventario, y ese inventario se cubre vendiendo duración en el secundario.",
             "implication": "Explica buena parte de los 7 pb del 10 años sin necesidad de invocar un cambio de expectativas de inflación.",
             "priced_in": "", "sources": [10]},
        ]},
        {"title": "Renta variable", "items": [
            {"fact": "NVIDIA cae 4,80% (z -2,5) tras reportar márgenes por debajo de guía pese a superar en ingresos.",
             "why": "Cuando la tesis de una acción es expansión de márgenes, superar en ingresos no compensa fallar en márgenes. El mercado castiga el numerador equivocado.",
             "implication": "El arrastre lleva a semiconductores a -3,40% (z -2,4). Es el canal que explica la caída del Nasdaq frente al S&P.",
             "priced_in": "", "sources": [3]},
        ]},
        {"title": "Renta fija y crédito", "items": [
            {"fact": "Los spreads de alto rendimiento se ampliaron 9 pb, el mayor movimiento diario desde abril.",
             "why": "El crédito suele anticipar al equity porque el acreedor cobra antes de que el accionista pierda. Una ampliación con acciones cayendo es confirmación, no divergencia.",
             "implication": "Si mañana el equity rebota pero el spread sigue ampliándose, la señal del crédito manda. Es el indicador a vigilar esta semana.",
             "priced_in": "", "sources": [11]},
        ]},
        {"title": "Colombia y LatAm", "items": [
            {"fact": "Banrep mantuvo la tasa en 8,50% con votación dividida 4-3.",
             "why": "Una votación 4-3 señala que el consenso interno es frágil: bastaría un miembro para cambiar la dirección en la próxima reunión.",
             "implication": "Reduce la convicción sobre la trayectoria de la tasa local y sube la prima por incertidumbre en la parte corta de la curva TES.",
             "priced_in": "El mantenimiento estaba descontado; la división del voto no.", "sources": [4]},
            {"fact": "Hacienda amplió el cupo de emisión de TES para el cierre fiscal.",
             "why": "Más oferta de papel con la misma demanda presiona los rendimientos al alza, con independencia de la política monetaria.",
             "implication": "Presión de oferta sobre la parte larga de la curva TES. El COP se debilitó 0,82%, coherente con esta lectura.",
             "priced_in": "", "sources": [5]},
        ]},
        {"title": "Commodities", "items": [
            {"fact": "Café arábica sube 4,20% (z 2,2) por heladas en el sur de Brasil.",
             "why": "Choque de oferta en un cultivo con reposición lenta: el árbol dañado no se reemplaza en un ciclo.",
             "implication": "Relevante para los términos de intercambio de Colombia y para la balanza cafetera, aunque el efecto agregado sobre el COP es de segundo orden frente al petróleo.",
             "priced_in": "", "sources": [7]},
        ]},
    ],
    "price_action": "Tres movimientos merecen explicación y uno no la tiene. El VIX (+18,6%, z 3,2) y semiconductores "
                    "(-3,40%, z -2,4) se explican por NVIDIA. El café (+4,20%, z 2,2) por el choque de oferta en Brasil. "
                    "El que no tiene explicación clara en el flujo de noticias es el oro (+0,95%) subiendo con tasa real "
                    "al alza: normalmente se mueven en direcciones opuestas, y no encuentro en las fuentes de hoy un "
                    "evento que lo justifique. Lo dejo señalado sin explicación inventada.",
    "what_changed": "Hasta ayer la narrativa dominante era recorte en diciembre casi asegurado. La condición explícita "
                    "de Powell no elimina el recorte pero lo vuelve dependiente de datos verificables, y eso reprecia "
                    "la volatilidad implícita de la curva corta. Ese es el cambio real del día.",
    "cross_asset": "Hay coherencia casi total: equity abajo, crédito ampliándose, dólar arriba, VIX arriba. La única "
                   "pieza fuera de sitio es el oro subiendo con tasa real al alza. Cuando todo confirma menos un activo, "
                   "ese activo suele ser el que está anticipando algo distinto — o el que está siendo comprado por un "
                   "motivo ajeno al ciclo.",
    "colombia": "Doble presión sobre los activos locales: externa vía dólar fuerte y tasas USD al alza, e interna vía "
                "mayor oferta de TES y una decisión de Banrep con consenso frágil. El COP a 4.012,5 (+0,82%) y GXG "
                "-1,85% son consistentes. La revisión de perspectiva de Moody's a la banca es el único dato en contra.",
    "watch_next": [
        {"when": "11 de septiembre", "what": "IPC de EE.UU.",
         "why": "Es la primera de las dos lecturas que Powell puso como condición explícita. Un dato por encima de 2,6% saca el recorte de diciembre de la mesa."},
        {"when": "Esta semana", "what": "Comportamiento del spread HY",
         "why": "Si sigue ampliándose mientras el equity rebota, el crédito estaría anticipando deterioro que las acciones aún no reconocen."},
        {"when": "Próxima subasta de TES", "what": "Demanda ante el cupo ampliado",
         "why": "Mide si el mercado local absorbe la mayor oferta sin exigir prima adicional."},
    ],
    "contrarian": "La lectura dominante es que el mercado está repreciando menos recortes. El argumento en contra: "
                  "el 2 años solo cedió 4 pb y el breakeven se movió 2 pb. Si de verdad se estuvieran quitando recortes, "
                  "el movimiento debería concentrarse en la parte corta y no en la real de 10 años. Es igual de "
                  "consistente con una historia puramente técnica de oferta de papel — subasta débil, cupo ampliado — "
                  "que se disipa en días y no cambia nada estructural.",
    "learning_note": "Descomposición de la tasa nominal: tasa nominal = tasa real + inflación implícita (breakeven). "
                     "Hoy el 10 años subió 7 pb con breakeven +2 pb y tasa real +5 pb, o sea que ~70% del movimiento "
                     "es real. Distinguirlo importa porque una subida por inflación esperada y una por tasa real "
                     "afectan de forma opuesta a los activos reales y a las acciones de crecimiento. Es una pregunta "
                     "recurrente en el módulo de renta fija del AMV.",
    "_meta": {"model": "demo (sin API)", "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0},
}


def demo_bundle():
    from src import config as cfg_mod
    from src.analyze import quant
    cfg = cfg_mod.load()
    quotes = demo_quotes()
    macro = demo_macro()
    return {
        "brief": DEMO_BRIEF,
        "items": demo_items(),
        "quotes": quotes,
        "macro": macro,
        "movers": quant.top_movers(quotes, cfg),
        "regime": quant.classify_regime(quotes, macro),
        "curve": quant.curve_summary(macro),
        "ipos": [
            {"status": "próxima", "company": "LatAm Fintech Corp", "ticker": "LATF",
             "date": "2026-09-15", "size": "$600,000,000", "price": "$18-21", "exchange": "NASDAQ"},
            {"status": "colocada", "company": "Nordic Grid AB", "ticker": "NGRD",
             "date": "2026-09-04", "size": "$310,000,000", "price": "$24", "exchange": "NYSE"},
        ],
        "calendar": [
            {"date": "2026-09-11", "event": "Consumer Price Index"},
            {"date": "2026-09-16", "event": "Retail Sales"},
            {"date": "2026-09-23", "event": "FOMC Minutes"},
        ],
    }
