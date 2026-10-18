"""Run reviewed recipes with normal browser controls. No CAPTCHA bypass or booking."""
import json
import re
from datetime import date, datetime
from zoneinfo import ZoneInfo
from urllib.parse import urlparse

ALLOWED_HOSTS = {'icp.administracionelectronica.gob.es', 'citaprevia.administracionelectronica.gob.es', 'sede.administracionespublicas.gob.es'}


class PortalStop(Exception):
    def __init__(self, state, message):
        self.state, self.message = state, message


def load_recipes(path):
    with open(path, encoding='utf-8') as file:
        return json.load(file)


def choose_recipe(recipes, request):
    return next((r for r in recipes if r.get('verified') is True
                 and r['procedure'] == request['type']
                 and (r.get('provinces') == '*' or request['province'] in r.get('provinces', []))), None)


def matching_slots(raw_dates, request, url):
    result = []
    today = datetime.now(ZoneInfo('Europe/Madrid')).date().isoformat()
    lower = max(today, request.get('from') or today)
    upper = request.get('to') or '9999-12-31'
    for value in raw_dates:
        # Read only explicit slot elements from a verified recipe, never whole-page dates.
        match = re.fullmatch(r'\s*(\d{2})/(\d{2})/(\d{4})\s*', value)
        if not match:
            continue
        day, month, year = map(int, match.groups())
        try:
            iso = date(year, month, day).isoformat()
        except ValueError:
            continue
        if lower <= iso <= upper and not any(s['date'] == iso for s in result):
            # Session URLs may contain identity/session material; return only the entry URL.
            result.append({'date':iso,'url':url})
    return result


async def inspect_guard(page):
    body = (await page.locator('body').inner_text())[:40000].lower()
    if any(t in body for t in ('verify you are human','verifica que eres humano','comprueba que eres humano','captcha','unusual traffic','access denied')):
        raise PortalStop('needs_action', 'El portal solicita una verificación humana o ha rechazado la conexión. La búsqueda se ha detenido.')
    if await page.locator('iframe[src*="recaptcha"], iframe[src*="hcaptcha"]').count():
        raise PortalStop('needs_action', 'El portal requiere una verificación humana. No se ha intentado eludirla.')


async def check(request, recipe):
    from playwright.async_api import async_playwright
    url = recipe['url']
    parsed = urlparse(url)
    if parsed.scheme != 'https' or parsed.hostname not in ALLOWED_HOSTS or parsed.query or parsed.fragment:
        raise PortalStop('configuration', 'La dirección del portal no está aprobada en la configuración del motor.')
    if request.get('city') and not recipe.get('supports_city'):
        raise PortalStop('configuration', 'El filtro de ciudad aún no está verificado; no se buscará en otra ciudad.')
    if request.get('office') and not recipe.get('supports_office'):
        raise PortalStop('configuration', 'El filtro de oficina aún no está verificado.')
    for field in recipe.get('required_fields', []):
        if not request.get(field):
            raise PortalStop('needs_action', 'Falta un dato obligatorio: ' + field)
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(locale='es-ES', timezone_id='Europe/Madrid')
        page = await context.new_page()
        page.set_default_timeout(20000)
        try:
            response = await page.goto(url, wait_until='domcontentloaded', timeout=45000)
            if response and response.status == 429:
                raise PortalStop('needs_action', 'El portal ha pedido reducir las consultas. Se ha detenido la búsqueda.')
            if response and response.status >= 400:
                raise PortalStop('error', 'El portal no ha respondido correctamente. Se volverá a intentar más tarde.')
            for step in recipe['steps']:
                await inspect_guard(page)
                selector = page.locator(step['selector'])
                if step.get('optional') and not await selector.count():
                    continue
                if await selector.count() != 1:
                    raise PortalStop('configuration', 'El formulario ha cambiado o no coincide con el trámite configurado. Se ha detenido la búsqueda para revisarlo.')
                value = request.get(step.get('field', ''), step.get('value', ''))
                if step.get('field') == 'province':
                    value = value.split(' — ')[0]
                if step['action'] == 'fill':
                    await selector.fill(value)
                elif step['action'] == 'select':
                    await selector.select_option(label=value)
                elif step['action'] == 'click':
                    await selector.click()
                else:
                    raise PortalStop('configuration', 'La configuración contiene un paso no admitido.')
                await page.wait_for_load_state('domcontentloaded')
            await inspect_guard(page)
            if await page.locator(recipe['empty_selector']).is_visible():
                return []
            dates = await page.locator(recipe['slot_selector']).all_text_contents()
            if not dates:
                raise PortalStop('configuration', 'No apareció un resultado claro. Esto no se considera prueba de que no haya citas.')
            return matching_slots(dates, request, url)
        finally:
            await context.close()
            await browser.close()
