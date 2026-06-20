"""Service pembentukan rekomendasi pembukaan kelas dan sesi perkuliahan."""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.paths import UPLOADED_DIR
from app.entities.class_opening_entities import (
    KelasPerkuliahan,
    KonfigurasiPembukaanKelas,
    SesiPerkuliahan,
)
from app.entities.dataset_bundle import DatasetBundle
from app.schemas.upload_schema import CANONICAL_FILENAMES


class ClassOpeningService:
    """Mengubah DatasetBundle valid menjadi konfigurasi kelas, kelas paralel, dan sesi."""

    def __init__(self, storage_dir: Path = UPLOADED_DIR):
        self.storage_dir = storage_dir

    @staticmethod
    def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df.columns = [str(column).strip() for column in df.columns]
        return df

    @staticmethod
    def _clean_text(value: Any) -> str:
        if pd.isna(value):
            return ""
        return str(value).strip()

    @staticmethod
    def _clean_code(value: Any) -> str:
        return ClassOpeningService._clean_text(value).upper()

    @staticmethod
    def _safe_int(value: Any, default: int = 0) -> int:
        try:
            if pd.isna(value):
                return default
            return int(float(value))
        except Exception:
            return default

    @staticmethod
    def _course_suffix(index: int) -> str:
        letters = ""
        idx = index
        while True:
            letters = chr(65 + (idx % 26)) + letters
            idx = idx // 26 - 1
            if idx < 0:
                break
        return letters

    @staticmethod
    def _slug_id(*parts: Any) -> str:
        raw = "_".join(str(part) for part in parts)
        return re.sub(r"[^A-Za-z0-9_]+", "_", raw).strip("_")

    def _dataset_dir(self, dataset: DatasetBundle) -> Path:
        return Path(dataset.storage_dir or self.storage_dir)

    def _read_dataset_csv(self, dataset: DatasetBundle, canonical_key: str) -> pd.DataFrame:
        path = self._dataset_dir(dataset) / CANONICAL_FILENAMES[canonical_key]
        if not path.exists():
            raise FileNotFoundError(f"File data belum tersedia: {path.name}")
        return self._normalize_columns(pd.read_csv(path))

    def _load_student_counts_by_semester(
        self,
        dataset: DatasetBundle,
        semester_active: str,
        tahun_akademik_mulai: int,
    ) -> dict[int, int]:
        df = self._read_dataset_csv(dataset, "data_jumlah_mahasiswa")
        df = df[df["Angkatan"].astype(str).str.lower() != "total"]

        semester_offset = 1 if semester_active.lower() == "ganjil" else 2
        mapping: dict[int, int] = {}

        for _, row in df.iterrows():
            angkatan = self._safe_int(row["Angkatan"])
            jumlah = self._safe_int(row["Jumlah Mahasiswa TIF"])
            if angkatan <= 0:
                continue
            semester = (tahun_akademik_mulai - angkatan) * 2 + semester_offset
            if semester > 0:
                mapping[semester] = jumlah

        return mapping

    def _load_prakrs(self, dataset: DatasetBundle) -> dict[tuple[str, str], int]:
        try:
            df = self._read_dataset_csv(dataset, "data_prakrs")
        except FileNotFoundError:
            return {}

        result: dict[tuple[str, str], int] = {}
        for _, row in df.iterrows():
            kode_mk = self._clean_code(row.get("Kode MK", ""))
            semester_active = self._clean_text(row.get("Semester Aktif", ""))
            jumlah_peminat = self._safe_int(row.get("Jumlah Peminat", 0))
            if kode_mk and semester_active:
                result[(kode_mk, semester_active)] = jumlah_peminat
        return result

    @staticmethod
    def is_course_active_for_semester(course_semester: Any, semester_active: str) -> bool:
        if isinstance(course_semester, int) or str(course_semester).strip().isdigit():
            sem = int(course_semester)
            if semester_active.lower() == "ganjil":
                return sem % 2 == 1
            return sem % 2 == 0

        sem_text = str(course_semester).strip().lower()
        if semester_active.lower() == "ganjil":
            return "ganjil" in sem_text
        return "genap" in sem_text

    def calculate_mandatory_class_opening(
        self,
        dataset: DatasetBundle,
        semester_active: str = "Ganjil",
        tahun_akademik_mulai: int = 2025,
        kapasitas_target_kelas: int = 40,
    ) -> list[KonfigurasiPembukaanKelas]:
        df_wajib = self._read_dataset_csv(dataset, "mk_wajib")
        student_counts = self._load_student_counts_by_semester(
            dataset=dataset,
            semester_active=semester_active,
            tahun_akademik_mulai=tahun_akademik_mulai,
        )

        configs: list[KonfigurasiPembukaanKelas] = []
        for _, row in df_wajib.iterrows():
            semester_kurikulum = self._safe_int(row.get("Semester", 0))
            if not self.is_course_active_for_semester(semester_kurikulum, semester_active):
                continue

            mahasiswa_reguler = int(student_counts.get(semester_kurikulum, 0))
            estimasi_pengulang = 0
            estimasi_peserta = mahasiswa_reguler + estimasi_pengulang
            jumlah_rekomendasi = max(1, math.ceil(estimasi_peserta / kapasitas_target_kelas))
            kode_mk = self._clean_code(row["Kode MK"])

            configs.append(
                KonfigurasiPembukaanKelas(
                    id_konfigurasi=self._slug_id(semester_active, "Wajib", kode_mk),
                    kode_mk=kode_mk,
                    nama_mk=self._clean_text(row["Nama MK"]),
                    sks=self._safe_int(row.get("SKS", row.get("sks", 0))),
                    jenis_mk="Wajib",
                    semester_kurikulum=str(semester_kurikulum),
                    semester_aktif=semester_active,
                    status_dibuka=True,
                    mahasiswa_reguler=mahasiswa_reguler,
                    peminat_prakrs=0,
                    estimasi_pengulang=estimasi_pengulang,
                    estimasi_peserta=estimasi_peserta,
                    kapasitas_target=kapasitas_target_kelas,
                    jumlah_kelas_rekomendasi=jumlah_rekomendasi,
                    jumlah_kelas_final=jumlah_rekomendasi,
                )
            )

        return configs

    def calculate_elective_class_opening(
        self,
        dataset: DatasetBundle,
        semester_active: str = "Ganjil",
        kapasitas_target_kelas: int = 40,
        default_peminat_pilihan: int = 40,
    ) -> list[KonfigurasiPembukaanKelas]:
        df_pilihan = self._read_dataset_csv(dataset, "mk_pilihan")
        prakrs = self._load_prakrs(dataset)

        configs: list[KonfigurasiPembukaanKelas] = []
        for _, row in df_pilihan.iterrows():
            semester_kurikulum = self._clean_text(row.get("Semester", ""))
            if not self.is_course_active_for_semester(semester_kurikulum, semester_active):
                continue

            kode_mk = self._clean_code(row["Kode MK"])
            peminat_prakrs = int(prakrs.get((kode_mk, semester_active), default_peminat_pilihan))
            estimasi_peserta = max(0, peminat_prakrs)

            if estimasi_peserta <= 0:
                jumlah_rekomendasi = 0
                status_dibuka = False
            else:
                jumlah_rekomendasi = math.ceil(estimasi_peserta / kapasitas_target_kelas)
                status_dibuka = True

            configs.append(
                KonfigurasiPembukaanKelas(
                    id_konfigurasi=self._slug_id(semester_active, "Pilihan", kode_mk),
                    kode_mk=kode_mk,
                    nama_mk=self._clean_text(row["Nama MK"]),
                    sks=self._safe_int(row.get("SKS", row.get("sks", 0))),
                    jenis_mk="Pilihan",
                    semester_kurikulum=semester_kurikulum,
                    semester_aktif=semester_active,
                    status_dibuka=status_dibuka,
                    mahasiswa_reguler=0,
                    peminat_prakrs=peminat_prakrs,
                    estimasi_pengulang=0,
                    estimasi_peserta=estimasi_peserta,
                    kapasitas_target=kapasitas_target_kelas,
                    jumlah_kelas_rekomendasi=jumlah_rekomendasi,
                    jumlah_kelas_final=jumlah_rekomendasi,
                )
            )

        return configs

    def generate_recommendation(
        self,
        dataset: DatasetBundle,
        semester_active: str = "Ganjil",
        tahun_akademik_mulai: int = 2025,
        kapasitas_target_kelas: int = 40,
        default_peminat_pilihan: int = 40,
    ) -> list[KonfigurasiPembukaanKelas]:
        mandatory = self.calculate_mandatory_class_opening(
            dataset=dataset,
            semester_active=semester_active,
            tahun_akademik_mulai=tahun_akademik_mulai,
            kapasitas_target_kelas=kapasitas_target_kelas,
        )
        elective = self.calculate_elective_class_opening(
            dataset=dataset,
            semester_active=semester_active,
            kapasitas_target_kelas=kapasitas_target_kelas,
            default_peminat_pilihan=default_peminat_pilihan,
        )
        configs = mandatory + elective
        return sorted(configs, key=lambda item: (item.jenis_mk != "Wajib", str(item.semester_kurikulum), item.kode_mk))

    def build_parallel_classes(self, configs: list[KonfigurasiPembukaanKelas]) -> list[KelasPerkuliahan]:
        classes: list[KelasPerkuliahan] = []
        for config in configs:
            if not config.is_opened():
                continue
            jumlah_per_kelas = config.estimated_students_per_class()
            for index in range(config.jumlah_kelas_final):
                parallel = self._course_suffix(index)
                class_id = self._slug_id(config.kode_mk, parallel)
                classes.append(
                    KelasPerkuliahan(
                        class_id=class_id,
                        kode_mk=config.kode_mk,
                        nama_mk=config.nama_mk,
                        sks=config.sks,
                        jenis_mk=config.jenis_mk,
                        semester_kurikulum=config.semester_kurikulum,
                        kelas_paralel=parallel,
                        estimasi_peserta=jumlah_per_kelas,
                    )
                )
        return classes

    def split_class_into_sessions(self, classes: list[KelasPerkuliahan]) -> list[SesiPerkuliahan]:
        sessions: list[SesiPerkuliahan] = []
        for class_item in classes:
            sessions.extend(class_item.split_into_sessions())
        return sessions

    def save_config_to_csv(
        self,
        configs: list[KonfigurasiPembukaanKelas],
        semester_active: str,
        output_dir: Path | None = None,
    ) -> Path:
        output_dir = output_dir or self.storage_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"Konfigurasi_Pembukaan_Kelas_{semester_active}.csv"
        df = pd.DataFrame([config.to_legacy_csv_row() for config in configs])
        if not df.empty:
            df = df.sort_values(
                by=["Jenis MK", "Semester Kurikulum", "Kode MK"],
                ascending=[False, True, True],
                kind="stable",
            )
        df.to_csv(path, index=False)
        return path

    @staticmethod
    def build_summary(
        configs: list[KonfigurasiPembukaanKelas],
        classes: list[KelasPerkuliahan] | None = None,
        sessions: list[SesiPerkuliahan] | None = None,
    ) -> dict[str, Any]:
        opened_configs = [config for config in configs if config.is_opened()]
        total_estimasi_peserta = sum(config.estimasi_peserta for config in opened_configs)
        total_kelas_final = sum(config.jumlah_kelas_final for config in opened_configs)
        total_rekomendasi = sum(config.jumlah_kelas_rekomendasi for config in configs)
        manual_overrides = sum(1 for config in configs if config.manual_override)
        return {
            "total_mata_kuliah": len(configs),
            "total_mata_kuliah_dibuka": len(opened_configs),
            "total_kelas_rekomendasi": total_rekomendasi,
            "total_kelas_final": total_kelas_final,
            "total_estimasi_peserta": total_estimasi_peserta,
            "total_kelas_terbentuk": len(classes or []),
            "total_sesi_terbentuk": len(sessions or []),
            "manual_overrides": manual_overrides,
            "status_konfigurasi": "Tersimpan" if classes is not None and sessions is not None else "Siap Ditinjau",
        }
