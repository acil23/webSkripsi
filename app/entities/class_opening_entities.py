"""Entity untuk konfigurasi pembukaan kelas, kelas paralel, dan sesi perkuliahan."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import ceil
from typing import Any


@dataclass
class KonfigurasiPembukaanKelas:
    """Merepresentasikan satu baris rekomendasi pembukaan kelas."""

    id_konfigurasi: str
    kode_mk: str
    nama_mk: str
    sks: int
    jenis_mk: str
    semester_kurikulum: str
    semester_aktif: str
    status_dibuka: bool
    mahasiswa_reguler: int
    peminat_prakrs: int
    estimasi_pengulang: int
    estimasi_peserta: int
    kapasitas_target: int
    jumlah_kelas_rekomendasi: int
    jumlah_kelas_final: int
    manual_override: bool = False
    catatan_admin: str = ""
    errors: list[str] = field(default_factory=list)

    def confirm_final_class_count(self, jumlah: int) -> bool:
        self.errors.clear()
        if jumlah < 0:
            self.errors.append("Jumlah kelas final tidak boleh negatif.")
            return False
        if jumlah > 20:
            self.errors.append("Jumlah kelas final terlalu besar untuk satu mata kuliah.")
            return False
        self.jumlah_kelas_final = int(jumlah)
        self.status_dibuka = self.jumlah_kelas_final > 0
        self.manual_override = self.jumlah_kelas_final != self.jumlah_kelas_rekomendasi
        return True

    def is_opened(self) -> bool:
        return self.status_dibuka and self.jumlah_kelas_final > 0

    @property
    def status_label(self) -> str:
        return "Dibuka" if self.is_opened() else "Tidak Dibuka"

    @property
    def status_class(self) -> str:
        return "opened" if self.is_opened() else "closed"

    def estimated_students_per_class(self) -> int:
        if self.jumlah_kelas_final <= 0:
            return 0
        return int(ceil(self.estimasi_peserta / self.jumlah_kelas_final))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id_konfigurasi": self.id_konfigurasi,
            "kode_mk": self.kode_mk,
            "nama_mk": self.nama_mk,
            "sks": self.sks,
            "jenis_mk": self.jenis_mk,
            "semester_kurikulum": self.semester_kurikulum,
            "semester_aktif": self.semester_aktif,
            "status_dibuka": self.status_dibuka,
            "status_label": self.status_label,
            "status_class": self.status_class,
            "mahasiswa_reguler": self.mahasiswa_reguler,
            "peminat_prakrs": self.peminat_prakrs,
            "estimasi_pengulang": self.estimasi_pengulang,
            "estimasi_peserta": self.estimasi_peserta,
            "kapasitas_target": self.kapasitas_target,
            "jumlah_kelas_rekomendasi": self.jumlah_kelas_rekomendasi,
            "jumlah_kelas_final": self.jumlah_kelas_final,
            "manual_override": self.manual_override,
            "catatan_admin": self.catatan_admin,
            "jumlah_mhs_per_kelas": self.estimated_students_per_class(),
            "errors": self.errors,
        }

    def to_legacy_csv_row(self) -> dict[str, Any]:
        """Format CSV kompatibel dengan data_loader algoritma lama."""
        return {
            "Kode MK": self.kode_mk,
            "Nama MK": self.nama_mk,
            "Jenis MK": self.jenis_mk,
            "Semester Kurikulum": self.semester_kurikulum,
            "Semester Aktif": self.semester_aktif,
            "Status Dibuka": "Ya" if self.is_opened() else "Tidak",
            "Mahasiswa Reguler": self.mahasiswa_reguler,
            "Peminat Pra-KRS": self.peminat_prakrs,
            "Estimasi Pengulang": self.estimasi_pengulang,
            "Estimasi Peserta": self.estimasi_peserta,
            "Kapasitas Target Kelas": self.kapasitas_target,
            "Jumlah Kelas Rekomendasi": self.jumlah_kelas_rekomendasi,
            "Jumlah Kelas Final": self.jumlah_kelas_final,
            "Manual Override": "Ya" if self.manual_override else "Tidak",
            "Catatan Admin": self.catatan_admin,
        }


@dataclass
class KelasPerkuliahan:
    """Representasi kelas paralel yang siap dipecah menjadi sesi."""

    class_id: str
    kode_mk: str
    nama_mk: str
    sks: int
    jenis_mk: str
    semester_kurikulum: str
    kelas_paralel: str
    estimasi_peserta: int

    def split_into_sessions(self) -> list["SesiPerkuliahan"]:
        if self.sks == 4:
            parts = [2, 2]
        elif self.sks == 5:
            parts = [3, 2]
        elif self.sks == 6:
            parts = [3, 3]
        else:
            parts = [self.sks]

        return [
            SesiPerkuliahan(
                session_id=f"{self.class_id}-S{index + 1}",
                class_id=self.class_id,
                kode_mk=self.kode_mk,
                nama_mk=self.nama_mk,
                kelas_paralel=self.kelas_paralel,
                urutan_sesi=index + 1,
                sks_sesi=sks_part,
            )
            for index, sks_part in enumerate(parts)
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "class_id": self.class_id,
            "kode_mk": self.kode_mk,
            "nama_mk": self.nama_mk,
            "sks": self.sks,
            "jenis_mk": self.jenis_mk,
            "semester_kurikulum": self.semester_kurikulum,
            "kelas_paralel": self.kelas_paralel,
            "estimasi_peserta": self.estimasi_peserta,
        }


@dataclass
class SesiPerkuliahan:
    """Sesi penjadwalan yang nantinya menjadi satu gen dalam kromosom."""

    session_id: str
    class_id: str
    kode_mk: str
    nama_mk: str
    kelas_paralel: str
    urutan_sesi: int
    sks_sesi: int

    def get_duration(self) -> int:
        return self.sks_sesi

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "class_id": self.class_id,
            "kode_mk": self.kode_mk,
            "nama_mk": self.nama_mk,
            "kelas_paralel": self.kelas_paralel,
            "urutan_sesi": self.urutan_sesi,
            "sks_sesi": self.sks_sesi,
        }
