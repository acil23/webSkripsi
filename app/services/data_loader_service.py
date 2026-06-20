"""Service untuk membaca, menyimpan, dan memvalidasi data CSV masukan."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Iterable

import pandas as pd

from app.core.paths import UPLOADED_DIR
from app.entities.dataset_bundle import DatasetBundle, DatasetValidationResult
from app.schemas.upload_schema import CANONICAL_FILENAMES, MAX_UPLOAD_SIZE_BYTES, REQUIRED_COLUMNS, UPLOAD_DATASETS


@dataclass
class UploadedCsvPayload:
    filename: str
    content: bytes


class DataLoaderService:
    """Menyediakan operasi CSV yang dibutuhkan oleh DataValidationController."""

    def __init__(self, storage_dir: Path = UPLOADED_DIR):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def normalize_columns(columns: Iterable[object]) -> list[str]:
        return [str(column).strip() for column in columns]

    @staticmethod
    def _empty_result(key: str, label: str) -> DatasetValidationResult:
        return DatasetValidationResult(key=key, label=label, status="Belum Diunggah")

    def create_empty_bundle(self) -> DatasetBundle:
        datasets = {
            item["key"]: self._empty_result(item["key"], item["label"])
            for item in UPLOAD_DATASETS
        }
        return DatasetBundle(datasets=datasets, storage_dir=self.storage_dir)

    def validate_and_store_payloads(self, payloads: dict[str, list[UploadedCsvPayload]]) -> DatasetBundle:
        """Validasi seluruh upload dan simpan file valid dengan nama kanonik."""
        bundle = self.create_empty_bundle()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        bundle.uploaded_at = timestamp

        self._validate_course_files(payloads.get("data_mata_kuliah", []), bundle)

        single_file_map = {
            "data_dosen": "data_dosen",
            "data_preferensi_dosen": "data_preferensi_dosen",
            "data_ruang_kelas": "data_ruang_kelas",
            "data_slot_waktu": "data_slot_waktu",
            "data_jumlah_mahasiswa": "data_jumlah_mahasiswa",
            "data_prakrs": "data_prakrs",
        }

        for form_key, dataset_key in single_file_map.items():
            files = payloads.get(form_key, [])
            label = bundle.datasets[dataset_key].label
            if not files:
                continue
            if len(files) > 1:
                bundle.datasets[dataset_key] = DatasetValidationResult(
                    key=dataset_key,
                    label=label,
                    status="Error",
                    errors=["Hanya satu file CSV yang diperbolehkan untuk data ini."],
                )
                continue
            result = self.validate_single_csv(
                payload=files[0],
                dataset_key=dataset_key,
                label=label,
                required_columns=REQUIRED_COLUMNS[dataset_key],
                canonical_filename=CANONICAL_FILENAMES[dataset_key],
            )
            bundle.datasets[dataset_key] = result

        self._cross_validate(bundle)
        return bundle

    def validate_single_csv(
        self,
        payload: UploadedCsvPayload,
        dataset_key: str,
        label: str,
        required_columns: list[str],
        canonical_filename: str,
    ) -> DatasetValidationResult:
        result = DatasetValidationResult(
            key=dataset_key,
            label=label,
            filename=payload.filename,
            required_columns=required_columns,
        )

        if not payload.filename:
            result.status = "Belum Diunggah"
            return result

        if not payload.filename.lower().endswith(".csv"):
            result.status = "Error"
            result.errors.append("Format file harus .csv.")
            return result

        if len(payload.content) > MAX_UPLOAD_SIZE_BYTES:
            result.status = "Error"
            result.errors.append("Ukuran file melebihi batas 2MB.")
            return result

        try:
            df = pd.read_csv(BytesIO(payload.content))
            df.columns = self.normalize_columns(df.columns)
        except Exception as exc:
            result.status = "Error"
            result.errors.append(f"File CSV tidak dapat dibaca: {exc}")
            return result

        result.row_count = int(len(df))
        result.column_count = int(len(df.columns))
        result.detected_columns = list(df.columns)

        if df.empty:
            result.errors.append("File CSV tidak boleh kosong.")

        missing = [column for column in required_columns if column not in df.columns]
        result.missing_columns = missing
        if missing:
            result.errors.append("Kolom wajib belum lengkap: " + ", ".join(missing))

        if result.errors:
            result.status = "Error"
            return result

        saved_path = self.storage_dir / canonical_filename
        saved_path.write_bytes(payload.content)
        result.saved_path = str(saved_path)
        result.status = "Valid"
        return result

    def _validate_course_files(self, course_files: list[UploadedCsvPayload], bundle: DatasetBundle) -> None:
        label = bundle.datasets["data_mata_kuliah"].label
        required_wajib = REQUIRED_COLUMNS["mk_wajib"]
        required_pilihan = REQUIRED_COLUMNS["mk_pilihan"]

        combined_result = DatasetValidationResult(
            key="data_mata_kuliah",
            label=label,
            required_columns=sorted(set(required_wajib + required_pilihan)),
        )

        if not course_files:
            bundle.datasets["data_mata_kuliah"] = combined_result
            return

        if len(course_files) > 2:
            combined_result.status = "Error"
            combined_result.errors.append("Data Mata Kuliah menerima maksimal dua file: MK wajib dan MK pilihan.")
            bundle.datasets["data_mata_kuliah"] = combined_result
            return

        detected: dict[str, DatasetValidationResult] = {}
        for payload in course_files:
            course_type = self._detect_course_type(payload)
            if course_type is None:
                combined_result.errors.append(
                    f"{payload.filename}: file tidak dikenali sebagai data MK wajib atau MK pilihan."
                )
                continue

            if course_type in detected:
                combined_result.errors.append(f"Terdapat lebih dari satu file untuk {course_type.replace('_', ' ')}.")
                continue

            result = self.validate_single_csv(
                payload=payload,
                dataset_key=course_type,
                label="Data MK Wajib" if course_type == "mk_wajib" else "Data MK Pilihan",
                required_columns=REQUIRED_COLUMNS[course_type],
                canonical_filename=CANONICAL_FILENAMES[course_type],
            )
            detected[course_type] = result

        missing_types = [key for key in ["mk_wajib", "mk_pilihan"] if key not in detected]
        if missing_types:
            combined_result.errors.append(
                "File mata kuliah belum lengkap: "
                + ", ".join("MK wajib" if key == "mk_wajib" else "MK pilihan" for key in missing_types)
                + "."
            )

        for result in detected.values():
            combined_result.row_count += result.row_count
            combined_result.column_count += result.column_count
            combined_result.detected_columns.extend(result.detected_columns)
            if result.filename:
                combined_result.filename = (
                    result.filename if not combined_result.filename else f"{combined_result.filename}; {result.filename}"
                )
            if result.saved_path:
                combined_result.saved_path = (
                    result.saved_path if not combined_result.saved_path else f"{combined_result.saved_path}; {result.saved_path}"
                )
            combined_result.errors.extend(result.errors)
            combined_result.warnings.extend(result.warnings)
            combined_result.missing_columns.extend(result.missing_columns)

        if combined_result.errors:
            combined_result.status = "Error"
        else:
            combined_result.status = "Valid"

        bundle.datasets["data_mata_kuliah"] = combined_result

    def _detect_course_type(self, payload: UploadedCsvPayload) -> str | None:
        filename = payload.filename.lower()
        if "pilihan" in filename:
            return "mk_pilihan"
        if "wajib" in filename:
            return "mk_wajib"

        try:
            df = pd.read_csv(BytesIO(payload.content), nrows=5)
            df.columns = self.normalize_columns(df.columns)
        except Exception:
            return None

        if "Wajib / Pilihan" in df.columns:
            return "mk_pilihan"

        if all(column in df.columns for column in REQUIRED_COLUMNS["mk_wajib"]):
            return "mk_wajib"

        return None

    def _read_saved_csv(self, canonical_key: str) -> pd.DataFrame | None:
        path = self.storage_dir / CANONICAL_FILENAMES[canonical_key]
        if not path.exists():
            return None
        df = pd.read_csv(path)
        df.columns = self.normalize_columns(df.columns)
        return df

    def _cross_validate(self, bundle: DatasetBundle) -> None:
        """Validasi relasional ringan. Peringatan tidak menggagalkan upload."""
        if not bundle.is_complete() or not all(item.status != "Error" for item in bundle.datasets.values()):
            return

        try:
            mk_wajib = self._read_saved_csv("mk_wajib")
            mk_pilihan = self._read_saved_csv("mk_pilihan")
            preferensi = self._read_saved_csv("data_preferensi_dosen")
            prakrs = self._read_saved_csv("data_prakrs")
        except Exception as exc:
            bundle.cross_validation_messages.append(f"Validasi relasional belum dapat dilakukan: {exc}")
            return

        if mk_wajib is None or mk_pilihan is None:
            return

        course_codes = set(mk_wajib["Kode MK"].astype(str).str.strip().str.upper())
        course_codes.update(mk_pilihan["Kode MK"].astype(str).str.strip().str.upper())

        if preferensi is not None:
            pref_codes = set(preferensi["Kode MK"].astype(str).str.strip().str.upper())
            unknown_pref = sorted(pref_codes - course_codes)
            if unknown_pref:
                bundle.cross_validation_messages.append(
                    f"Peringatan: {len(unknown_pref)} kode MK pada preferensi tidak ditemukan di master MK."
                )

        if prakrs is not None:
            elective_codes = set(mk_pilihan["Kode MK"].astype(str).str.strip().str.upper())
            prakrs_codes = set(prakrs["Kode MK"].astype(str).str.strip().str.upper())
            unknown_prakrs = sorted(prakrs_codes - elective_codes)
            if unknown_prakrs:
                bundle.cross_validation_messages.append(
                    f"Peringatan: {len(unknown_prakrs)} kode MK pada Pra-KRS tidak ditemukan di master MK pilihan."
                )
