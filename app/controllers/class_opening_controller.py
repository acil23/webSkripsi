"""Controller UC-02 Mengelola Konfigurasi Pembukaan Kelas."""

from __future__ import annotations

from typing import Any

from app.entities.class_opening_entities import (
    KelasPerkuliahan,
    KonfigurasiPembukaanKelas,
    SesiPerkuliahan,
)
from app.entities.dataset_bundle import DatasetBundle
from app.services.class_opening_service import ClassOpeningService


class ClassOpeningController:
    def __init__(self):
        self.class_opening_service = ClassOpeningService()

    def generate_recommendation(
        self,
        dataset: DatasetBundle,
        semester_active: str = "Ganjil",
        tahun_akademik_mulai: int = 2025,
        kapasitas_target_kelas: int = 40,
    ) -> list[KonfigurasiPembukaanKelas]:
        if dataset is None or not dataset.is_valid():
            raise ValueError("Data masukan belum valid. Unggah dan validasi data terlebih dahulu.")
        return self.class_opening_service.generate_recommendation(
            dataset=dataset,
            semester_active=semester_active,
            tahun_akademik_mulai=tahun_akademik_mulai,
            kapasitas_target_kelas=kapasitas_target_kelas,
        )

    def confirm_final_class_count(self, configs: list[KonfigurasiPembukaanKelas]) -> bool:
        for config in configs:
            if config.jumlah_kelas_final < 0:
                return False
        return True

    def update_config_from_form(
        self,
        current_configs: list[KonfigurasiPembukaanKelas],
        form_data: dict[str, Any],
    ) -> list[KonfigurasiPembukaanKelas]:
        config_by_id = {config.id_konfigurasi: config for config in current_configs}

        for config_id, config in config_by_id.items():
            final_key = f"jumlah_kelas_final_{config_id}"
            note_key = f"catatan_admin_{config_id}"

            raw_final = form_data.get(final_key, config.jumlah_kelas_final)
            try:
                final_count = int(raw_final)
            except Exception:
                config.errors = ["Jumlah kelas final harus berupa bilangan bulat."]
                continue

            config.confirm_final_class_count(final_count)
            config.catatan_admin = str(form_data.get(note_key, config.catatan_admin) or "").strip()

        return list(config_by_id.values())

    def build_parallel_classes(self, configs: list[KonfigurasiPembukaanKelas]) -> list[KelasPerkuliahan]:
        return self.class_opening_service.build_parallel_classes(configs)

    def build_sessions(self, classes: list[KelasPerkuliahan]) -> list[SesiPerkuliahan]:
        return self.class_opening_service.split_class_into_sessions(classes)

    def save_active_config(self, configs: list[KonfigurasiPembukaanKelas], semester_active: str):
        return self.class_opening_service.save_config_to_csv(configs, semester_active)

    def build_summary(
        self,
        configs: list[KonfigurasiPembukaanKelas],
        classes: list[KelasPerkuliahan] | None = None,
        sessions: list[SesiPerkuliahan] | None = None,
    ) -> dict[str, Any]:
        return self.class_opening_service.build_summary(configs, classes, sessions)
