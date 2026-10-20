"""GUI testleri için bir ekran gerekir; Linux'ta DISPLAY tanımlanmalıdır."""

import csv
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app_service import load_project
from uav import ROOT


@unittest.skipUnless(os.environ.get("DISPLAY") or os.name == "nt", "Grafik ekranı yok; GUI testleri atlandı")
class DesktopFlowTests(unittest.TestCase):
    def setUp(self):
        from desktop_app import UAVApp
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        self.app = UAVApp(self.directory / "gui.sqlite3")
        self.app.update()

    def tearDown(self):
        self.app.destroy()
        self.temporary.cleanup()

    def test_navigation_and_profile_search(self):
        for page in ("design", "compare", "roadmap", "home", "library"):
            self.app.nav_buttons[page].invoke()
            self.app.update()
            self.assertEqual(self.app.current_page, page)
        self.assertEqual(len(self.app.tree.get_children()), 80)
        self.app.search_var.set("s1223")
        self.app.filter_library()
        self.assertEqual(set(self.app.tree.get_children()), {"s1223", "s1223rtl"})
        self.app.search_var.set("no-matching-profile")
        self.app.filter_library()
        self.assertEqual(len(self.app.tree.get_children()), 0)
        self.assertIsNone(self.app.library_selection)
        self.app.search_var.set("")
        self.app.family_var.set("NACA")
        self.app.filter_library()
        self.assertEqual(len(self.app.tree.get_children()), 12)

    def test_calculation_validation_and_stale_result_reset(self):
        self.app.show_page("design")
        self.assertTrue(self.app.calculate())
        before = self.app.results["required_wing_CL"]
        self.app.fields["mass_kg"].set("10,0")
        self.assertIsNone(self.app.results)
        self.assertEqual(self.app.result_labels["required_wing_CL"].cget("text"), "—")
        self.assertTrue(self.app.calculate())
        self.assertAlmostEqual(self.app.results["required_wing_CL"], before * 2)
        self.app.fields["mass_kg"].set("0")
        self.assertFalse(self.app.calculate())
        self.assertIsNone(self.app.results)
        self.assertTrue(self.app.form_message.get())

    def test_project_save_open_and_csv_export(self):
        self.app.show_page("design")
        project = self.directory / "Tasarım denemesi.json"
        self.app.fields["name"].set("Türkçe test tasarımı")
        with patch("desktop_app.filedialog.asksaveasfilename", return_value=str(project)):
            self.app.save_design()
        self.assertEqual(load_project(project)["name"], "Türkçe test tasarımı")
        self.app.fields["mass_kg"].set("9")
        with patch("desktop_app.filedialog.askopenfilename", return_value=str(project)):
            self.app.open_design()
        self.assertEqual(self.app.fields["mass_kg"].get(), "5.0")
        report = self.directory / "Rapor.csv"
        with patch("desktop_app.filedialog.asksaveasfilename", return_value=str(report)):
            self.app.export_results()
        with report.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.reader(handle, delimiter=";"))
        self.assertTrue(any(row[1] == "reference_reynolds" for row in rows[1:]))

    def test_missing_comparison_data_is_explicit(self):
        self.app.show_page("compare")
        self.assertEqual(len(self.app.compare_chart.series), 2)
        self.app.candidate_var.set("E387")
        self.app.refresh_comparison()
        self.assertEqual(len(self.app.compare_chart.series), 1)
        self.assertIn("E387", self.app.compare_note.cget("text"))
        self.assertIn("eksik", self.app.compare_note.cget("text"))

    def test_import_dat_updates_library_and_database(self):
        self.app.show_page("library")
        original = (ROOT / "data/raw/naca2412.dat").read_text(encoding="utf-8")
        modified = self.directory / "modified.dat"
        modified.write_text(original.replace("0.0114", "0.0115"), encoding="utf-8")
        with patch("desktop_app.filedialog.askopenfilename", return_value=str(modified)):
            self.app.import_selected()
        self.assertEqual(self.app.store.summary()["geometry_versions"], 3)
        self.assertAlmostEqual(self.app.store.geometry("naca2412")[1][1], 0.0115)
        self.app.use_selected()
        self.assertEqual(self.app.current_page, "design")
        self.assertEqual(self.app.fields["current_airfoil"].get(), "NACA 2412")
