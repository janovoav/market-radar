# Guía de instalación — paso a paso

Sin conocimientos técnicos previos. Tiempo total: **45 a 60 minutos**, una sola vez.
Después de esto, el sistema corre solo para siempre.

Haz los pasos **en orden**. Al final de cada uno hay una forma de verificar que quedó bien.

---

## Antes de empezar

Necesitas:
- Un computador (tu EliteBook sirve)
- Tu iPhone
- Un correo Gmail
- Unos 10 minutos de paciencia con la parte de las claves

Vas a crear cuentas en 4 servicios. **Tres son completamente gratis.** Solo uno cobra,
y cobra centavos: la API de Claude.

---

# PASO 1 — Instalar Python (10 min)

Python es el lenguaje en el que está escrito el sistema. Tu computador necesita tenerlo.

1. Entra a **python.org/downloads**
2. Clic en el botón amarillo grande que dice "Download Python 3.13" (o la versión que aparezca)
3. Abre el archivo descargado
4. **⚠️ MUY IMPORTANTE:** en la primera pantalla del instalador, marca la casilla que dice
   **"Add Python to PATH"** antes de darle a Install. Si no la marcas, nada va a funcionar
   después y tendrás que desinstalar y repetir.
5. Clic en "Install Now" y espera

### Verificar que quedó bien
Abre **PowerShell** (busca "PowerShell" en el menú de inicio de Windows) y escribe:

```
python --version
```

Debe responder algo como `Python 3.13.1`. Si dice "no se reconoce el comando", Python no
quedó en el PATH: desinstala y repite el paso 4.

---

# PASO 2 — Crear la cuenta de GitHub y subir el proyecto (10 min)

GitHub es donde va a vivir el código y desde donde se va a ejecutar solo. Es gratis.

## 2.1 Crear la cuenta
1. Entra a **github.com** → "Sign up"
2. Usa tu correo, crea un usuario (por ejemplo `janovoa`) y una contraseña
3. Verifica tu correo

## 2.2 Crear el repositorio
1. Arriba a la derecha, clic en el **+** → "New repository"
2. Nombre: `market-radar`
3. Marca **Private** (privado — nadie más lo ve)
4. **No** marques ninguna de las casillas de abajo (README, .gitignore, license)
5. Clic en "Create repository"

## 2.3 Subir los archivos
GitHub te muestra una página con instrucciones. Ignórala y haz esto:

1. Clic en el link que dice **"uploading an existing file"**
   (o entra a `github.com/TU-USUARIO/market-radar/upload/main`)
2. Arrastra **todas las carpetas y archivos** del proyecto a esa ventana
3. Espera a que suban (verás una lista de archivos)
4. Abajo, escribe "primera versión" y clic en **"Commit changes"**

### Verificar
Entra a `github.com/TU-USUARIO/market-radar`. Debes ver las carpetas `src`, `docs`,
`tests` y los archivos `config.yaml`, `README.md`.

---

# PASO 3 — Crear el bot de Telegram (5 min)

Este es el que te va a mandar los mensajes al celular. **Gratis e ilimitado.**

## 3.1 Instalar Telegram
Si no lo tienes, descarga **Telegram** de la App Store y crea tu cuenta con tu número.

## 3.2 Crear el bot
1. En Telegram, busca **@BotFather** (con la palomita azul de verificado)
2. Escríbele `/newbot`
3. Te pide un nombre → escribe `Market Radar`
4. Te pide un usuario → debe terminar en `bot`, por ejemplo `janovoa_radar_bot`
   (si está ocupado, prueba otro)
5. Te responde con un mensaje que contiene algo así:

   ```
   Use this token to access the HTTP API:
   8123456789:AAHk3lPq9vNx-2Zm4RtY7uWs1DcFgHj5KlM
   ```

6. **Copia ese código largo y guárdalo.** Ese es tu `TELEGRAM_TOKEN`.

## 3.3 Obtener tu ID de chat
1. En Telegram busca **@userinfobot**
2. Escríbele cualquier cosa, por ejemplo `hola`
3. Te responde con tu `Id:` seguido de un número, por ejemplo `1234567890`
4. **Ese número es tu `TELEGRAM_CHAT_ID`.** Guárdalo.

