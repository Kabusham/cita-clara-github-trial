"""Monitors only explicitly verified recipes from public GitHub issues."""
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

# When invoked as `python scripts/monitor.py`, Python puts `scripts/` rather
# than the repository root on sys.path. Add the root so `portal.py` imports
# consistently in GitHub Actions and in local runs.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from portal import PortalStop, check, load_recipes, choose_recipe

TOKEN = os.environ["GH_TOKEN"]
REPOSITORY = os.environ["REPOSITORY"]
API = f"https://api.github.com/repos/{REPOSITORY}"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
MARKER = "<!-- CITA-CLARA-REQUEST -->"
END_MARKER = "<!-- FIN CITA-CLARA-REQUEST -->"


def api(path, method="GET", body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(API + path, data=data, headers={**HEADERS, "Content-Type": "application/json"}, method=method)
    with urllib.request.urlopen(req, timeout=25) as res:
        return json.loads(res.read()) if res.status != 204 else None


def request_from_issue(issue):
    body = issue.get("body") or ""
    if MARKER not in body or END_MARKER not in body:
        return None
    payload = body.split(MARKER, 1)[1].split(END_MARKER, 1)[0].strip()
    request = json.loads(payload)
    allowed = {"province", "city", "office", "office_id", "procedure", "from", "to", "frequency_minutes"}
    if set(request) - allowed:
        raise ValueError("La solicitud de GitHub contiene campos no permitidos.")
    for key in ("province", "city", "office", "procedure"):
        if not isinstance(request.get(key), str) or not request[key].strip():
            raise ValueError(f"Falta el campo {key}.")
    return request


def last_marker_comment(issue_number):
    comments = api(f"/issues/{issue_number}/comments?per_page=100")
    return next((c["body"] for c in reversed(comments) if c["body"].startswith("<!-- CITA-CLARA-STATUS:")), "")


def post_status(issue, state, message, slots=None):
    stamp = f"<!-- CITA-CLARA-STATUS:{state} -->"
    details = "\n".join(f"- {s['date']} · [Revisar en portal oficial]({s['url']})" for s in slots or [])
    body = f"{stamp}\n**Estado de la prueba:** {message}\n\n{details}\n\nEste aviso no reserva la cita. Comprueba la disponibilidad en el portal oficial antes de actuar."
    if last_marker_comment(issue["number"]) == stamp:
        return False
    api(f"/issues/{issue['number']}/comments", "POST", {"body": body})
    return True


def alert_telegram():
    bot = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat = os.getenv("TELEGRAM_CHAT_ID", "")
    if not bot or not chat:
        return
    body = urllib.parse.urlencode({"chat_id": chat, "text": "Cita Clara: se detectó una posible disponibilidad. Revísala en el portal oficial; no se ha reservado ninguna cita."}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{bot}/sendMessage", data=body, method="POST")
    with urllib.request.urlopen(req, timeout=15):
        pass


async def run():
    recipes = load_recipes(str(PROJECT_ROOT / "config" / "recipes.json"))
    verified = [r for r in recipes if r.get("verified") is True]
    issues = api("/issues?state=open&per_page=100")
    for issue in issues:
        if "pull_request" in issue:
            continue
        if issue.get("user", {}).get("login", "").casefold() != REPOSITORY.split("/", 1)[0].casefold():
            continue
        try:
            request = request_from_issue(issue)
            if request is None:
                continue
            recipe = choose_recipe(verified, {"type": request["procedure"], "province": request["province"]})
            if recipe is None:
                post_status(issue, "not-verified", "Esta provincia y trámite aún no tienen una integración verificada. No se consultó disponibilidad.")
                continue
            request["type"] = request["procedure"]
            try:
                slots = await check(request, recipe)
            except PortalStop as exc:
                post_status(issue, exc.state, exc.message)
                continue
            if slots:
                changed = post_status(issue, "availability", "Posible disponibilidad detectada. Compruébala manualmente en el portal oficial.", slots)
                if changed:
                    alert_telegram()
            else:
                post_status(issue, "checked-empty", "Comprobación completada: no se detectó una cita dentro del periodo solicitado.")
        except Exception as exc:
            post_status(issue, "error", f"No se pudo completar esta comprobación ({type(exc).__name__}). Se detuvo sin reservar citas ni eludir verificaciones humanas.")

asyncio.run(run())
