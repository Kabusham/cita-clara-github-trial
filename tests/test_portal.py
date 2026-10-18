import unittest
from datetime import date
from portal import choose_recipe, matching_slots


class PortalTests(unittest.TestCase):
    def test_only_verified_province_and_procedure_recipe_is_selected(self):
        recipes = [
            {"verified": False, "procedure": "TIE", "provinces": ["Zaragoza"]},
            {"verified": True, "procedure": "TIE", "provinces": ["Zaragoza"]},
        ]
        self.assertIs(choose_recipe(recipes, {"type": "TIE", "province": "Zaragoza"}), recipes[1])
        self.assertIsNone(choose_recipe(recipes, {"type": "TIE", "province": "Huesca"}))

    def test_slots_are_date_filtered_and_duplicate_dates_removed(self):
        request = {"from": date.today().isoformat(), "to": "9999-12-31"}
        future = date.today().replace(year=date.today().year + 1)
        raw = [future.strftime("%d/%m/%Y"), future.strftime("%d/%m/%Y"), "fecha no reconocida"]
        result = matching_slots(raw, request, "https://icp.administracionelectronica.gob.es/icpplus/index.html")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["date"], future.isoformat())
        self.assertEqual(set(result[0]), {"date", "url"})


if __name__ == "__main__":
    unittest.main()
