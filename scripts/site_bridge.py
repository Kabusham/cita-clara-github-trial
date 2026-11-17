"""Connect the private Cita Clara dashboard to this repository's scheduled runner."""
import asyncio
from datetime import datetime
import json
import os
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from portal import PortalStop, check, choose_recipe, load_recipes

SITE = "https://khalil-citas-desk.kabusham.chatgpt.site"


class NoRedirect(HTTPRedirectHandler):
    """Never follow redirects carrying a credential."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


OPENER = build_opener(NoRedirect)


def fetch(url, *, data=None, headers=None, timeout=15):
    headers = dict(headers or {})
    if data is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(data).encode()
    with OPENER.open(Request(url, data=data, headers=headers), timeout=timeout) as response:
        return json.load(response)


class SiteBridge:
    def __init__(self, access):
        self.access = access

    def call(self, op, **data):
        oidc_url = os.environ["ACTIONS_ID_TOKEN_REQUEST_URL"]
        oidc = fetch(oidc_url + ("&" if "?" in oidc_url else "?") + urlencode({"audience": SITE}),
                     headers={"Authorization": "Bearer " + os.environ["ACTIONS_ID_TOKEN_REQUEST_TOKEN"]})
        return fetch(SITE + "/api/github-bridge", data={"op": op, **data}, headers={
            "OAI-Sites-Authorization": "Bearer " + self.access,
            "X-Cita-Clara-Identity": oidc["value"],
        })


class Telegram:
    def __init__(self, token, chat):
        self.token = token
        self.chat = chat

    def request(self, method, **fields):
        result = fetch("https://api.telegram.org/bot" + self.token + "/" + method, data=fields)
        if not isinstance(result, dict) or result.get("ok") is not True:
            return None
        return result.get("result")

    def health(self):
        if not self.token or not self.chat:
            return "MISSING_SECRETS"
        try:
            if self.request("getMe") and self.request("getChat", chat_id=self.chat):
                return "READY"
            return "INVALID_DESTINATION"
        except HTTPError as exc:
            return "INVALID_DESTINATION" if exc.code in (400, 401, 403, 404) else "TELEGRAM_UNREACHABLE"
        except (URLError, OSError, ValueError):
            return "TELEGRAM_UNREACHABLE"

    def send(self, text):
        if not self.token or not self.chat:
            return "SEND_FAILED"
        try:
            result = self.request("sendMessage", chat_id=self.chat, text=text,
                                  link_preview_options={"is_disabled": True})
            return "DELIVERED" if isinstance(result, dict) and "message_id" in result else "SEND_FAILED"
        except HTTPError as exc:
            return "SEND_FAILED" if 400 <= exc.code < 500 else "SEND_UNCERTAIN"
        except (URLError, OSError, ValueError):
            return "SEND_UNCERTAIN"


MESSAGES = {
    "es": {
        "availability": "Se detectó una posible cita. Revisa el portal oficial para confirmar la disponibilidad.",
        "failure": "Falló una consulta de disponibilidad. Revisa el estado de la solicitud.",
        "stopped": "Se detuvo el seguimiento de una solicitud. Revisa su estado antes de reanudarlo.",
        "recovered": "El monitor o el canal de Telegram se ha restablecido tras una interrupción.",
        "test": "Mensaje de prueba de Cita Clara. El monitor recibió tu solicitud de prueba.",
    },
    "ar": {
        "availability": "رصد المراقب توفرًا محتملًا. راجع البوابة الرسمية للتحقق من الموعد.",
        "failure": "تعذّر إكمال فحص الموعد. راجع حالة الطلب في اللوحة.",
        "stopped": "توقّفت متابعة أحد الطلبات. راجع الحالة قبل استئنافها.",
        "recovered": "عاد اتصال المراقب أو قناة Telegram بعد انقطاع.",
        "test": "رسالة اختبار من Cita Clara. تلقّى المراقب طلبك للاختبار.",
    },
}


def send_alert(bridge, telegram, kind, locale, key=None):
    status = telegram.send("Cita Clara\n" + MESSAGES.get(locale, MESSAGES["ar"])[kind] + "\n" + SITE)
    bridge.call("delivery", kind=kind, key=key, status=status)


def report_public_health(status):
    # Only a coarse provider health flag goes to the public GitHub repository.
    token = os.environ.get("GH_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    sha = os.environ.get("GITHUB_SHA")
    if not token or not repo or not sha:
        return
    fetch(f"https://api.github.com/repos/{repo}/statuses/{sha}",
          headers={"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json",
                   "User-Agent": "Cita-Clara-Monitor"},
          data={"state": "success" if status == "READY" else "error", "context": "cita-clara/site",
                "description": status, "target_url": f"https://github.com/{repo}/actions/runs/{os.environ['GITHUB_RUN_ID']}"})


async def check_one(bridge, telegram, recipes):
    for _ in range(15):
        job = bridge.call("claim").get("job")
        if not job:
            return
        job_ref = {"id": job["id"], "lease": job["lease"]}
        criteria = job["criteria"]
        request = {**criteria, "type": criteria["procedure"]}
        recipe = choose_recipe(recipes, request)
        today = datetime.now(ZoneInfo("Europe/Madrid")).date().isoformat()
        if criteria.get("to") and criteria["to"] < today:
            result = "EXPIRED"
        elif not recipe:
            result = "UNVERIFIED"
        elif any(not request.get(field) for field in recipe.get("required_fields", [])):
            # The Site keeps documents and names private, also when a procedure needs manual completion.
            result = "MANUAL_REQUIRED"
        elif (request["city"] and not recipe.get("supports_city")) or (request["office"] and not recipe.get("supports_office")):
            result = "UNVERIFIED"
        else:
            if not bridge.call("start", **job_ref).get("started"):
                return
            result = await check_portal(request, recipe)
            report = bridge.call("finish", **job_ref, result=result).get("report")
            if report and report.get("alert"):
                send_alert(bridge, telegram, report["alert"], report["language"])
            return
        report = bridge.call("finish", **job_ref, result=result).get("report")
        if report and report.get("alert"):
            send_alert(bridge, telegram, report["alert"], report["language"])


async def check_portal(request, recipe):
    try:
        slots = await check(request, recipe)
        return "SLOT_AVAILABLE" if slots else "NO_SLOTS"
    except PortalStop as exc:
        return {"needs_action": "MANUAL_REQUIRED", "access_rejected": "ACCESS_REJECTED",
                "error": "ERROR_TECNICO"}.get(exc.state, "UNCERTAIN")
    except Exception:
        # Avoid printing URLs, sessions or raw browser responses.
        return "ERROR_TECNICO"


async def main():
    recipes = [recipe for recipe in load_recipes(ROOT / "config" / "recipes.json") if recipe.get("verified") is True]
    telegram = Telegram(os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID"))
    state = telegram.health()
    try:
        report_public_health(state)
    except (OSError, ValueError):
        print("GitHub public health could not be updated.")
    print(f"Telegram health: {state}. Verified portal recipes: {len(recipes)}.")
    access = os.getenv("CITA_CLARA_SITE_ACCESS")
    if not access:
        print("Private Site connection is pending configuration.")
        return
    bridge = SiteBridge(access)
    signal = bridge.call("heartbeat", recipes=len(recipes), telegram=state)
    if signal.get("testKey"):
        send_alert(bridge, telegram, "test", signal["language"], signal["testKey"])
    if signal.get("recovered"):
        send_alert(bridge, telegram, "recovered", signal["language"])
    await check_one(bridge, telegram, recipes)
    print("Private Site synchronization completed.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except HTTPError as error:
        sys.exit(f"Synchronization could not finish (HTTP {error.code}).")
    except (OSError, KeyError, ValueError):
        sys.exit("Synchronization could not finish.")
