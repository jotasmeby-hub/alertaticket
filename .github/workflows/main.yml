name: 🎵 Monitor de Conciertos

on:
  schedule:
    - cron: "*/5 * * * *"

  workflow_dispatch:
    inputs:
      sector_prueba:
        description: "🧪 Sector inventado para probar la alerta (ej: 'Platea VIP'). Déjalo vacío para correr normal."
        type: string
        default: ""

jobs:
  check-tickets:
    name: Chequear disponibilidad
    runs-on: ubuntu-latest
    timeout-minutes: 4

    steps:
      - name: 📂 Restaurar estado previo
        uses: actions/cache/restore@v4
        with:
          path: estado_previo.json
          key: tm-estado2-${{ github.run_id }}
          restore-keys: tm-estado2-

      - name: 🐍 Configurar Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: 📦 Instalar dependencias
        run: |
          pip install playwright requests
          playwright install chromium --with-deps

      - name: 🔍 Chequear disponibilidad
        env:
          TELEGRAM_TOKEN:   ${{ secrets.TELEGRAM_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
          SECTOR_PRUEBA:    ${{ inputs.sector_prueba }}
        run: |
          python - <<'PYEOF'
          import os, json, asyncio, requests
          from datetime import datetime, timezone, timedelta

          EVENTOS = [
              {
                  "id":               "gorillaz",
                  "nombre":           "Gorillaz Chile 2026 🎸",
                  "url":              "https://www.ticketmaster.cl/event/gorillaz-live-2026-scl-venta-general",
                  "fecha_agotado":    None,
                  "fecha_selector":   None,
                  "sectores_iniciales": {
                      "pit", "pacifico sur", "pacífico sur", "cancha frontal",
                  },
              },
              {
                  "id":               "ironmaiden_31oct",
                  "nombre":           "Iron Maiden 31 Oct 2026 🤘",
                  "url":              "https://www.ticketmaster.cl/event/iron-maiden-run-for-your-lives-scl-2026-venta-general",
                  "fecha_agotado":    "31/10/2026",
                  "fecha_selector":   None,
                  "sectores_iniciales": set(),
              },
              {
                  "id":               "edsheeran",
                  "nombre":           "Ed Sheeran 2026 🎵",
                  "url":              "https://www.ticketmaster.cl/event/ed-sheeran-loop-tour-2026-scl-venta-general",
                  "fecha_agotado":    None,
                  "fecha_selector":   "21/11/2026",
                  "sectores_iniciales": {
                      "pacifico centro", "pacífico centro",
                      "platea zafiro",
                      "pacifico sur", "pacífico sur",
                      "cancha frontal pacifico", "cancha frontal pacífico",
                      "cancha frontal andes",
                      "platea royal", "platea baja",
                      "cancha general", "movilidad reducida",
                  },
              },
              {
                  "id":               "foofighters",
                  "nombre":           "Foo Fighters 2027 🤘",
                  "url":              "https://www.ticketmaster.cl/event/foo-fighters-live-2027-scl-venta-general",
                  "fecha_agotado":    None,
                  "fecha_selector":   None,
                  "sectores_iniciales": set(),
              },
          ]

          TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
          TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
          SECTOR_PRUEBA    = os.environ.get("SECTOR_PRUEBA", "").strip()

          def send_telegram(msg: str) -> bool:
              if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
                  print("  ⚠️  Sin credenciales Telegram")
                  return False
              try:
                  r = requests.post(
                      f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": msg,
                            "parse_mode": "HTML", "disable_web_page_preview": False},
                      timeout=10)
                  r.raise_for_status()
                  print("  ✅ Telegram OK")
                  return True
              except Exception as e:
                  print(f"  ❌ Telegram error: {e}")
                  return False

          def normalizar(texto: str) -> str:
              import unicodedata
              t = unicodedata.normalize("NFKD", texto.lower())
              return "".join(c for c in t if not unicodedata.combining(c)).strip()

          async def seleccionar_fecha(page, fecha: str) -> bool:
              print(f"  🗓  Seleccionando fecha: '{fecha}'")
              for sel in [
                  "text=Selecciona la función", "[class*='dropdown']",
                  "[class*='select']", "[class*='function']", "[class*='arrow']",
              ]:
                  try:
                      el = page.locator(sel).first
                      if await el.is_visible(timeout=2000):
                          await el.click()
                          await asyncio.sleep(2)
                          break
                  except Exception:
                      continue
              for sel in [
                  f"text={fecha}",
                  f"[class*='option']:has-text('{fecha}')",
                  f"li:has-text('{fecha}')",
              ]:
                  try:
                      el = page.locator(sel).first
                      if await el.is_visible(timeout=2000):
                          await el.click()
                          await asyncio.sleep(4)
                          print(f"  ✅ Fecha seleccionada: {fecha}")
                          return True
                  except Exception:
                      continue
              try:
                  await page.get_by_text(fecha, exact=False).first.click()
                  await asyncio.sleep(4)
                  print(f"  ✅ Fecha seleccionada (fallback): {fecha}")
                  return True
              except Exception as e:
                  print(f"  ⚠️  No se pudo seleccionar '{fecha}': {e}")
                  return False

          async def abrir_dropdown_agotado(page) -> bool:
              for sel in [
                  "text=Selecciona la función", "[class*='dropdown']",
                  "[class*='select']", "[class*='arrow']",
              ]:
                  try:
                      el = page.locator(sel).first
                      if await el.is_visible(timeout=2000):
                          await el.click()
                          await asyncio.sleep(2)
                          return True
                  except Exception:
                      continue
              try:
                  await page.get_by_text("Selecciona", exact=False).first.click()
                  await asyncio.sleep(2)
                  return True
              except Exception:
                  pass
              return False

          async def obtener_sectores(url: str, fecha_agotado, fecha_selector) -> list:
              from playwright.async_api import async_playwright
              sectores = []
              async with async_playwright() as pw:
                  browser = await pw.chromium.launch(
                      headless=True,
                      args=["--no-sandbox", "--disable-dev-shm-usage"])
                  ctx = await browser.new_context(
                      user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                                 "Chrome/124.0.0.0 Safari/537.36",
                      locale="es-CL", timezone_id="America/Santiago",
                      viewport={"width": 1440, "height": 900})
                  page = await ctx.new_page()
                  try:
                      await page.goto(url, wait_until="networkidle", timeout=28000)
                  except Exception:
                      try:
                          await page.goto(url, wait_until="domcontentloaded", timeout=28000)
                      except Exception as e:
                          print(f"  ⚠️  Goto falló: {e}")
                  await asyncio.sleep(5)
                  try:
                      if fecha_agotado:
                          await abrir_dropdown_agotado(page)
                          texto       = await page.inner_text("body")
                          texto_lower = texto.lower()
                          fecha_lower = fecha_agotado.lower()
                          print(f"  Buscando fecha: '{fecha_agotado}'")
                          if fecha_lower in texto_lower:
                              idx      = texto_lower.find(fecha_lower)
                              contexto = texto_lower[max(0, idx-80):idx+80]
                              print(f"  Contexto: ...{contexto.strip()}...")
                              if "agotado" in contexto:
                                  print(f"  🔴 {fecha_agotado} sigue agotado")
                              else:
                                  print(f"  🟢 {fecha_agotado} → DISPONIBLE")
                                  sectores.append(f"Fecha habilitada: {fecha_agotado}")
                          else:
                              print(f"  ⚠️  No se encontró '{fecha_agotado}'")

                      elif fecha_selector:
                          await seleccionar_fecha(page, fecha_selector)
                          texto  = await page.inner_text("body")
                          lineas = [l.strip() for l in texto.splitlines() if l.strip()]
                          print(f"  Página cargada: {len(lineas)} líneas")
                          for i, linea in enumerate(lineas):
                              ll = linea.lower().replace(" ", "")
                              if "desde$" in ll and any(c.isdigit() for c in linea):
                                  if i > 0:
                                      nombre = lineas[i-1].strip()
                                      if (2 < len(nombre) < 70
                                              and not nombre.lower().startswith("desde")
                                              and not nombre.startswith("$")):
                                          sectores.append(nombre)
                                          print(f"  ✅ Sector: '{nombre}'")

                      else:
                          texto  = await page.inner_text("body")
                          lineas = [l.strip() for l in texto.splitlines() if l.strip()]
                          print(f"  Página cargada: {len(lineas)} líneas")
                          for i, linea in enumerate(lineas):
                              ll = linea.lower().replace(" ", "")
                              if "desde$" in ll and any(c.isdigit() for c in linea):
                                  if i > 0:
                                      nombre = lineas[i-1].strip()
                                      if (2 < len(nombre) < 70
                                              and not nombre.lower().startswith("desde")
                                              and not nombre.startswith("$")):
                                          sectores.append(nombre)
                                          print(f"  ✅ Sector: '{nombre}'")
                          if not sectores:
                              texto_lower = texto.lower()
                              if any(p in texto_lower for p in ["agotado", "sold out"]):
                                  print("  🔴 Agotado — sin sectores")
                              else:
                                  print("  ⚠️  Sin sectores detectados")

                  except Exception as e:
                      print(f"  ⚠️  Lectura falló: {e}")
                  await browser.close()
              return sectores

          def cargar_estado() -> dict:
              if os.path.exists("estado_previo.json"):
                  try:
                      with open("estado_previo.json") as f:
                          data = json.load(f)
                          print(f"✅ Estado cargado: {list(data.keys())}")
                          return data
                  except Exception:
                      pass
              print("⚠️  Sin estado previo")
              return {}

          def guardar_estado(estado: dict):
              with open("estado_previo.json", "w") as f:
                  json.dump(estado, f, ensure_ascii=False, indent=2)

          # ══════════════════════════════════════════════════════════════════════
          ahora_utc = datetime.now(timezone.utc)
          hora_scl  = ahora_utc - timedelta(hours=4)

          print("=" * 55)
          print(f"  🎵 {ahora_utc.strftime('%Y-%m-%d %H:%M UTC')} ({hora_scl.strftime('%H:%M')} SCL)")
          if SECTOR_PRUEBA:
              print(f"  🧪 MODO PRUEBA — sector: '{SECTOR_PRUEBA}'")
          print("=" * 55)

          estado_global = cargar_estado()
          estado_nuevo  = {}

          for evento in EVENTOS:
              eid            = evento["id"]
              nombre         = evento["nombre"]
              url            = evento["url"]
              fecha_agotado  = evento.get("fecha_agotado")
              fecha_selector = evento.get("fecha_selector")
              si_norm        = {normalizar(s) for s in evento["sectores_iniciales"]}

              print(f"\n{'─'*55}")
              print(f"  {nombre}")
              print(f"{'─'*55}")

              ev_estado    = estado_global.get(eid, {})
              es_baseline  = not ev_estado
              panel_prev   = set(ev_estado.get("sectores_panel", []))
              primer_check = ev_estado.get("primer_check", ahora_utc.isoformat())

              print(f"  baseline={es_baseline} | panel_prev={sorted(panel_prev) or '(vacío)'}")

              sectores    = asyncio.run(obtener_sectores(url, fecha_agotado, fecha_selector))
              panel_ahora = set(sectores)

              if SECTOR_PRUEBA:
                  panel_ahora.add(SECTOR_PRUEBA)
                  print(f"  🧪 Inyectado: '{SECTOR_PRUEBA}'")

              print(f"  Panel ahora: {sorted(panel_ahora) or '(vacío)'}")

              if es_baseline:
                  print("  📌 Baseline guardado — próximo run detectará cambios")
              else:
                  sectores_nuevos    = panel_ahora - panel_prev
                  sectores_perdidos  = panel_prev  - panel_ahora
                  sectores_a_alertar = {
                      s for s in sectores_nuevos
                      if normalizar(s) not in si_norm
                  }

                  print(f"  A alertar: {sorted(sectores_a_alertar) or 'ninguno'}")

                  if sectores_a_alertar:
                      prueba_tag = " <i>(PRUEBA)</i>" if SECTOR_PRUEBA else ""
                      lista = "\n".join(f"  🎟 <b>{s}</b>" for s in sorted(sectores_a_alertar))
                      send_telegram(
                          f"🚨 <b>¡Disponible!{prueba_tag}</b>\n"
                          f"<b>{nombre}</b>\n\n"
                          f"{lista}\n\n"
                          f"⚡ Compra AHORA:\n{url}\n\n"
                          f"🕐 {hora_scl.strftime('%H:%M')} Santiago"
                      )
                      print("  🚨 ALERTA enviada.")
                  else:
                      print("  ✅ Sin cambios.")

                  # No spamear "se agotó" para eventos tipo fecha_agotado
                  if sectores_perdidos and not fecha_agotado:
                      send_telegram(
                          f"😞 <b>Sector se agotó – {nombre}</b>\n"
                          f"Ya no disponible: {', '.join(sorted(sectores_perdidos))}\n"
                          f"Seguimos monitoreando..."
                      )

              # Para eventos fecha_agotado: siempre guardar estado actual
              if fecha_agotado:
                  panel_a_guardar = panel_ahora
              else:
                  panel_a_guardar = set(sectores) if sectores else panel_prev

              estado_nuevo[eid] = {
                  "sectores_panel": list(panel_a_guardar),
                  "primer_check":   primer_check,
                  "ultimo_check":   ahora_utc.isoformat(),
              }

          guardar_estado(estado_nuevo)
          print(f"\n{'='*55}\n  ✅ Listo.\n{'='*55}")
          PYEOF

      - name: 💾 Guardar estado
        uses: actions/cache/save@v4
        if: always()
        with:
          path: estado_previo.json
          key: tm-estado2-${{ github.run_id }}
