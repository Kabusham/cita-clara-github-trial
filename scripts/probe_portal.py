"""Single manual connectivity probe. Does not choose a province or submit a form."""
from playwright.sync_api import sync_playwright

URL = "https://mptmd.sede.gob.es/pagina?id=Extranjeria-cita-previa-extranjeria"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(locale="es-ES", timezone_id="Europe/Madrid")
    try:
        response = page.goto(URL, wait_until="domcontentloaded", timeout=45000)
        print(f"Portal informativo: HTTP {response.status if response else 'sin respuesta'}")
        print(f"Título: {page.title()}")
        link = page.get_by_role("link", name="Acceder al procedimiento")
        if link.count() != 1:
            raise RuntimeError("No se pudo identificar exactamente el enlace oficial de acceso.")
        target = link.get_attribute("href")
        if not target or not target.startswith("https://icp.administracionelectronica.gob.es/"):
            raise RuntimeError("El destino del acceso oficial cambió o no coincide con el dominio esperado.")
        print(f"Enlace oficial ICP+ localizado: {target}")
        try:
            page.goto(target, wait_until="domcontentloaded", timeout=45000)
            text = (page.locator("body").inner_text() or "")[:6000].lower()
            if any(term in text for term in ("captcha", "verifica que eres humano", "comprueba que eres humano", "access denied", "unusual traffic")):
                print("Resultado: el portal requiere intervención humana o ha bloqueado la sesión. No se intentó eludirlo.")
                raise SystemExit(2)
            print(f"Respuesta de ICP+: HTTP {page.url} · título: {page.title()}")
            print("Este resultado solo verifica acceso a la página inicial; no comprueba citas ni disponibilidad.")
        except SystemExit:
            raise
        except Exception as exc:
            print(f"ICP+ no pudo abrirse en esta ejecución: {type(exc).__name__}: {exc}")
            raise SystemExit(1)
    finally:
        browser.close()
