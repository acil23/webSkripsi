"""Value object DatasetBundle untuk menyimpan status data masukan.

DatasetBundle merepresentasikan kumpulan data akademik yang telah diunggah
oleh Admin Program Studi. Pada Tahap 2, objek ini berfokus pada validasi
kelengkapan dan struktur CSV. Isi data rinci tetap disimpan sebagai file CSV
pada folder data/uploaded agar dapat digunakan pada tahap konfigurasi kelas
serta integrasi engine algoritma.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class DatasetValidationResult:
    """Status validasi untuk satu jenis data masukan."""

    key: str
    label: str
    status: str = "Belum Diunggah"
    filename: str | None = None
    saved_path: str | None = None
    row_count: int = 0
    column_count: int = 0
    required_columns: list[str] = field(default_factory=list)
    detected_columns: list[str] = field(default_factory=list)
    missing_columns: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return self.status == "Valid" and not self.errors

    @property
    def badge_class(self) -> str:
        if self.status == "Valid":
            return "valid"
        if self.status == "Error":
            return "error"
        return "pending"

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "status": self.status,
            "filename": self.filename,
            "saved_path": self.saved_path,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "required_columns": self.required_columns,
            "detected_columns": self.detected_columns,
            "missing_columns": self.missing_columns,
            "errors": self.errors,
            "warnings": self.warnings,
            "is_valid": self.is_valid,
            "badge_class": self.badge_class,
        }


@dataclass
class DatasetBundle:
    """Kumpulan status dan lokasi file data masukan penjadwalan."""

    datasets: dict[str, DatasetValidationResult]
    uploaded_at: str | None = None
    storage_dir: Path | None = None
    cross_validation_messages: list[str] = field(default_factory=list)

    def is_complete(self) -> bool:
        return all(item.status != "Belum Diunggah" for item in self.datasets.values())

    def is_valid(self) -> bool:
        return self.is_complete() and all(item.is_valid for item in self.datasets.values())

    def get_status_summary(self) -> dict[str, int]:
        summary = {"Valid": 0, "Belum Diunggah": 0, "Error": 0}
        for item in self.datasets.values():
            summary[item.status] = summary.get(item.status, 0) + 1
        return summary

    def to_view_data(self) -> dict[str, Any]:
        return {
            "is_complete": self.is_complete(),
            "is_valid": self.is_valid(),
            "summary": self.get_status_summary(),
            "datasets": [item.to_dict() for item in self.datasets.values()],
            "uploaded_at": self.uploaded_at,
            "cross_validation_messages": self.cross_validation_messages,
        }
