# 🎸 Gorillaz Chile – Monitor de Tickets (100% en la nube)

Corre 24/7 en los servidores de **GitHub gratis**, sin necesidad de tener el computador prendido.
Cuando detecta disponibilidad, te manda un mensaje al **celular por Telegram** al instante.

---

## ¿Cómo funciona?

```
GitHub Actions (cada 5 min)
       ↓
  Abre Ticketmaster Chile con Playwright
       ↓
  ¿Hay tickets de Tribuna / Cancha General?
       ↓ SÍ
  Mensaje a tu Telegram 📲
```

---

## 🚀 Configuración paso a paso (~10 minutos)

### Paso 1 – Crear tu Bot de Telegram (2 min)

1. Abre Telegram y busca **@BotFather**
2. Escríbele `/newbot`
3. Ponle un nombre: ej. `Gorillaz Monitor`
4. Ponle un username: ej. `gorillaz_monitor_bot`
5. BotFather te da un **token** que se ve así:
   ```
   7123456789:AAHdqTcvCHhvQSBzklM4gHCyPMThFoWlhyI
   ```
   **Guárdalo**, lo vas a necesitar.

6. Busca tu bot en Telegram y aprieta **Start** (o escríbele `/start`)

### Paso 2 – Obtener tu Chat ID (1 min)

Con el token que te dio BotFather, abre este link en el browser
(reemplaza `TU_TOKEN` con tu token real):

```
https://api.telegram.org/botTU_TOKEN/getUpdates
```

Busca en el resultado el número de `"id"` dentro de `"chat"`. Se ve así:

```json
{"message": {"chat": {"id": 123456789, "first_name": "Juan"}}}
```

Ese número `123456789` es tu **Chat ID**.

### Paso 3 – Crear el repositorio en GitHub (2 min)

1. Ve a [github.com](https://github.com) e inicia sesión (o crea cuenta gratis)
2. Click en **"New repository"** (botón verde)
3. Nombre: `gorillaz-monitor` (o lo que quieras)
4. **Private** ✓ (para que nadie vea tus credenciales)
5. Click **"Create repository"**

### Paso 4 – Subir los archivos (2 min)

**Opción A – Sin git (más fácil):**
1. En tu repo nuevo, click en **"uploading an existing file"**
2. Arrastra todos los archivos de esta carpeta
3. Click **"Commit changes"**

**Opción B – Con git:**
```bash
cd gorillaz-monitor-ticketmaster
git init
git remote add origin https://github.com/TU_USUARIO/gorillaz-monitor.git
git add .
git commit -m "Monitor inicial"
git push -u origin main
```

### Paso 5 – Agregar las credenciales de Telegram (2 min)

En tu repositorio de GitHub:

1. Ve a **Settings** → **Secrets and variables** → **Actions**
2. Click **"New repository secret"**
3. Agrega estos dos secrets:

| Name | Value |
|------|-------|
| `TELEGRAM_TOKEN` | El token que te dio BotFather |
| `TELEGRAM_CHAT_ID` | Tu Chat ID numérico |

### Paso 6 – Activar el monitor (1 min)

1. Ve a la pestaña **Actions** en tu repo
2. Si ves un aviso amarillo "Workflows aren't running", click en **"I understand my workflows, enable them"**
3. Click en **"🎸 Gorillaz Ticket Monitor"** en el panel izquierdo
4. Click en **"Run workflow"** → **"Run workflow"** (para correrlo ya por primera vez)

Recibirás un mensaje de Telegram confirmando que el monitor está activo. 🎉

---

## 📲 Mensajes que vas a recibir

**Al iniciar:**
```
👀 Monitor iniciado – Gorillaz Chile 2026 🎸

Estado actual:
  ❌ Tribuna: agotada
  ❌ Cancha General: agotada

Te avisaré cuando haya cambios.
Chequeando cada 5 minutos 24/7 🔄
```

**Cuando hay tickets:**
```
🚨🎸 ¡GORILLAZ – TICKETS DISPONIBLES!

📍 Zona(s): TRIBUNA

⚡ Compra AHORA antes de que se agoten:
https://www.ticketmaster.cl/event/gorillaz-live-2026-scl-venta-general

🕐 Detectado: 03:42:15 UTC
```

**Si cambia algo sospechoso:**
```
⚠️ Cambio detectado en la página – Gorillaz Chile 2026 🎸

El contenido cambió pero no se confirmaron zonas disponibles.
👉 Revisá manualmente: [link]
```

---

## ⚙️ Personalización

Para cambiar zonas o intervalo, edita `scripts/check_tickets.py`:

```python
# Zonas a vigilar
ZONAS_OBJETIVO = [
    "tribuna",
    "cancha general",
    "cancha",
    "piso",
    "field",
]
```

Para cambiar el intervalo, edita `.github/workflows/monitor.yml`:
```yaml
schedule:
  - cron: "*/5 * * * *"   # cada 5 min (mínimo de GitHub)
  # - cron: "*/10 * * * *"  # cada 10 min
```

---

## ❓ Preguntas frecuentes

**¿Es gratis?**
Sí. GitHub Actions tiene 2000 minutos gratis por mes. Este monitor usa ~4 min cada hora = ~120 min/día, bien dentro del límite.

**¿Cada cuánto chequea?**
Cada 5 minutos (mínimo de GitHub Actions). En la práctica puede variar 1-2 minutos.

**¿Y si GitHub falla?**
Los runs fallidos se reintentan. GitHub tiene 99.9% de uptime. Mucho más confiable que tu computador.

**¿Cómo paro el monitor?**
Ve a Actions → "🎸 Gorillaz Ticket Monitor" → "..." → "Disable workflow".

**¿Puedo monitorear otro evento?**
Cambia la variable `EVENT_URL` en `scripts/check_tickets.py`.

---

## 🔍 Ver los logs

En GitHub → Actions → click en cualquier run → click en "check-tickets" → ves todo lo que hizo el script en detalle.
