"""Service ekspor hasil penjadwalan.

Tahap 7 merealisasikan CSVExporter sesuai class diagram Bab 5. Service ini
mengubah objek PenjadwalanResult menjadi berkas CSV dan paket ZIP yang dapat
diunduh oleh Admin Program Studi melalui FileExportRouter.
"""

from __future__ import annotations

import csv
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.paths import EXPORT_DIR
from app.entities.result_entities import PenjadwalanResult


class CSVExporter:
    """Membentuk file ekspor jadwal, evaluasi, beban dosen, log, dan ZIP."""

    def __init__(self, export_dir: Path = EXPORT_DIR):
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def export_schedule(self, result: PenjadwalanResult) -> Path:
        path = self._build_path(result, "jadwal", "csv")
        rows = [item.to_row() for item in result.get_jadwal().get_items()]
        fieldnames = [
            "class_id",
            "jenis_mk",
            "semester",
            "kode_mk",
            "mata_kuliah",
            "sks",
            "kelas",
            "dosen",
            "hari",
            "jam_mulai",
            "jam_selesai",
            "ruang",
            "kapasitas_ruang",
            "jumlah_mahasiswa",
            "prioritas_dosen",
            "metode_pemilihan",
        ]
        header_map = {
            "class_id": "ID Kelas",
            "jenis_mk": "Jenis MK",
            "semester": "Semester",
            "kode_mk": "Kode MK",
            "mata_kuliah": "Mata Kuliah",
            "sks": "SKS",
            "kelas": "Kelas",
            "dosen": "Dosen",
            "hari": "Hari",
            "jam_mulai": "Jam Mulai",
            "jam_selesai": "Jam Selesai",
            "ruang": "Ruangan",
            "kapasitas_ruang": "Kapasitas Ruang",
            "jumlah_mahasiswa": "Jumlah Mahasiswa",
            "prioritas_dosen": "Prioritas Dosen",
            "metode_pemilihan": "Metode Pemilihan",
        }
        self._write_csv(path, rows, fieldnames, header_map)
        return path

    def export_evaluation(self, result: PenjadwalanResult) -> Path:
        path = self._build_path(result, "evaluasi", "csv")
        summary = result.to_summary()
        evaluation = result.get_evaluasi().to_dict()
        row = {
            "jadwal_id": result.get_jadwal().jadwal_id,
            "generated_at": summary.get("generated_at"),
            "semester_active": result.semester_active,
            "model_name": result.model_name,
            "total_items": summary.get("total_items"),
            "fitness": evaluation.get("fitness"),
            "total_penalty": evaluation.get("total_penalty"),
            "hard_penalty": evaluation.get("hard_penalty"),
            "preference_penalty": evaluation.get("preference_penalty"),
            "fairness_penalty": evaluation.get("fairness_penalty"),
            "total_conflict": evaluation.get("total_conflict"),
            "capacity_conflicts": evaluation.get("capacity_conflicts"),
            "room_conflicts": evaluation.get("room_conflicts"),
            "lecturer_conflicts": evaluation.get("lecturer_conflicts"),
            "standar_deviasi_beban": evaluation.get("standar_deviasi_beban"),
            "avg_sks": evaluation.get("avg_sks"),
            "min_sks": evaluation.get("min_sks"),
            "max_sks": evaluation.get("max_sks"),
            "jumlah_dosen_fairness": evaluation.get("jumlah_dosen_fairness"),
            "waktu_komputasi_detik": evaluation.get("waktu_komputasi"),
            "is_feasible": evaluation.get("is_feasible"),
        }
        header_map = {
            "jadwal_id": "ID Jadwal",
            "generated_at": "Waktu Dibuat",
            "semester_active": "Semester Aktif",
            "model_name": "Model Algoritma",
            "total_items": "Total Sesi Jadwal",
            "fitness": "Fitness",
            "total_penalty": "Total Penalty",
            "hard_penalty": "Hard Penalty",
            "preference_penalty": "Preference Penalty",
            "fairness_penalty": "Fairness Penalty",
            "total_conflict": "Total Konflik",
            "capacity_conflicts": "Konflik Kapasitas",
            "room_conflicts": "Konflik Ruang",
            "lecturer_conflicts": "Konflik Dosen",
            "standar_deviasi_beban": "Standar Deviasi Beban",
            "avg_sks": "Rata-rata SKS",
            "min_sks": "Minimum SKS",
            "max_sks": "Maksimum SKS",
            "jumlah_dosen_fairness": "Jumlah Dosen Fairness",
            "waktu_komputasi_detik": "Waktu Komputasi (detik)",
            "is_feasible": "Feasible",
        }
        self._write_csv(path, [row], list(row.keys()), header_map)
        return path

    def export_workload(self, result: PenjadwalanResult) -> Path:
        path = self._build_path(result, "beban_dosen", "csv")
        rows = [item.to_dict() for item in result.get_beban_dosen()]
        rows = sorted(
            rows,
            key=lambda row: (
                0 if row.get("dihitung_fairness") else 1,
                -int(row.get("total_sks") or 0),
                str(row.get("dosen") or ""),
            ),
        )
        fieldnames = [
            "dosen",
            "total_sks",
            "jumlah_sesi",
            "jumlah_mk_unik",
            "dihitung_fairness",
            "status_fairness",
        ]
        header_map = {
            "dosen": "Dosen",
            "total_sks": "Total SKS",
            "jumlah_sesi": "Jumlah Sesi",
            "jumlah_mk_unik": "Jumlah MK Unik",
            "dihitung_fairness": "Dihitung Fairness",
            "status_fairness": "Status Fairness",
        }
        self._write_csv(path, rows, fieldnames, header_map)
        return path

    def export_convergence_log(self, result: PenjadwalanResult) -> Path:
        path = self._build_path(result, "log_konvergensi", "csv")
        rows = [log.to_dict() for log in result.get_log_konvergensi()]
        fieldnames = ["generasi", "best_fitness", "total_conflict", "total_penalty"]
        header_map = {
            "generasi": "Generasi",
            "best_fitness": "Fitness Terbaik",
            "total_conflict": "Jumlah Konflik",
            "total_penalty": "Total Penalty",
        }
        self._write_csv(path, rows, fieldnames, header_map)
        return path

    def export_package(self, result: PenjadwalanResult) -> Path:
        """Membentuk ZIP berisi seluruh file CSV hasil penjadwalan."""
        schedule_file = self.export_schedule(result)
        evaluation_file = self.export_evaluation(result)
        workload_file = self.export_workload(result)
        log_file = self.export_convergence_log(result)

        zip_path = self._build_path(result, "paket_hasil", "zip")
        with zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as zip_file:
            for file_path in [schedule_file, evaluation_file, workload_file, log_file]:
                zip_file.write(file_path, arcname=file_path.name)
        return zip_path

    def export_by_type(self, result: PenjadwalanResult, export_type: str) -> Path:
        export_type = export_type.strip().lower()
        if export_type == "schedule":
            return self.export_schedule(result)
        if export_type == "evaluation":
            return self.export_evaluation(result)
        if export_type == "workload":
            return self.export_workload(result)
        if export_type in {"convergence_log", "log"}:
            return self.export_convergence_log(result)
        if export_type in {"package", "zip"}:
            return self.export_package(result)
        raise ValueError(f"Jenis ekspor tidak dikenal: {export_type}")

    def get_export_manifest(self, result: PenjadwalanResult) -> list[dict[str, Any]]:
        """Metadata pilihan ekspor untuk halaman UI."""
        total_schedule = len(result.get_jadwal().get_items())
        total_workload = len(result.get_beban_dosen())
        total_logs = len(result.get_log_konvergensi())
        return [
            {
                "key": "schedule",
                "title": "Jadwal Perkuliahan",
                "description": "Ekspor data jadwal perkuliahan yang berisi mata kuliah, dosen, ruang, hari, dan jam.",
                "format": "CSV",
                "icon": "▣",
                "url": "/export/schedule",
                "meta": f"{total_schedule} sesi jadwal",
            },
            {
                "key": "evaluation",
                "title": "Evaluasi Jadwal",
                "description": "Ekspor ringkasan evaluasi jadwal meliputi fitness, total penalty, konflik, dan fairness.",
                "format": "CSV",
                "icon": "↗",
                "url": "/export/evaluation",
                "meta": "1 baris ringkasan",
            },
            {
                "key": "workload",
                "title": "Beban Dosen",
                "description": "Ekspor ringkasan beban mengajar dosen dan status fairness.",
                "format": "CSV",
                "icon": "♙",
                "url": "/export/workload",
                "meta": f"{total_workload} dosen",
            },
            {
                "key": "convergence_log",
                "title": "Log Konvergensi",
                "description": "Ekspor log konvergensi yang berisi progress optimasi per generasi.",
                "format": "CSV",
                "icon": "⌁",
                "url": "/export/convergence-log",
                "meta": f"{total_logs} generasi",
            },
            {
                "key": "package",
                "title": "Paket Hasil Lengkap",
                "description": "Unduh arsip lengkap yang berisi jadwal, evaluasi, beban dosen, dan log konvergensi.",
                "format": "ZIP",
                "icon": "▤",
                "url": "/export/package",
                "meta": "4 file hasil",
                "wide": True,
            },
        ]

    def _write_csv(
        self,
        path: Path,
        rows: list[dict[str, Any]],
        fieldnames: list[str],
        header_map: dict[str, str],
    ) -> None:
        with path.open("w", newline="", encoding="utf-8-sig") as csv_file:
            writer = csv.DictWriter(
                csv_file,
                fieldnames=fieldnames,
                extrasaction="ignore",
            )
            writer.writerow({field: header_map.get(field, field) for field in fieldnames})
            for row in rows:
                writer.writerow({field: self._format_value(row.get(field)) for field in fieldnames})

    def _build_path(self, result: PenjadwalanResult, suffix: str, extension: str) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        semester = self._safe_token(result.semester_active)
        model = self._safe_token(result.model_name)
        filename = f"{suffix}_{timestamp}_{semester}_{model}.{extension}"
        return self.export_dir / filename

    @staticmethod
    def _safe_token(value: str) -> str:
        cleaned = "".join(char if char.isalnum() or char in {"_", "-"} else "_" for char in str(value))
        return cleaned.strip("_") or "result"

    @staticmethod
    def _format_value(value: Any) -> Any:
        if isinstance(value, bool):
            return "Ya" if value else "Tidak"
        if value is None:
            return ""
        return value
