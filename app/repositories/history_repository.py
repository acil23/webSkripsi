"""Repository SQLite untuk penyimpanan riwayat jadwal."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.paths import DB_DIR
from app.entities.history_entities import DATE_FORMAT, RiwayatJadwal


class HistoryRepository:
    """Persistence layer untuk RiwayatJadwal menggunakan SQLite."""

    def __init__(self, db_path: Path | None = None):
        self.db_path = Path(db_path or DB_DIR / "scheduling_history.sqlite3")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS riwayat_jadwal (
                    id_riwayat TEXT PRIMARY KEY,
                    nama_riwayat TEXT NOT NULL,
                    waktu_simpan TEXT NOT NULL,
                    semester_active TEXT,
                    model_name TEXT,
                    fitness REAL,
                    total_conflict INTEGER,
                    total_penalty REAL,
                    standar_deviasi_beban REAL,
                    is_feasible INTEGER,
                    result_json TEXT NOT NULL,
                    parameter_json TEXT NOT NULL,
                    class_opening_json TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_riwayat_waktu ON riwayat_jadwal(waktu_simpan)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_riwayat_nama ON riwayat_jadwal(nama_riwayat)")

    def save(self, riwayat: RiwayatJadwal) -> RiwayatJadwal:
        summary = riwayat.get_summary()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO riwayat_jadwal (
                    id_riwayat, nama_riwayat, waktu_simpan, semester_active, model_name,
                    fitness, total_conflict, total_penalty, standar_deviasi_beban, is_feasible,
                    result_json, parameter_json, class_opening_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    riwayat.id_riwayat,
                    riwayat.nama_riwayat,
                    riwayat.waktu_simpan.strftime(DATE_FORMAT),
                    summary["semester_active"],
                    summary["model_name"],
                    float(summary["fitness"]),
                    int(summary["total_conflict"]),
                    float(summary["total_penalty"]),
                    float(summary["standar_deviasi_beban"]),
                    1 if summary["is_feasible"] else 0,
                    json.dumps(riwayat.result_payload, ensure_ascii=False),
                    json.dumps(riwayat.parameter_payload, ensure_ascii=False),
                    json.dumps(riwayat.class_opening_payload, ensure_ascii=False),
                ),
            )
        return riwayat

    def find_all(self) -> list[RiwayatJadwal]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM riwayat_jadwal ORDER BY waktu_simpan DESC"
            ).fetchall()
        return [self._row_to_entity(row) for row in rows]

    def find_by_id(self, id_riwayat: str) -> RiwayatJadwal | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM riwayat_jadwal WHERE id_riwayat = ?",
                (id_riwayat,),
            ).fetchone()
        return self._row_to_entity(row) if row else None

    def delete(self, id_riwayat: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM riwayat_jadwal WHERE id_riwayat = ?", (id_riwayat,))
            return cursor.rowcount > 0

    def count(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS total FROM riwayat_jadwal").fetchone()
        return int(row["total"] if row else 0)

    def _row_to_entity(self, row: sqlite3.Row) -> RiwayatJadwal:
        return RiwayatJadwal(
            id_riwayat=str(row["id_riwayat"]),
            nama_riwayat=str(row["nama_riwayat"]),
            waktu_simpan=datetime.strptime(str(row["waktu_simpan"]), DATE_FORMAT),
            result_payload=json.loads(row["result_json"] or "{}"),
            parameter_payload=json.loads(row["parameter_json"] or "{}"),
            class_opening_payload=json.loads(row["class_opening_json"] or "[]"),
        )
