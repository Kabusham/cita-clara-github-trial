"""Comprueba el acceso a la página oficial, sin consultar citas ni enviar datos."""
from urllib.parse import urlparse
from datetime import datetime, timezone
from time import monotonic
import json

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


INFORMATION_URL = "https://mptmd.sede.gob.es/pagina?id=Extranjeria-cita-previa-extranjeria"
OFFICIAL_HOST = "icp.administracionelectronica.gob.es"


def find_official_link(page):
    """Find the ICP+ link by its destination, not by its visible/accessibility name."""
    anchors = page.locator("a").evaluate_all(
        """nodes => nodes.map(a => ({
            href: a.href,
            text: (a.innerText || a.textContent || '').trim()
        }))"""
    )
    targets = {}
    for anchor in anchors:
        href = anchor.get("href", "")
        parsed = urlparse(href)
        if parsed.scheme == "https" and parsed.hostname == OFFICIAL_HOST:
            targets[href] = anchor.get("text", "")

    if len(targets) != 1:
        raise RuntimeError(
            "La página oficial cargó, pero el enlace único de ICP+ no se pudo "
            f"identificar de forma segura (enlaces encontrados: {len(targets)})."
        )
    return next(iter(targets.items()))


def main():
    started = monotonic()
    print("Inicio de comprobación (UTC): " + datetime.now(timezone.utc).isoformat())
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(locale="es-ES", timezone_id="Europe/Madrid")
            response = page.goto(
                INFORMATION_URL, wait_until="domcontentloaded", timeout=45000
            )
            status = response.status if response else "sin respuesta"
            print(f"Portal informativo: HTTP {status}")
            print(f"Título: {page.title()}")
            if response and response.status >= 400:
                raise RuntimeError("La página informativa respondió con un error HTTP.")

            target, label = find_official_link(page)
            print(f"Enlace oficial localizado: {label or '(sin texto visible)'} · {target}")

            parsed = urlparse(target)
            if parsed.scheme != "https" or parsed.hostname != OFFICIAL_HOST:
                raise RuntimeError("El destino ya no coincide con el dominio oficial ICP+.")

            try:
                # `commit` records the initial server response even if the portal
                # keeps loading scripts or never reaches DOMContentLoaded.
                portal_response = page.goto(target, wait_until="commit", timeout=45000)
                portal_status = portal_response.status if portal_response else "sin respuesta"
                print(f"ICP+: respuesta inicial HTTP {portal_status}")
                try:
                    page.wait_for_load_state("domcontentloaded", timeout=15000)
                    fully_loaded = True
                except PlaywrightTimeoutError:
                    fully_loaded = False
                print(f"Título: {page.title() or '(aún no disponible)'}")
                text = (page.locator("body").inner_text(timeout=5000) or "")[:6000].lower()
                if any(
                    term in text
                    for term in (
                        "captcha",
                        "verifica que eres humano",
                        "comprueba que eres humano",
                        "access denied",
                        "unusual traffic",
                    )
                ):
                    print(
                        "Resultado: el portal requiere intervención humana o ha "
                        "bloqueado la sesión. No se intentó eludirlo."
                    )
                    raise SystemExit(2)
                if portal_response and portal_response.status >= 400:
                    raise RuntimeError("ICP+ respondió con un error HTTP.")
                if not fully_loaded:
                    print(
                        "Resultado: ICP+ respondió, pero la página no terminó de "
                        "cargar. No se puede confirmar el acceso al formulario."
                    )
                    raise SystemExit(1)
                # Only read public selection controls before entering any identity data.
                # This provides observed labels/values for subsequent reviewed integration.
                controls = page.locator("select").evaluate_all(
                    """nodes => nodes.map(s => ({
                        id: s.id, name: s.name,
                        options: Array.from(s.options).map(o => ({
                            value: o.value, label: o.text.trim(), disabled: o.disabled
                        }))
                    }))"""
                )
                print("Selectores públicos observados: " + json.dumps(controls, ensure_ascii=False))
                if not controls:
                    print("No se identificaron listas de selección; el formulario sigue sin verificar.")
                print(
                    "Resultado: se comprobó el acceso a la página inicial de ICP+. "
                    "No se consultaron trámites ni disponibilidad de citas."
                )
            except SystemExit:
                raise
            except Exception as exc:
                print(f"ICP+ no pudo abrirse en esta ejecución: {type(exc).__name__}: {exc}")
                raise SystemExit(1)
        finally:
            browser.close()
            print(f"Duración de la comprobación: {monotonic() - started:.1f} segundos")


if __name__ == "__main__":
    main()
