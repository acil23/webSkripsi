"""Entity riwayat jadwal dan helper serialisasi hasil penjadwalan.

Tahap 8 merealisasikan RiwayatJadwal sesuai class diagram Bab 5. Objek ini
menyimpan snapshot hasil jadwal, evaluasi, parameter, konfigurasi kelas, beban
dosen, dan log konvergensi agar hasil dapat ditelusuri kembali melalui SQLite.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from app.entities.result_entities import (
    BebanDosen,
    EvaluasiJadwal,
    Jadwal,
    JadwalItem,
    LogKonvergensi,
    PenjadwalanResult,
)


DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _parse_datetime(value: str | datetime | None) -> datetime:
    if isinstance(value, datetime):
        return value
    if not value:
        return datetime.now()
    for fmt in (DATE_FORMAT, "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(str(value), fmt)
        except ValueError:
            continue
    return datetime.now()


def result_to_payload(result: PenjadwalanResult) -> dict[str, Any]:
    """Mengubah PenjadwalanResult menjadi dictionary JSON-serializable."""
    return {
        "jadwal": {
            "jadwal_id": result.jadwal.jadwal_id,
            "generated_at": result.jadwal.generated_at.strftime(DATE_FORMAT),
            "items": [item.to_row() for item in result.jadwal.items],
        },
        "evaluasi": result.evaluasi.to_dict(),
        "beban_dosen": [item.to_dict() for item in result.beban_dosen],
        "log_konvergensi": [item.to_dict() for item in result.log_konvergensi],
        "parameter": dict(result.parameter or {}),
        "semester_active": result.semester_active,
        "model_name": result.model_name,
    }


def result_from_payload(payload: dict[str, Any]) -> PenjadwalanResult:
    """Membentuk ulang PenjadwalanResult dari payload JSON SQLite."""
    jadwal_payload = payload.get("jadwal", {})
    evaluasi_payload = payload.get("evaluasi", {})

    jadwal_items = [
        JadwalItem(
            item_id=str(row.get("item_id") or f"item-{index + 1}"),
            class_id=row.get("class_id", "-"),
            kode_mk=str(row.get("kode_mk", "-")),
            mata_kuliah=str(row.get("mata_kuliah", "-")),
            sks=int(row.get("sks") or 0),
            kelas=str(row.get("kelas", "-")),
            dosen=str(row.get("dosen", "-")),
            hari=str(row.get("hari", "-")),
            jam_mulai=str(row.get("jam_mulai", "-")),
            jam_selesai=str(row.get("jam_selesai", "-")),
            ruang=str(row.get("ruang", "-")),
            kapasitas_ruang=int(row.get("kapasitas_ruang") or 0),
            jumlah_mahasiswa=int(row.get("jumlah_mahasiswa") or 0),
            jenis_mk=str(row.get("jenis_mk", "-")),
            semester=str(row.get("semester", "-")),
            prioritas_dosen=int(row.get("prioritas_dosen") or 99),
            metode_pemilihan=str(row.get("metode_pemilihan", "-")),
        )
        for index, row in enumerate(jadwal_payload.get("items", []))
    ]

    jadwal = Jadwal(
        jadwal_id=str(jadwal_payload.get("jadwal_id") or f"jadwal-{uuid4().hex[:8]}"),
        generated_at=_parse_datetime(jadwal_payload.get("generated_at")),
        items=jadwal_items,
    )

    evaluasi = EvaluasiJadwal(
        total_conflict=int(evaluasi_payload.get("total_conflict") or 0),
        fitness=float(evaluasi_payload.get("fitness") or 0.0),
        total_penalty=float(evaluasi_payload.get("total_penalty") or 0.0),
        hard_penalty=float(evaluasi_payload.get("hard_penalty") or 0.0),
        preference_penalty=float(evaluasi_payload.get("preference_penalty") or 0.0),
        fairness_penalty=float(evaluasi_payload.get("fairness_penalty") or 0.0),
        standar_deviasi_beban=float(evaluasi_payload.get("standar_deviasi_beban") or 0.0),
        waktu_komputasi=float(evaluasi_payload.get("waktu_komputasi") or 0.0),
        capacity_conflicts=int(evaluasi_payload.get("capacity_conflicts") or 0),
        room_conflicts=int(evaluasi_payload.get("room_conflicts") or 0),
        lecturer_conflicts=int(evaluasi_payload.get("lecturer_conflicts") or 0),
        avg_sks=float(evaluasi_payload.get("avg_sks") or 0.0),
        min_sks=int(evaluasi_payload.get("min_sks") or 0),
        max_sks=int(evaluasi_payload.get("max_sks") or 0),
        jumlah_dosen_fairness=int(evaluasi_payload.get("jumlah_dosen_fairness") or 0),
    )

    beban_dosen = [
        BebanDosen(
            dosen=str(row.get("dosen", "-")),
            total_sks=int(row.get("total_sks") or 0),
            jumlah_sesi=int(row.get("jumlah_sesi") or 0),
            jumlah_mk_unik=int(row.get("jumlah_mk_unik") or 0),
            dihitung_fairness=bool(row.get("dihitung_fairness", True)),
        )
        for row in payload.get("beban_dosen", [])
    ]

    log_konvergensi = [
        LogKonvergensi(
            generasi=int(row.get("generasi") or 0),
            best_fitness=float(row.get("best_fitness") or 0.0),
            total_conflict=int(row.get("total_conflict") or 0),
            total_penalty=row.get("total_penalty"),
        )
        for row in payload.get("log_konvergensi", [])
    ]

    return PenjadwalanResult(
        jadwal=jadwal,
        evaluasi=evaluasi,
        beban_dosen=beban_dosen,
        log_konvergensi=log_konvergensi,
        parameter=dict(payload.get("parameter") or {}),
        semester_active=str(payload.get("semester_active") or "-"),
        model_name=str(payload.get("model_name") or "MA_FIHC_ROBINHOOD"),
    )


@dataclass
class RiwayatJadwal:
    id_riwayat: str
    nama_riwayat: str
    waktu_simpan: datetime
    result_payload: dict[str, Any]
    parameter_payload: dict[str, Any] = field(default_factory=dict)
    class_opening_payload: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        nama_riwayat: str,
        result: PenjadwalanResult,
        parameter_payload: dict[str, Any] | None = None,
        class_opening_payload: list[dict[str, Any]] | None = None,
    ) -> "RiwayatJadwal":
        return cls(
            id_riwayat=f"RJ-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:6]}",
            nama_riwayat=nama_riwayat.strip(),
            waktu_simpan=datetime.now(),
            result_payload=result_to_payload(result),
            parameter_payload=parameter_payload or dict(result.parameter or {}),
            class_opening_payload=class_opening_payload or [],
        )

    @property
    def result(self) -> PenjadwalanResult:
        return result_from_payload(self.result_payload)

    def get_summary(self) -> dict[str, Any]:
        result = self.result
        evaluasi = result.evaluasi
        return {
            "id_riwayat": self.id_riwayat,
            "nama_riwayat": self.nama_riwayat,
            "waktu_simpan": self.waktu_simpan.strftime(DATE_FORMAT),
            "semester_active": result.semester_active,
            "model_name": result.model_name,
            "fitness": evaluasi.fitness,
            "total_conflict": evaluasi.total_conflict,
            "total_penalty": evaluasi.total_penalty,
            "standar_deviasi_beban": evaluasi.standar_deviasi_beban,
            "waktu_komputasi": evaluasi.waktu_komputasi,
            "jumlah_sesi": len(result.jadwal.items),
            "jumlah_beban_dosen": len(result.beban_dosen),
            "is_feasible": evaluasi.is_feasible(),
            "status_label": "Feasible" if evaluasi.is_feasible() else "Masih Ada Konflik",
            "status_class": "feasible" if evaluasi.is_feasible() else "conflict",
        }
