import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from uav import ROOT, connect, flight_conditions, import_geometry, parse_dat, seed, status


class FlightTests(unittest.TestCase):
    def setUp(self):
        self.aircraft = json.loads((ROOT / "examples/aircraft.json").read_text(encoding="utf-8"))

    def test_hand_calculated_level_flight(self):
        result = flight_conditions(self.aircraft)
        self.assertAlmostEqual(result["weight_n"], 49.03325)
        self.assertAlmostEqual(result["dynamic_pressure_pa"], 198.45)
        self.assertAlmostEqual(result["required_wing_CL"], 49.03325 / 158.76)
        self.assertAlmostEqual(result["reference_reynolds"], 7.056 / 0.00001789)
        self.assertAlmostEqual(result["aspect_ratio"], 7.8125)

    def test_speed_effect(self):
        initial = flight_conditions(self.aircraft)
        self.aircraft["cruise_speed_m_s"] *= 2
        faster = flight_conditions(self.aircraft)
        self.assertAlmostEqual(faster["reference_reynolds"], 2 * initial["reference_reynolds"])
        self.assertAlmostEqual(faster["required_wing_CL"], initial["required_wing_CL"] / 4)

    def test_invalid_or_missing_inputs(self):
        for value in (0, -1, float("nan"), float("inf"), True, "18", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                flight_conditions({**self.aircraft, "cruise_speed_m_s": value})
        with self.assertRaises(ValueError):
            flight_conditions({})
        with self.assertRaises(ValueError):
            flight_conditions([])


class GeometryTests(unittest.TestCase):
    def setUp(self):
        self.text = (ROOT / "data/raw/naca2412.dat").read_text(encoding="utf-8")

    def test_official_sample_counts_and_comments(self):
        self.assertEqual(len(parse_dat(self.text)), 35)
        self.assertEqual(len(parse_dat((ROOT / "data/raw/s1223.dat").read_text(encoding="utf-8"))), 81)
        commented = "# Provenance\n" + self.text.replace("0.9500 0.0114", "0.9500 0.0114 # point") + "\x1a"
        self.assertEqual(parse_dat(commented), parse_dat(self.text))

    def test_lednicer_converts_to_same_contour(self):
        points = parse_dat(self.text)
        leading_edge = min(range(len(points)), key=lambda i: points[i][0])
        upper = list(reversed(points[:leading_edge + 1]))
        lower = points[leading_edge:]
        lednicer = "NACA 2412\n" + f"{len(upper)} {len(lower)}\n"
        lednicer += "\n".join(f"{x} {y}" for x, y in upper + lower)
        self.assertEqual(parse_dat(lednicer), points)

    def test_bad_geometry_is_rejected(self):
        invalid = [
            "<html>Not an airfoil</html>",
            self.text.replace("0.9500 0.0114", "nan 0.0114"),
            self.text.replace("0.9500 0.0114", "95 1.14"),
            self.text.replace("0.9500 0.0114", "broken row"),
            "NACA\n19 18\n" + "\n".join(self.text.splitlines()[1:]),
        ]
        for content in invalid:
            with self.subTest(content=content[:35]), self.assertRaises(ValueError):
                parse_dat(content)


class DatabaseTests(unittest.TestCase):
    def test_idempotent_import_and_geometry_history(self):
        with tempfile.TemporaryDirectory() as directory:
            db = connect(Path(directory) / "test.sqlite3")
            try:
                seed(db)
                seed(db)
                text = (ROOT / "data/raw/naca2412.dat").read_text(encoding="utf-8")
                import_geometry(db, "naca2412", text, "test://official-sample")
                import_geometry(db, "naca2412", text, "test://official-sample")
                report = status(db)
                self.assertEqual(report["candidate_airfoils"], 80)
                self.assertEqual(report["geometry_versions"], 1)
                self.assertFalse(report["recommendation_ready"])
                import_geometry(db, "naca2412", text.replace("0.0114", "0.0115"), "test://modified-sample")
                self.assertEqual(status(db)["geometry_versions"], 2)
                self.assertEqual(status(db)["airfoils_with_geometry"], 1)
                with self.assertRaises(ValueError):
                    import_geometry(db, "unknown", text, "test://unknown")
                with self.assertRaises(ValueError):
                    import_geometry(db, "naca2412", "bad", "test://bad")
                self.assertEqual(status(db)["geometry_versions"], 2)
            finally:
                db.close()

    def test_polar_cannot_reference_nonexistent_geometry(self):
        with tempfile.TemporaryDirectory() as directory:
            db = connect(Path(directory) / "test.sqlite3")
            try:
                with self.assertRaises(sqlite3.IntegrityError):
                    with db:
                        db.execute(
                            "INSERT INTO polar_runs "
                            "(geometry_id, data_kind, source, reynolds, mach, surface_condition, settings_json) "
                            "VALUES (999, 'simulation', 'test', 400000, 0.05, 'smooth', '{}')"
                        )
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()
