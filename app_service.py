"""Arayüzden bağımsız veri, proje dosyası ve hesaplama işlemleri."""

import json
import math
from pathlib import Path

from uav import DEFAULT_DB, ROOT, connect, flight_conditions, import_geometry, seed, status

NUMERIC_FIELDS = (
    ("mass_kg", "Uçuş kütlesi", "kg"),
    ("wing_area_m2", "Kanat alanı", "m²"),
    ("span_m", "Kanat açıklığı", "m"),
    ("reference_chord_m", "Referans kord", "m"),
    ("cruise_speed_m_s", "Seyir hava hızı", "m/s"),
    ("density_kg_m3", "Hava yoğunluğu", "kg/m³"),
    ("dynamic_viscosity_pa_s", "Dinamik viskozite", "Pa·s"),
    ("speed_of_sound_m_s", "Ses hızı", "m/s"),
)


def sample_aircraft():
    return json.loads((ROOT / "examples" / "aircraft.json").read_text(encoding="utf-8"))


def aircraft_from_fields(fields):
    aircraft = {
        "name": str(fields.get("name", "")).strip() or "İsimsiz tasarım",
        "current_airfoil": str(fields.get("current_airfoil", "")).strip(),
    }
    for key, label, unit in NUMERIC_FIELDS:
        value = fields.get(key, "")
        if isinstance(value, bool):
            raise ValueError(f"{label}: {unit} biriminde pozitif bir sayı girin.")
        try:
            aircraft[key] = float(str(value).strip().replace(",", "."))
        except (ValueError, TypeError):
            raise ValueError(f"{label}: {unit} biriminde bir sayı girin.") from None
        if not math.isfinite(aircraft[key]) or aircraft[key] <= 0:
            raise ValueError(f"{label}: {unit} biriminde sıfırdan büyük, sonlu bir sayı girin.")
    flight_conditions(aircraft)
    return aircraft


def save_project(path, aircraft):
    payload = {"format_version": 1, "aircraft": aircraft, "results": flight_conditions(aircraft)}
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def load_project(path):
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("Proje dosyası bir JSON nesnesi olmalı.")
    if "format_version" in payload and payload["format_version"] != 1:
        raise ValueError("Bu proje dosyasının sürümü desteklenmiyor.")
    aircraft = payload.get("aircraft", payload)
    if not isinstance(aircraft, dict):
        raise ValueError("Proje dosyasında İHA bilgileri bulunamadı.")
    return aircraft_from_fields(aircraft)


class ProjectStore:
    def __init__(self, db_path=DEFAULT_DB):
        self.db = connect(db_path)
        try:
            seed(self.db)
            for file in sorted((ROOT / "data" / "raw").glob("*.dat")):
                import_geometry(self.db, file.stem, file.read_text(encoding="utf-8-sig"), file.resolve().as_uri())
        except Exception:
            self.db.close()
            raise

    def close(self):
        self.db.close()

    def summary(self):
        return status(self.db)

    def airfoils(self):
        return [dict(row) for row in self.db.execute(
            "SELECT a.*, coalesce(g.point_count, 0) AS point_count "
            "FROM airfoils a LEFT JOIN geometries g ON g.id = "
            "(SELECT max(id) FROM geometries WHERE airfoil_id = a.id) ORDER BY a.rowid"
        )]

    def geometry(self, airfoil_id):
        row = self.db.execute(
            "SELECT points_json FROM geometries WHERE airfoil_id = ? ORDER BY id DESC LIMIT 1", (airfoil_id,)
        ).fetchone()
        return json.loads(row["points_json"]) if row else []

    def import_dat(self, airfoil_id, path):
        file = Path(path)
        return import_geometry(self.db, airfoil_id, file.read_text(encoding="utf-8-sig"), file.resolve().as_uri())
