# Market Radar

Sistema personal de inteligencia de mercados. Recolecta noticias y precios de todo el
espectro transable, filtra por relevancia con reglas explícitas, sintetiza con Claude y
entrega tres cosas: un mensaje de Telegram, un correo con gráficos y un dashboard web que
se instala como app en el iPhone.

**Infraestructura: US$0.** Único costo: la API del modelo, US$3–5 al mes.

👉 **¿Primera vez? Empieza por [GUIA_INSTALACION.md](GUIA_INSTALACION.md).**

---

## Qué entrega, exactamente

Cada briefing tiene esta estructura, y cada punto sigue la misma cadena:

```
   QUÉ PASÓ          hecho verificable, con la cifra exacta
       ↓
   POR QUÉ IMPORTA   el mecanismo económico — no el adjetivo
       ↓
   IMPLICACIÓN       qué activo, en qué dirección, bajo qué condición
       ↓
   ¿YA DESCONTADO?   si el mercado ya lo tenía, se dice explícitamente
```

Además de las secciones por clase de activo, cada briefing incluye:

- **Régimen del día** — risk-on / risk-off clasificado con una regla numérica explícita
  (S&P, VIX, spread HY, oro, dólar, emergentes), no con la intuición del modelo
- **Movimientos inusuales** — detectados por z-score contra la volatilidad propia de cada
  activo. Un 2% en el S&P y un 2% en bitcoin no son lo mismo, y el sistema lo sabe
- **Lectura del movimiento de precios** — explica los movimientos que merecen explicación,
  y dice explícitamente cuáles *no* tienen explicación en el flujo de noticias
- **Qué cambió** — la diferencia frente a la narrativa que el mercado traía
- **Coherencia entre activos** — cuando el crédito contradice al equity, eso es la noticia
- **Contra-argumento** — el mejor caso en contra de la lectura del día
- **Concepto del día** — un tema técnico del flujo explicado, orientado a AMV/CFA

---

## Arquitectura

```
        cron de GitHub Actions  (gratis, 2 corridas diarias + 1 semanal)
                      │
      ┌───────────────┴────────────────┐
      │        RECOLECCIÓN             │   todas las fuentes son gratuitas
      ├────────────────────────────────┤
      │ 28 feeds RSS/Atom  → Fed, BCE, BIS, FMI, SEC, FT, WSJ, Economist,
      │                       Valora, Portafolio, La República, + GNews
      │ Stooq              → ~65 activos: índices, sectores, regiones,
      │                       renta fija, commodities, FX, acciones
      │ FRED               → 12 series: curva UST, breakevens, spreads
      │ CoinGecko          → 5 criptoactivos
      │ Nasdaq             → calendario de IPOs
      └───────────────┬────────────────┘
                      │
      ┌───────────────┴────────────────┐
      │     ANÁLISIS DETERMINISTA      │   verificable, sin IA
      ├────────────────────────────────┤
      │ · z-score de cada activo vs. su volatilidad de 60 días
      │ · clasificación de régimen por regla numérica
      │ · descomposición de la tasa nominal en real + breakeven
      │ · scoring de relevancia: ~500 titulares → 55
      └───────────────┬────────────────┘
                      │
      ┌───────────────┴────────────────┐
      │      SÍNTESIS CON CLAUDE       │
      │  recibe las cifras YA hechas;  │
      │  interpreta y conecta, no      │
      │  calcula ni inventa            │
      └───────────────┬────────────────┘
                      │
      ┌───────┬───────┴───────┬────────┐
   Telegram  Correo      Dashboard PWA
   (push)   (archivo)    (iPhone + web)
```

### La regla de diseño que sostiene todo

**El modelo no produce cifras.** Precios, variaciones, z-scores, régimen y curva se
calculan en Python y se le entregan hechos. Él interpreta, jerarquiza y conecta causas.
Cada afirmación sobre una noticia debe apuntar al índice de su fuente, que se convierte
en link real. Si no puede anclarla, no la escribe.

Es el fallo que vuelve inútil a la mayoría de los "resúmenes con IA": una cifra plausible
pero inventada contamina todo el análisis. Aquí es estructuralmente imposible.

---

## Uso diario

Ninguno. El sistema corre solo. Estos comandos son para cuando quieras intervenir:

| Comando | Qué hace | Costo |
|---|---|---|
| `python -m src.run demo` | Briefing de ejemplo con datos simulados | US$0 |
| `python -m src.run check` | Diagnóstico de fuentes y credenciales | US$0 |
| `python -m src.run check --email` | Además envía un correo de prueba | US$0 |
| `python -m src.run run --dry` | Muestra qué recibiría el modelo, sin llamarlo | US$0 |
| `python -m src.run run --local` | Briefing real, sin enviarlo | ~US$0,05 |
| `python -m src.run run` | Corrida completa | ~US$0,05 |
| `python -m src.run run --weekly` | Ventana de 7 días, modelo escalado | ~US$0,25 |
| `python -m tests.test_pipeline` | 67 pruebas del sistema | US$0 |

---

