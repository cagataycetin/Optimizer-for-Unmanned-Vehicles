import json
import tempfile
import unittest
from pathlib import Path

from app_service import ProjectStore, aircraft_from_fields, load_project, sample_aircraft, save_project


class ProjectFileTests(unittest.TestCase):
    def test_turkish_decimal_input(self):
        fields = {key: str(value) for key, value in sample_aircraft().items()}
        fields["mass_kg"] = " 5,5 "
        self.assertEqual(aircraft_from_fields(fields)["mass_kg"], 5.5)
        for value in ("", "abc", "nan", "inf", "-5", True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                aircraft_from_fields({**fields, "mass_kg": value})

    def test_project_roundtrip_and_untrusted_saved_results(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "İHA Tasarımım.json"
            original = sample_aircraft()
            save_project(path, original)
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["results"]["required_wing_CL"] = -999
            path.write_text(json.dumps(payload), encoding="utf-8")
            self.assertEqual(load_project(path), original)
            self.assertEqual(load_project(Path(__file__).parents[1] / "examples/aircraft.json"), original)

    def test_invalid_project_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            for payload in ([], {"format_version": 999}, {"aircraft": []}, {"aircraft": {}}):
                path.write_text(json.dumps(payload), encoding="utf-8")
                with self.subTest(payload=payload), self.assertRaises(ValueError):
                    load_project(path)

    def test_store_reopens_without_duplicates(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "data.sqlite3"
            for _ in range(2):
                store = ProjectStore(db_path)
                try:
                    self.assertEqual(len(store.airfoils()), 80)
                    self.assertEqual(store.summary()["geometry_versions"], 2)
                    self.assertEqual(len(store.geometry("naca2412")), 35)
                    self.assertEqual(store.geometry("e387"), [])
                finally:
                    store.close()