## 3.4 Paso que todo el mundo olvida
1. Busca **tu propio bot** en Telegram (el nombre que le pusiste, ej. `@janovoa_radar_bot`)
2. Ábrelo y presiona **START** (o escríbele `/start`)

Esto es obligatorio: un bot de Telegram **no puede escribirte primero** si tú nunca le
hablaste. Si te saltas esto, el sistema va a funcionar pero nunca te va a llegar nada.

---

# PASO 4 — Obtener la clave de Claude (5 min) — el único costo

1. Entra a **console.anthropic.com**
2. Crea una cuenta (puedes usar la misma de Claude)
3. Ve a **Settings → Billing** y carga un saldo mínimo (US$5 es más que suficiente:
   te va a durar 2 o 3 meses)
4. Ve a **API Keys** → "Create Key" → ponle de nombre `market-radar`
5. **Copia la clave inmediatamente** (empieza con `sk-ant-...`). Solo se muestra una vez.

> **Sobre el costo:** con Sonnet 5 y dos briefings diarios, gastas entre **US$3 y US$5 al
> mes** (≈12.000–20.000 COP). Cabe en tu presupuesto. Si prefieres gastar menos, en
> `config.yaml` cambia `daily: "claude-sonnet-5"` por `daily: "claude-haiku-4-5-20251001"`
> y baja a ~US$1,5/mes, con un análisis algo menos fino.

---

# PASO 5 — Clave de FRED (2 min) — gratis

FRED es la base de datos de la Reserva Federal. De ahí salen las tasas de interés.

1. Entra a **fredaccount.stlouisfed.org/apikeys**
2. Crea una cuenta (solo correo y contraseña)
3. Clic en "Request API Key", escribe cualquier descripción ("uso personal")
4. Copia la clave que te dan

---

# PASO 6 — Contraseña de aplicación de Gmail (5 min)

Gmail no te deja usar tu contraseña normal en programas. Hay que crear una especial.

1. Entra a **myaccount.google.com/security**
2. Si no tienes **verificación en dos pasos** activada, actívala primero (es obligatorio)
3. Busca **"Contraseñas de aplicaciones"** (o entra a
   `myaccount.google.com/apppasswords`)
4. Escribe un nombre: `Market Radar`
5. Google te da una contraseña de **16 letras** en 4 grupos, ej. `abcd efgh ijkl mnop`
6. **Cópiala sin los espacios**: `abcdefghijklmnop`

> Si no encuentras la opción, es porque falta activar la verificación en dos pasos.

---

# PASO 7 — Guardar las claves en GitHub (5 min)

Ahora le vas a dar las claves a GitHub para que el robot las use. Van en un lugar
cifrado: nadie puede verlas, ni siquiera tú después de guardarlas.

1. Entra a tu repositorio en GitHub
2. **Settings** (arriba, en la barra del repositorio, no el de tu perfil)
3. En el menú izquierdo: **Secrets and variables → Actions**
4. Botón verde **"New repository secret"**
5. Crea uno por uno, así:

| Name (exacto, en mayúsculas) | Secret (el valor) |
|---|---|
| `ANTHROPIC_API_KEY` | tu clave `sk-ant-...` del paso 4 |
| `FRED_API_KEY` | la clave del paso 5 |
| `TELEGRAM_TOKEN` | el código largo del paso 3.2 |
| `TELEGRAM_CHAT_ID` | tu número del paso 3.3 |
| `SMTP_USER` | tu correo completo, ej. `juanchonovoavillarreal@gmail.com` |
| `SMTP_PASS` | los 16 caracteres del paso 6, **sin espacios** |
| `EMAIL_TO` | tu correo otra vez |

> ⚠️ Los nombres deben ir **exactamente** así, en mayúsculas y con guiones bajos.
> `Anthropic_Api_Key` no funciona.

### Verificar
Debes ver 7 secretos en la lista. Los valores aparecen ocultos: es correcto.

