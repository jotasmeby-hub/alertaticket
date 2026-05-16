#!/usr/bin/env python3
"""
Ticketmaster Chile – Monitor de disponibilidad
Corre en GitHub Actions cada 5 minutos.
Notifica por Telegram cuando detecta cambios.
"""

import os
import sys
import json
import asyncio
import hashlib
import requests
from datetime import datetime

# ── CONFIG ────────────────────────────────────────────────────────────────────
EVENT_URL   = "https://www.ticketmaster.cl/event/gorillaz-live-2026-scl-venta-general"
EVENT_NAME  = "Gorillaz Chile 2026 🎸"

# Zonas a vigilar (substrings, case-insensitive)
ZONAS_OBJETIVO = [
    "tribuna",
    "cancha general",
    "cancha",
    "piso",
    "field",
    "general",
]

# Palabras que indican que una zona está DISPONIBLE
PALABRAS_DISPONIBLE = [
    "comprar", "buy", "agregar", "add to cart",
    "seleccionar", "disponible", "available",
    "en venta", "on sale",
]

# Palabras que indican que está AGOTADA (descarta falsos positivos)
PALABRAS_AGOTADA = [
    "agotado", "sold out", "no disponible", "unavailable",
    "sin stock", "out of stock",
]

# Credenciales desde variables de entorno (GitHub Secrets)
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
# ─────────────────────────────────────────────────────────────────────────────


