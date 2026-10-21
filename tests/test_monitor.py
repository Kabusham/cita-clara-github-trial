import importlib
import json
import os
import unittest
from unittest.mock import patch

with patch.dict(os.environ, {"GH_TOKEN": "test-only", "REPOSITORY": "owner/repo"}):
    monitor = importlib.import_module("scripts.monitor")


class MonitorTests(unittest.TestCase):
    def test_identical_status_is_not_posted_twice(self):
        issue = {"number": 1}
        with patch.object(monitor, "last_marker_comment", return_value=""), patch.object(monitor, "api") as api:
            self.assertTrue(monitor.post_status(issue, "not-verified", "Sin integración."))
            body = api.call_args.args[2]["body"]
        with patch.object(monitor, "last_marker_comment", return_value=body), patch.object(monitor, "api") as api:
            self.assertFalse(monitor.post_status(issue, "not-verified", "Sin integración."))
            api.assert_not_called()

    def test_changed_dates_are_not_suppressed(self):
        issue = {"number": 1}
        url = "https://icp.administracionelectronica.gob.es/icpplus/index.html"
        with patch.object(monitor, "last_marker_comment", return_value=""), patch.object(monitor, "api") as api:
            monitor.post_status(issue, "availability", "Disponibilidad.", [{"date": "2099-01-01", "url": url}])
            previous = api.call_args.args[2]["body"]
        with patch.object(monitor, "last_marker_comment", return_value=previous), patch.object(monitor, "api") as api:
            self.assertTrue(monitor.post_status(issue, "availability", "Disponibilidad.", [{"date": "2099-01-02", "url": url}]))
            self.assertEqual(api.call_count, 1)

    def test_latest_bot_status_is_found_after_first_page(self):
        def comment(body, login="github-actions[bot]"):
            return {"body": body, "user": {"login": login}}
        old = "<!-- CITA-CLARA-STATUS:old -->"
        latest = "<!-- CITA-CLARA-STATUS:new -->"
        first_page = [comment(old)] + [comment("Comentario normal")] * 99
        second_page = [comment(latest), comment(old, "someone-else")]
        with patch.object(monitor, "api", side_effect=[first_page, second_page]) as api:
            self.assertEqual(monitor.last_marker_comment(1), latest)
            self.assertIn("page=2", api.call_args.args[0])

    def test_public_request_rejects_personal_data(self):
        payload = {"province": "Zaragoza", "city": "Calatayud", "office": "Cualquier oficina", "procedure": "Prueba", "documentNumber": "PRIVATE"}
        issue = {"body": monitor.MARKER + json.dumps(payload) + monitor.END_MARKER}
        with self.assertRaises(ValueError):
            monitor.request_from_issue(issue)