---

# PASO 8 — Publicar el dashboard (3 min)

1. En tu repositorio: **Settings → Pages** (menú izquierdo)
2. En "Source" elige **"Deploy from a branch"**
3. Branch: **main**, y en la carpeta elige **`/docs`**
4. Clic en **Save**
5. Espera 1–2 minutos y recarga la página. Aparecerá:
   `Your site is live at https://TU-USUARIO.github.io/market-radar/`
6. **Copia esa dirección**

Ahora guárdala en GitHub:
1. **Settings → Secrets and variables → Actions**
2. Pestaña **"Variables"** (no "Secrets") → "New repository variable"
3. Name: `DASHBOARD_URL` · Value: la dirección que copiaste

---

# PASO 9 — Instalar el dashboard en tu iPhone (2 min)

1. Abre **Safari** en el iPhone (tiene que ser Safari, no Chrome)
2. Entra a `https://TU-USUARIO.github.io/market-radar/`
3. Toca el botón **Compartir** (el cuadrito con la flecha hacia arriba)
4. Desliza y toca **"Añadir a pantalla de inicio"**
5. Ponle el nombre `Radar` y toca "Añadir"

Ahora tienes el ícono en tu pantalla de inicio. Al abrirlo se ve a pantalla completa,
sin barra de navegador. Parece una app nativa aunque no pasó por la App Store.

---

# PASO 10 — La primera corrida (3 min)

1. En tu repositorio, pestaña **Actions** (arriba)
2. Si aparece un aviso pidiendo habilitar los workflows, acéptalo
3. En el menú izquierdo, clic en **"Briefing"**
4. A la derecha, botón **"Run workflow"** → deja "diario" → clic en el botón verde

Espera de 3 a 5 minutos. Vas a ver un punto amarillo que gira, luego una palomita verde.

### Qué debe pasar
- Te llega un mensaje a Telegram
- Te llega un correo
- El dashboard en tu iPhone ya muestra el briefing

Si el círculo sale **rojo**, clic en la corrida → clic en el paso que falló → lee el
mensaje de error. La sección "Problemas comunes" del README cubre los casos frecuentes.

---

# PASO 11 — Confirmar que quedó automatizado

No tienes que hacer nada más. El sistema ahora corre solo:

| Cuándo | Qué llega |
|---|---|
| Lunes a viernes, 5:45 a.m. | Briefing de pre-apertura |
| Lunes a viernes, 4:30 p.m. | Briefing de cierre de Nueva York |
| Sábados, 8:00 a.m. | Resumen semanal (análisis más profundo) |
| Cuando algo se mueva de forma extrema | Alerta inmediata en la siguiente corrida |

Para cambiar los horarios, edita las líneas `cron` en
`.github/workflows/briefing.yml`. Recuerda que están en hora UTC:
**hora de Colombia + 5 = hora UTC**.

---

# Opcional — Correrlo en tu computador

Solo si quieres probar cosas sin esperar a la corrida automática.

Abre PowerShell y escribe, línea por línea:

```powershell
cd Downloads\market-radar
pip install -r requirements.txt
python -m src.run demo
```

El comando `demo` genera un briefing de ejemplo **sin gastar un peso**. Crea dos archivos
que puedes abrir para ver cómo se verá todo:
- `demo_email.html` — ábrelo con doble clic, así se verá el correo
- `demo_telegram.txt` — así se verá el mensaje de Telegram

Para una corrida real desde tu computador necesitas las claves en un archivo `.env`
(copia `.env.example`, renómbralo a `.env` y llena los valores).

---

# Los tres comandos que vale la pena conocer

| Comando | Para qué |
|---|---|
| `python -m src.run demo` | Ver cómo se ve todo, sin costo |
| `python -m src.run check` | Diagnóstico: qué fuentes y claves funcionan |
| `python -m src.run run --dry` | Ver exactamente qué datos recibiría la IA, sin llamarla |

El más útil de los tres es `check`. Córrelo cada dos o tres meses: los feeds de noticias
se rompen sin avisar y `check` te dice cuáles hay que reemplazar.
