"""İHA airfoil projesi: harici Python paketi gerektirmeyen ilk veri hattı."""

import argparse
import csv
import hashlib
import json
import math
import sqlite3
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_DB = ROOT / "data" / "airfoils.sqlite3"


def connect(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))
    return db


def parse_dat(text):
    """Birim kordlu Selig veya Lednicer DAT; geometriyi otomatik düzeltmez."""
    rows = []
    for line_number, raw in enumerate(text.replace("\x1a", "").splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        fields = line.split()
        try:
            values = tuple(float(v.replace("D", "E").replace("d", "e")) for v in fields)
        except ValueError:
            if rows:
                raise ValueError(f"DAT satır {line_number}: koordinatlar arasında metin var")
            continue  # Başlık, koordinatlar başlamadan önce gelebilir.
        if len(values) != 2 or not all(math.isfinite(v) for v in values):
            raise ValueError(f"DAT satır {line_number}: iki sonlu sayı bekleniyor")
        rows.append(values)

    # Lednicer: önce üst/alt yüzey nokta sayıları, sonra LE -> TE yüzeyleri.
    if rows and all(v >= 2 and v.is_integer() for v in rows[0]):
        upper_count, lower_count = (int(v) for v in rows[0])
        if len(rows) - 1 != upper_count + lower_count:
            raise ValueError("Lednicer nokta sayıları dosyayla uyuşmuyor")
        upper = rows[1:1 + upper_count]
        lower = rows[1 + upper_count:]
        if upper[0][0] > upper[-1][0] or lower[0][0] > lower[-1][0]:
            raise ValueError("Lednicer yüzeyleri LE -> TE sırasıyla bekleniyor")
        rows = list(reversed(upper)) + (lower[1:] if upper[0] == lower[0] else lower)

    if len(rows) < 20:
        raise ValueError("En az 20 koordinat noktası gerekli")
    if any(not (-0.02 <= x <= 1.02 and abs(y) <= 0.5) for x, y in rows):
        raise ValueError("Birim kordlu koordinat bekleniyor; ölçek ve formatı kontrol edin")
    if min(x for x, _ in rows) > 0.02 or max(x for x, _ in rows) < 0.98:
        raise ValueError("Koordinatlar hücum ve firar kenarlarını kapsamıyor")
    if rows[0][0] < 0.95 or rows[-1][0] < 0.95:
        raise ValueError("Kontur firar kenarında başlayıp bitmeli")
    if len(set(rows)) < 20:
        raise ValueError("En az 20 farklı koordinat noktası gerekli")
    return rows


def seed(db):
    with (ROOT / "data" / "airfoil_candidates.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 80 or len({row["id"] for row in rows}) != 80:
        raise ValueError("Katalog 80 farklı aday içermeli")
    with db:
        db.executemany(
            "INSERT INTO airfoils (id, name, family, source_url, notes) "
            "VALUES (:id, :name, :family, :source_url, :notes) ON CONFLICT(id) DO NOTHING",
            rows,
        )


def import_geometry(db, airfoil_id, text, source_url):
    airfoil = db.execute("SELECT * FROM airfoils WHERE id = ?", (airfoil_id,)).fetchone()
    if airfoil is None:
        raise ValueError(f"Katalogda profil yok: {airfoil_id}; önce init çalıştırın")
    points = parse_dat(text)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    with db:
        db.execute(
            "INSERT INTO geometries "
            "(airfoil_id, sha256, source_url, original_text, points_json, point_count) "
            "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(airfoil_id, sha256) DO NOTHING",
            (airfoil_id, digest, source_url, text, json.dumps(points), len(points)),
        )
    return len(points)


def flight_conditions(aircraft):
    if not isinstance(aircraft, dict):
        raise ValueError("İHA girdisi bir JSON nesnesi olmalı")
    keys = ("mass_kg", "wing_area_m2", "span_m", "reference_chord_m",
            "cruise_speed_m_s", "density_kg_m3", "dynamic_viscosity_pa_s", "speed_of_sound_m_s")
    values = {}
    for key in keys:
        value = aircraft.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{key}: SI biriminde sayısal değer gerekli")
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"{key}: sıfırdan büyük, sonlu değer gerekli")
        values[key] = value
    rho = values["density_kg_m3"]
    speed = values["cruise_speed_m_s"]
    area = values["wing_area_m2"]
    weight = values["mass_kg"] * 9.80665
    q = 0.5 * rho * speed ** 2
    return {
        "weight_n": weight,
        "dynamic_pressure_pa": q,
        "wing_loading_n_m2": weight / area,
        "required_wing_CL": weight / (q * area),
        "reference_reynolds": rho * speed * values["reference_chord_m"] / values["dynamic_viscosity_pa_s"],
        "mach": speed / values["speed_of_sound_m_s"],
        "aspect_ratio": values["span_m"] ** 2 / area,
        "model": "Düz, yatay, ivmesiz uçuş; kaldırmanın tamamı kanada atanır.",
        "interpretation": "Kanat CL değeri, 2B profil cl değeriyle aynı kabul edilemez. "
                          "Referans Reynolds yalnızca ilk profil taramasını yönlendirir.",
    }


def status(db):
    return {
        "candidate_airfoils": db.execute("SELECT count(*) FROM airfoils").fetchone()[0],
        "airfoils_with_geometry": db.execute("SELECT count(DISTINCT airfoil_id) FROM geometries").fetchone()[0],
        "geometry_versions": db.execute("SELECT count(*) FROM geometries").fetchone()[0],
        "polar_runs": db.execute("SELECT count(*) FROM polar_runs").fetchone()[0],
        "recommendation_ready": False,
        "next_step": "5 profil için aynı koşullarda polar üretimi ve deneysel doğrulama",
    }


def fetch_geometries(db, limit):
    rows = db.execute("SELECT * FROM airfoils ORDER BY rowid").fetchall()
    if limit is not None:
        rows = rows[:limit]
    failures = []
    for row in rows:
        try:
            cached = ROOT / "data" / "raw" / f"{row['id']}.dat"
            if cached.exists():
                text = cached.read_text(encoding="utf-8")
                geometry_source = cached.resolve().as_uri()
            else:
                request = urllib.request.Request(row["source_url"], headers={"User-Agent": "UAV-Airfoil-Student-Project/0.1"})
                with urllib.request.urlopen(request, timeout=20) as response:
                    text = response.read(1_000_001).decode("utf-8-sig")
                if len(text) > 1_000_000:
                    raise ValueError("Beklenenden büyük DAT dosyası")
                parse_dat(text)
                cached.parent.mkdir(parents=True, exist_ok=True)
                cached.write_text(text, encoding="utf-8")
                geometry_source = row["source_url"]
            count = import_geometry(db, row["id"], text, geometry_source)
            print(f"{row['id']}: {count} nokta")
        except (OSError, ValueError, urllib.error.URLError) as error:
            failures.append(row["id"])
            print(f"{row['id']}: alınamadı: {error}", file=sys.stderr)
    return failures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="80 aday kaydı ve mevcut örnek DAT dosyalarını içeri al")
    commands.add_parser("status", help="Veri kapsamını göster")
    flight = commands.add_parser("flight", help="İHA girdilerinden uçuş koşullarını hesapla")
    flight.add_argument("file", type=Path)
    importer = commands.add_parser("import-dat", help="Yerel DAT koordinatlarını içeri al")
    importer.add_argument("airfoil_id")
    importer.add_argument("file", type=Path)
    fetch = commands.add_parser("fetch", help="UIUC'den adayların DAT dosyalarını indir; internet gerekir")
    fetch.add_argument("--limit", type=int)
    args = parser.parse_args()
    try:
        if args.command == "flight":
            result = flight_conditions(json.loads(args.file.read_text(encoding="utf-8")))
            print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
            return 0
        if args.command == "fetch" and args.limit is not None and args.limit <= 0:
            raise ValueError("--limit pozitif olmalı")
        db = connect(args.db)
        try:
            if args.command == "init":
                seed(db)
                for file in sorted((ROOT / "data" / "raw").glob("*.dat")):
                    import_geometry(db, file.stem, file.read_text(encoding="utf-8"), file.resolve().as_uri())
                print(json.dumps(status(db), ensure_ascii=False, indent=2))
            elif args.command == "status":
                print(json.dumps(status(db), ensure_ascii=False, indent=2))
            elif args.command == "import-dat":
                count = import_geometry(db, args.airfoil_id, args.file.read_text(encoding="utf-8-sig"), args.file.resolve().as_uri())
                print(f"{args.airfoil_id}: {count} nokta içeri alındı")
            elif args.command == "fetch":
                if not db.execute("SELECT count(*) FROM airfoils").fetchone()[0]:
                    raise ValueError("Önce init çalıştırın")
                failures = fetch_geometries(db, args.limit)
                if failures:
                    print("Başarısız profiller: " + ", ".join(failures), file=sys.stderr)
                    return 1
        finally:
            db.close()
    except (OSError, ValueError, sqlite3.Error) as error:
        print(f"Hata: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
