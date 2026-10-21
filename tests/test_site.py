import json
import os
from pathlib import Path
import unittest
from urllib.parse import parse_qs, unquote, urlparse

try:
    from playwright.sync_api import sync_playwright, expect
except ImportError:
    sync_playwright = None

ROOT = Path(__file__).resolve().parents[1] / "site"
BASE = "https://kabusham.github.io/cita-clara-github-trial/"
DIRECTORY = {"retrieved_at": "datos de prueba", "provinces": [
    {"name": "Zaragoza", "offices": [
        {"id": "test-a", "city": "Zaragoza", "name": "Oficina de prueba A", "procedures": ["Trámite de prueba A"]},
        {"id": "test-b", "city": "Zaragoza", "name": "Oficina de prueba B", "procedures": ["Trámite de prueba B"]},
        {"id": "test-c", "city": "Calatayud", "name": "Oficina de prueba C", "procedures": ["Trámite de prueba C"]}
    ]}
]}


@unittest.skipUnless(sync_playwright, "Playwright no está instalado localmente")
class SiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        try:
            cls.browser = cls.pw.chromium.launch(headless=True)
        except Exception:
            cls.pw.stop()
            if os.getenv("CI"):
                raise
            raise unittest.SkipTest("Chromium no está instalado localmente")

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def setUp(self):
        self.context = self.browser.new_context()
        def route_handler(route):
            url = route.request.url
            if not url.startswith(BASE):
                route.abort()
                return
            path = url[len(BASE):].split("?")[0] or "index.html"
            if path == "oficinas-extranjeria.json":
                route.fulfill(content_type="application/json", body=json.dumps(DIRECTORY))
                return
            if path not in {"index.html", "app.js", "styles.css"}:
                route.abort()
                return
            content_type = {"index.html": "text/html", "app.js": "text/javascript", "styles.css": "text/css"}[path]
            route.fulfill(content_type=content_type, body=(ROOT / path).read_text())
        self.context.route("**/*", route_handler)
        self.page = self.context.new_page()
        self.page.goto(BASE)
        self.unlock()
        self.page.locator("#province").select_option("Zaragoza")

    def tearDown(self):
        self.context.close()

    def unlock(self):
        self.page.locator("#passphrase").fill("clave privada de prueba")
        self.page.locator("#unlock").click()
        expect(self.page.locator("#workspace")).to_be_visible()

    def fill_client(self):
        self.page.locator("#client-name").fill("Persona Ficticia Prueba")
        self.page.locator("#document-type").select_option("Pasaporte")
        self.page.locator("#document-number").fill("TEST-PRIVATE-1234")
        self.page.locator("#client-phone").fill("+34000000000")
        self.page.locator("#client-email").fill("privado@example.invalid")
        self.page.locator("#client").fill("REFERENCIA-PRIVADA")
        self.page.locator("#client-consent").check()
        self.page.locator("#procedure").select_option(label="Trámite de prueba A")

    def test_province_defaults_to_all_offices_and_filters_by_city(self):
        expect(self.page.locator("#city")).to_have_value("*")
        expect(self.page.locator("#office")).to_have_value("*")
        expect(self.page.locator("#office option:checked")).to_have_text("Cualquier oficina (3)")
        self.page.locator("#city").select_option("Calatayud")
        expect(self.page.locator("#office option:checked")).to_have_text("Cualquier oficina (1)")
        expect(self.page.locator("#procedure option")).to_have_count(2)
        self.assertEqual(self.page.locator("#procedure option").last.text_content(), "Trámite de prueba C")

    def test_private_data_survives_unlock_without_leaking_to_issue(self):
        self.fill_client()
        self.page.locator('button[type="submit"]').click()
        expect(self.page.locator(".history-item")).to_have_count(1)
        expect(self.page.locator("#result")).to_contain_text("La búsqueda no se ha iniciado")
        link = self.page.locator("#history a").get_attribute("href")
        public_body = parse_qs(urlparse(link).query)["body"][0]
        stored = self.page.evaluate("localStorage.getItem('cita-clara-vault-v1')")
        for secret in ("Persona Ficticia Prueba", "TEST-PRIVATE-1234", "+34000000000", "privado@example.invalid", "REFERENCIA-PRIVADA"):
            self.assertNotIn(secret, unquote(link))
            self.assertNotIn(secret, stored)
        self.assertIn('"office_id": "*"', public_body)
        self.page.locator("#lock").click()
        self.assertEqual(self.page.locator("#history").text_content(), "")
        self.page.reload()
        self.unlock()
        expect(self.page.locator("#history")).to_contain_text("Persona Ficticia Prueba")
        expect(self.page.locator("#history")).to_contain_text("privado@example.invalid")
        self.page.locator("button[data-delete]").click()
        expect(self.page.locator(".history-item")).to_have_count(0)
        self.page.locator("#lock").click()
        self.unlock()
        expect(self.page.locator(".history-item")).to_have_count(0)

    def test_storage_failure_keeps_form_and_does_not_create_record(self):
        self.fill_client()
        self.page.evaluate("Storage.prototype.setItem = function(){throw new DOMException('Test quota', 'QuotaExceededError')}")
        self.page.locator('button[type="submit"]').click()
        expect(self.page.locator("#result")).to_contain_text("No se pudo guardar")
        expect(self.page.locator("#client-name")).to_have_value("Persona Ficticia Prueba")
        expect(self.page.locator(".history-item")).to_have_count(0)
        expect(self.page.locator('button[type="submit"]')).to_be_enabled()