## Ajuste fino — todo en `config.yaml`

**`owner.mandate`** — el campo más importante. Define cómo piensa el analista: qué le
importa, en qué orden, y qué lo aburre. Cámbialo cuando cambie tu enfoque y todo el
briefing cambia con él.

**`scoring.keywords`** — el volante de la relevancia. ¿El briefing trae ruido? Baja un
peso. ¿Se te escapó algo importante? Súbelo. **Nunca toques el prompt para arreglar
relevancia**: se arregla aquí, es auditable, es reversible y no rompe nada más.

**`universe`** — agrega o quita activos. Verifica cualquier ticker nuevo en
`stooq.com/q/?s=TICKER` antes de agregarlo.

**`movers.z_alert`** — qué tan raro debe ser un movimiento para marcarlo. En 2.0 verás
unos 3–6 por día; en 2.5, uno o dos.

**`model.daily`** — `claude-sonnet-5` (recomendado) o `claude-haiku-4-5-20251001` (más
barato, análisis algo menos fino).

---

## Costos reales

| Componente | Costo mensual |
|---|---|
| GitHub Actions (~8 min/día de los 2.000 min/mes gratis) | US$0 |
| GitHub Pages (dashboard) | US$0 |
| Telegram Bot API | US$0, sin límite |
| Gmail SMTP (500 correos/día) | US$0 |
| Stooq, FRED, CoinGecko, RSS, Nasdaq | US$0 |
| **API de Claude — Sonnet 5, ~45 corridas** | **US$3–5** |
| **API de Claude — Haiku 4.5** | **US$1,5–2** |

≈ **12.000–20.000 COP al mes** con Sonnet 5. Cabe en tu presupuesto de 30.000.

El costo exacto de cada corrida se imprime en el log, viaja dentro del JSON y aparece al
pie del dashboard y del correo. No hay sorpresas a fin de mes.

---

## Problemas comunes

**No me llega nada a Telegram**
→ ¿Le diste `/start` a tu propio bot desde el celular? Un bot no puede escribirte primero.
Corre `python -m src.run check` para confirmarlo.

**El correo no llega**
→ Gmail exige una "Contraseña de aplicación" de 16 caracteres, no tu clave normal. Si no
aparece esa opción, falta activar la verificación en dos pasos.

**El workflow falla con error 401 de Anthropic**
→ La clave está mal copiada o no hay saldo en la cuenta. Revisa
`console.anthropic.com → Billing`.

**Varias fuentes marcan FALLA en `check`**
→ Normal con el tiempo: los RSS cambian de dirección. Reemplaza la URL en `config.yaml` o
comenta la línea con `#`. Con que funcione el 60% de los feeds, el briefing sale bien.

**El dashboard dice "Todavía no hay briefings"**
→ Aún no ha corrido el workflow, o GitHub Pages tarda un par de minutos en publicar los
cambios. Espera y recarga.

**Un activo aparece siempre sin datos**
→ El ticker de Stooq está mal. Búscalo en `stooq.com/q/?s=TICKER` y corrígelo.

---

## Limitaciones que debes conocer

- El cron de GitHub Actions **se retrasa entre 5 y 15 minutos** en horas pico. Sirve para
  briefings programados, no para alertas intradía en tiempo real.
- Los feeds de FT, WSJ y Bloomberg entregan **titular y bajada, no el artículo completo**.
  El análisis se construye sobre esa base.
- Stooq publica **precios de cierre con rezago**, no cotización en vivo.
- El endpoint de IPOs de Nasdaq **no es una API contractual**: puede cambiar sin aviso. Si
  falla, el pipeline continúa y lo reporta.
- El modelo puede equivocarse en la **interpretación**, aunque no en las cifras. Las
  secciones "Contra-argumento" y "¿ya descontado?" existen para hacerte dudar
  deliberadamente, no para darte confianza.
- **Esto no es asesoría de inversión.** Es un sistema de recolección y síntesis que
  reduce el tiempo entre "pasó algo" y "entiendo qué significa".

---

## Estructura del proyecto

```
config.yaml               ← todo lo editable vive aquí
GUIA_INSTALACION.md       ← empieza por aquí si es tu primera vez
src/
  config.py               carga y valida la configuración
  sources/
    common.py             reintentos y registro de errores
    news.py               RSS/Atom + deduplicación
    prices.py             Stooq: precios, series históricas, retornos
    market_data.py        FRED, CoinGecko, IPOs, calendario
  analyze/
    quant.py              z-scores, régimen, curva  ← determinista
    relevance.py          scoring de noticias        ← determinista
  brief.py                prompt, llamada a la API, validación de esquema
  deliver/
    telegram.py           formato HTML y envío
    mail.py               SMTP
  render/
    mail_html.py          correo con sparklines SVG
    dashboard.py          JSON + archivo histórico
  run.py                  orquestador (run / check / demo)
tests/
  fixtures.py             datos simulados realistas
  test_pipeline.py        67 pruebas, sin red ni API
docs/                     el dashboard (GitHub Pages sirve esta carpeta)
```
