PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS airfoils (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    family TEXT NOT NULL,
    source_url TEXT NOT NULL,
    selection_status TEXT NOT NULL DEFAULT 'candidate',
    notes TEXT NOT NULL DEFAULT ''
);

-- Geometri değişirse önceki analizler eski geometriye bağlı kalır.
CREATE TABLE IF NOT EXISTS geometries (
    id INTEGER PRIMARY KEY,
    airfoil_id TEXT NOT NULL REFERENCES airfoils(id),
    sha256 TEXT NOT NULL,
    source_url TEXT NOT NULL,
    original_text TEXT NOT NULL,
    points_json TEXT NOT NULL,
    point_count INTEGER NOT NULL CHECK (point_count >= 20),
    imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (airfoil_id, sha256)
);

-- Sonraki geliştirme aşaması içindir; başlangıçta polar verisi yoktur.
CREATE TABLE IF NOT EXISTS polar_runs (
    id INTEGER PRIMARY KEY,
    geometry_id INTEGER NOT NULL REFERENCES geometries(id),
    data_kind TEXT NOT NULL CHECK (data_kind IN ('simulation', 'experiment')),
    source TEXT NOT NULL,
    solver_version TEXT,
    reynolds REAL NOT NULL CHECK (reynolds > 0),
    mach REAL NOT NULL CHECK (mach >= 0),
    ncrit REAL,
    transition_top REAL,
    transition_bottom REAL,
    surface_condition TEXT NOT NULL,
    settings_json TEXT NOT NULL,
    raw_output_path TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS polar_points (
    id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES polar_runs(id),
    alpha_deg REAL NOT NULL,
    cl REAL,
    cd REAL,
    cm REAL,
    converged INTEGER NOT NULL CHECK (converged IN (0, 1)),
    UNIQUE (run_id, alpha_deg),
    CHECK (converged = 0 OR (cl IS NOT NULL AND cd > 0 AND cm IS NOT NULL))
);
