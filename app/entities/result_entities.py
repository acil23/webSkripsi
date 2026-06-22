"""Entity hasil penjadwalan untuk Tahap 5.

File ini merealisasikan Jadwal, JadwalItem, EvaluasiJadwal, BebanDosen,
LogKonvergensi, dan PenjadwalanResult sesuai class diagram Bab 5. Objek-objek
ini menjadi bentuk data web-friendly dari hasil engine Memetic Algorithm lama.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class JadwalItem:
    item_id: str
    class_id: int | str
    kode_mk: str
    mata_kuliah: str
    sks: int
    kelas: str
    dosen: str
    hari: str
    jam_mulai: str
    jam_selesai: str
    ruang: str
    kapasitas_ruang: int
    jumlah_mahasiswa: int
    jenis_mk: str = "-"
    semester: str = "-"
    prioritas_dosen: int = 99
    metode_pemilihan: str = "-"

    def to_row(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "class_id": self.class_id,
            "kode_mk": self.kode_mk,
            "mata_kuliah": self.mata_kuliah,
            "sks": self.sks,
            "kelas": self.kelas,
            "dosen": self.dosen,
            "hari": self.hari,
            "jam_mulai": self.jam_mulai,
            "jam_selesai": self.jam_selesai,
            "ruang": self.ruang,
            "kapasitas_ruang": self.kapasitas_ruang,
            "jumlah_mahasiswa": self.jumlah_mahasiswa,
            "jenis_mk": self.jenis_mk,
            "semester": self.semester,
            "prioritas_dosen": self.prioritas_dosen,
            "metode_pemilihan": self.metode_pemilihan,
        }


@dataclass
class Jadwal:
    jadwal_id: str
    generated_at: datetime
    items: list[JadwalItem] = field(default_factory=list)

    def get_items(self) -> list[JadwalItem]:
        return self.items

    def has_conflict(self, evaluasi: "EvaluasiJadwal") -> bool:
        return evaluasi.total_conflict > 0

    def to_rows(self) -> list[dict[str, Any]]:
        return [item.to_row() for item in self.items]


@dataclass
class EvaluasiJadwal:
    total_conflict: int
    fitness: float
    total_penalty: float
    hard_penalty: float
    preference_penalty: float
    fairness_penalty: float
    standar_deviasi_beban: float
    waktu_komputasi: float
    capacity_conflicts: int = 0
    room_conflicts: int = 0
    lecturer_conflicts: int = 0
    avg_sks: float = 0.0
    min_sks: int = 0
    max_sks: int = 0
    jumlah_dosen_fairness: int = 0

    def is_feasible(self) -> bool:
        return self.total_conflict == 0 and self.hard_penalty == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_conflict": self.total_conflict,
            "fitness": self.fitness,
            "total_penalty": self.total_penalty,
            "hard_penalty": self.hard_penalty,
            "preference_penalty": self.preference_penalty,
            "fairness_penalty": self.fairness_penalty,
            "standar_deviasi_beban": self.standar_deviasi_beban,
            "waktu_komputasi": self.waktu_komputasi,
            "capacity_conflicts": self.capacity_conflicts,
            "room_conflicts": self.room_conflicts,
            "lecturer_conflicts": self.lecturer_conflicts,
            "avg_sks": self.avg_sks,
            "min_sks": self.min_sks,
            "max_sks": self.max_sks,
            "jumlah_dosen_fairness": self.jumlah_dosen_fairness,
            "is_feasible": self.is_feasible(),
        }


@dataclass
class BebanDosen:
    dosen: str
    total_sks: int = 0
    jumlah_sesi: int = 0
    jumlah_mk_unik: int = 0
    dihitung_fairness: bool = True

    def add_load(self, sks: int) -> None:
        self.total_sks += int(sks)
        self.jumlah_sesi += 1

    @property
    def status_fairness(self) -> str:
        if not self.dihitung_fairness:
            return "Tidak Dihitung"
        if self.total_sks <= 12:
            return "Seimbang"
        if self.total_sks <= 15:
            return "Cukup Seimbang"
        return "Perlu Ditinjau"

    def to_dict(self) -> dict[str, Any]:
        return {
            "dosen": self.dosen,
            "total_sks": self.total_sks,
            "jumlah_sesi": self.jumlah_sesi,
            "jumlah_mk_unik": self.jumlah_mk_unik,
            "dihitung_fairness": self.dihitung_fairness,
            "status_fairness": self.status_fairness,
        }


@dataclass
class LogKonvergensi:
    generasi: int
    best_fitness: float
    total_conflict: int
    total_penalty: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "generasi": self.generasi,
            "best_fitness": self.best_fitness,
            "total_conflict": self.total_conflict,
            "total_penalty": self.total_penalty,
        }


@dataclass
class PenjadwalanResult:
    jadwal: Jadwal
    evaluasi: EvaluasiJadwal
    beban_dosen: list[BebanDosen]
    log_konvergensi: list[LogKonvergensi]
    parameter: dict[str, Any]
    semester_active: str
    model_name: str = "MA_FIHC_ROBINHOOD"

    def is_ready_to_display(self) -> bool:
        return bool(self.jadwal and self.jadwal.items and self.evaluasi)

    def get_jadwal(self) -> Jadwal:
        return self.jadwal

    def get_evaluasi(self) -> EvaluasiJadwal:
        return self.evaluasi

    def get_beban_dosen(self) -> list[BebanDosen]:
        return self.beban_dosen

    def get_log_konvergensi(self) -> list[LogKonvergensi]:
        return self.log_konvergensi

    def to_summary(self) -> dict[str, Any]:
        return {
            "jadwal_id": self.jadwal.jadwal_id,
            "generated_at": self.jadwal.generated_at.strftime("%Y-%m-%d %H:%M:%S"),
            "semester_active": self.semester_active,
            "model_name": self.model_name,
            "total_items": len(self.jadwal.items),
            "total_beban_dosen": len(self.beban_dosen),
            **self.evaluasi.to_dict(),
        }