def send_telegram(message: str, parse_mode: str = "HTML") -> bool:
    """Envía mensaje por Telegram."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️  TELEGRAM_TOKEN o TELEGRAM_CHAT_ID no configurados.")
        return False
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": parse_mode,
                "disable_web_page_preview": False,
            },
            timeout=10,
        )
        resp.raise_for_status()
        print("✅ Telegram enviado.")
        return True
    except Exception as e:
        print(f"❌ Error Telegram: {e}")
        return False


def check_with_requests() -> dict:
    """
    Intento rápido con requests puro.
    Ticketmaster Chile es una SPA, así que esto solo captura el HTML inicial.
    Aun así puede detectar cambios de estado en meta-tags o scripts embebidos.
    """
    resultado = {"metodo": "requests", "zonas": {}, "html_hash": "", "raw_snippet": ""}
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "es-CL,es;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    try:
        resp = requests.get(EVENT_URL, headers=headers, timeout=20)
        html  = resp.text
        lower = html.lower()

        # Hash del HTML para detectar cualquier cambio
        resultado["html_hash"] = hashlib.md5(html.encode()).hexdigest()

        # Guardar snippet relevante para debug
        idx = lower.find("ticket")
        resultado["raw_snippet"] = html[max(0, idx-200):idx+500] if idx >= 0 else ""

        # Buscar cada zona objetivo
        for zona in ZONAS_OBJETIVO:
            if zona in lower:
                idx_z = lower.find(zona)
                ctx   = lower[max(0, idx_z - 150): idx_z + 300]

                agotada    = any(p in ctx for p in PALABRAS_AGOTADA)
                disponible = any(p in ctx for p in PALABRAS_DISPONIBLE)

                if disponible and not agotada:
                    resultado["zonas"][zona] = "disponible"
                elif agotada:
                    resultado["zonas"][zona] = "agotada"
                else:
                    resultado["zonas"][zona] = "mencionada_sin_contexto"

    except Exception as e:
        print(f"⚠️  requests falló: {e}")

    return resultado


async def check_with_playwright() -> dict:
    """
    Check completo con Playwright: renderiza el JS de la SPA.
    Intercepta las llamadas de API internas para máxima precisión.
    """
    resultado = {"metodo": "playwright", "zonas": {}, "api_calls": [], "page_text": ""}

    try:
        from playwright.async_api import async_playwright, TimeoutError as PWTimeout
    except ImportError:
        print("⚠️  Playwright no disponible.")
        return resultado

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage",
                  "--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="es-CL",
            timezone_id="America/Santiago",
        )

        # Interceptar respuestas JSON de la API interna
        api_responses = []

        async def capturar_response(response):
            url = response.url
            if any(k in url for k in ["getcrowder", "/api/", "/tickets",
                                       "/sections", "/availability",
                                       "/offers", "/event"]):
                try:
                    ct = response.headers.get("content-type", "")
                    if "json" in ct:
                        body = await response.json()
                        api_responses.append({"url": url, "data": body})
                except Exception:
                    pass

        page = await context.new_page()
        page.on("response", capturar_response)

        try:
            await page.goto(EVENT_URL, wait_until="networkidle", timeout=30_000)
        except PWTimeout:
            await page.goto(EVENT_URL, wait_until="domcontentloaded", timeout=30_000)

        # Esperar contenido dinámico
        await asyncio.sleep(5)

        # Texto completo de la página
        try:
            texto = await page.inner_text("body")
            resultado["page_text"] = texto
            lower = texto.lower()

            for zona in ZONAS_OBJETIVO:
                if zona in lower:
                    idx_z = lower.find(zona)
                    ctx   = lower[max(0, idx_z - 200): idx_z + 400]

                    agotada    = any(p in ctx for p in PALABRAS_AGOTADA)
                    disponible = any(p in ctx for p in PALABRAS_DISPONIBLE)

                    if disponible and not agotada:
                        resultado["zonas"][zona] = "disponible"
                    elif agotada:
                        resultado["zonas"][zona] = "agotada"
                    else:
                        resultado["zonas"][zona] = "mencionada"

        except Exception as e:
            print(f"⚠️  inner_text falló: {e}")

        # Analizar respuestas de API capturadas
        resultado["api_calls"] = api_responses
        for api in api_responses:
            texto_api = json.dumps(api["data"], ensure_ascii=False).lower()
            for zona in ZONAS_OBJETIVO:
                if zona in texto_api:
                    idx_z = texto_api.find(zona)
                    ctx   = texto_api[max(0, idx_z - 100): idx_z + 200]
                    if any(p in ctx for p in ["true", "available", "stock", "enabled"]):
                        if not any(p in ctx for p in ["false", "agotado", "0"]):
                            # API dice disponible → máxima confianza
                            resultado["zonas"][f"{zona}"] = "disponible_api"

        await browser.close()

    return resultado


def cargar_estado_previo() -> dict:
    """Lee el estado guardado del run anterior (via archivo en repo o env var)."""
    # GitHub Actions puede pasar el estado como variable de entorno
    estado_json = os.environ.get("ESTADO_PREVIO", "")
    if estado_json:
        try:
            return json.loads(estado_json)
        except Exception:
            pass

    # Fallback: archivo local (útil para pruebas locales)
    if os.path.exists("estado_previo.json"):
        try:
            with open("estado_previo.json") as f:
                return json.load(f)
        except Exception:
            pass

    return {"zonas_disponibles": [], "html_hash": "", "primera_vez": True}


def guardar_estado(estado: dict):
    """Guarda el estado para el próximo run."""
    with open("estado_previo.json", "w") as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)
    # También lo imprime para que GitHub Actions lo pueda capturar como output
    print(f"::set-output name=estado::{json.dumps(estado)}")


def main():
    print("=" * 55)
    print(f"  🎸 TM Monitor — {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"  URL: {EVENT_URL}")
    print("=" * 55)

    estado_previo = cargar_estado_previo()
    primera_vez   = estado_previo.get("primera_vez", True)
    zonas_prev    = set(estado_previo.get("zonas_disponibles", []))
    hash_prev     = estado_previo.get("html_hash", "")

    # ── Check con requests (rápido) ───────────────────────────────────────────
    print("\n📡 Check rápido (requests)...")
    res_req = check_with_requests()
    print(f"   Zonas detectadas: {res_req['zonas']}")
    print(f"   HTML hash: {res_req['html_hash'][:12]}...")

    # ── Check con Playwright (completo) ───────────────────────────────────────
    print("\n🎭 Check completo (Playwright)...")
    res_pw = asyncio.run(check_with_playwright())
    print(f"   Zonas detectadas: {res_pw['zonas']}")
    print(f"   API calls interceptadas: {len(res_pw['api_calls'])}")

    # ── Combinar resultados ───────────────────────────────────────────────────
    zonas_combinadas = {}
    zonas_combinadas.update(res_req["zonas"])
    # Playwright tiene mayor prioridad
    for k, v in res_pw["zonas"].items():
        if v in ("disponible", "disponible_api"):
            zonas_combinadas[k] = v
        elif k not in zonas_combinadas:
            zonas_combinadas[k] = v

    zonas_disponibles_ahora = {
        z for z, s in zonas_combinadas.items()
        if s in ("disponible", "disponible_api")
    }

    print(f"\n✅ Zonas disponibles ahora: {zonas_disponibles_ahora or 'ninguna'}")
    print(f"   Zonas previas:           {zonas_prev or 'ninguna'}")

    # ── Detectar cambios ──────────────────────────────────────────────────────
    zonas_nuevas   = zonas_disponibles_ahora - zonas_prev
    zonas_perdidas = zonas_prev - zonas_disponibles_ahora
    html_cambio    = res_req["html_hash"] != hash_prev and hash_prev != ""

    # ── Notificaciones ────────────────────────────────────────────────────────
    if zonas_nuevas and not primera_vez:
        # 🚨 ALERTA PRINCIPAL: nueva zona disponible
        zonas_str = ", ".join(z.upper() for z in sorted(zonas_nuevas))
        mensaje = (
            f"🚨🎸 <b>¡GORILLAZ – TICKETS DISPONIBLES!</b>\n\n"
            f"📍 Zona(s): <b>{zonas_str}</b>\n\n"
            f"⚡ Compra AHORA antes de que se agoten:\n"
            f"{EVENT_URL}\n\n"
            f"🕐 Detectado: {datetime.now().strftime('%H:%M:%S')} UTC"
        )
        send_telegram(mensaje)
        print(f"\n🚨 ALERTA ENVIADA: {zonas_nuevas}")

    elif primera_vez:
        # Mensaje de inicio
        estado_str = "\n".join(
            f"  {'✅' if s in ('disponible','disponible_api') else '❌'} {z.title()}: {s}"
            for z, s in zonas_combinadas.items()
            if any(obj in z for obj in ZONAS_OBJETIVO)
        ) or "  (no se detectaron zonas objetivo en la página)"

        mensaje = (
            f"👀 <b>Monitor iniciado – {EVENT_NAME}</b>\n\n"
            f"Estado actual:\n{estado_str}\n\n"
            f"Te avisaré cuando haya cambios.\n"
            f"Chequeando cada 5 minutos 24/7 🔄"
        )
        send_telegram(mensaje)
        print("📨 Mensaje de inicio enviado por Telegram.")

    elif html_cambio:
        # Cambio en el HTML pero sin zonas claras → aviso preventivo
        mensaje = (
            f"⚠️ <b>Cambio detectado en la página – {EVENT_NAME}</b>\n\n"
            f"El contenido cambió pero no se confirmaron zonas disponibles.\n"
            f"👉 Revisá manualmente: {EVENT_URL}\n\n"
            f"🕐 {datetime.now().strftime('%H:%M:%S')} UTC"
        )
        send_telegram(mensaje)
        print("⚠️  Cambio de HTML detectado, aviso enviado.")

    else:
        print("✅ Sin cambios. Todo tranquilo.")

    if zonas_perdidas and not primera_vez:
        mensaje = (
            f"😞 <b>Zona(s) volvieron a agotarse – {EVENT_NAME}</b>\n\n"
            f"Zonas: {', '.join(z.upper() for z in zonas_perdidas)}\n"
            f"Seguimos monitoreando..."
        )
        send_telegram(mensaje)

    # ── Guardar estado ────────────────────────────────────────────────────────
    nuevo_estado = {
        "zonas_disponibles": list(zonas_disponibles_ahora),
        "html_hash": res_req["html_hash"],
        "primera_vez": False,
        "ultimo_check": datetime.now().isoformat(),
    }
    guardar_estado(nuevo_estado)

    print("\n" + "=" * 55)
    print(f"  Check completado. Próximo en ~5 min.")
    print("=" * 55)


if __name__ == "__main__":
    main()
