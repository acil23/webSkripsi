"""Control layer utama untuk alur penjadwalan.

Tahap 3 menambahkan orkestrasi UC-02 Mengelola Konfigurasi Pembukaan Kelas.
Controller ini menyimpan currentClassOpening, currentClasses, dan currentSessions
ke AppState setelah Admin menyimpan konfigurasi final.
"""

from __future__ import annotations

from typing import Any

from app.controllers.class_opening_controller import ClassOpeningController
from app.controllers.data_validation_controller import DataValidationController
from app.core.app_state import app_state
from app.core.config import config
from app.entities.class_opening_entities import KonfigurasiPembukaanKelas
from app.entities.dataset_bundle import DatasetBundle
from app.schemas.upload_schema import UPLOAD_DATASETS
from app.services.data_loader_service import UploadedCsvPayload


class SchedulingController:
    def __init__(self):
        self.data_validation_controller = DataValidationController()
        self.class_opening_controller = ClassOpeningController()

    def get_dashboard_context(self) -> dict:
        return {
            "page_title": "Dashboard Penjadwalan",
            "welcome_title": "Selamat Datang, Admin Program Studi",
            "system_name": config.app_name,
            "institution_name": config.institution_name,
            "active_algorithm": config.active_algorithm,
            "system_status": "Sistem siap digunakan",
            "workflow_steps": [
                "Unggah Data",
                "Konfigurasi Kelas",
                "Parameter Algoritma",
                "Eksekusi",
                "Hasil",
            ],
        }

    def get_placeholder_context(self, title: str, description: str) -> dict:
        return {
            "page_title": title,
            "description": description,
            "active_algorithm": config.active_algorithm,
        }

    # ======================================================
    # UC-01 Mengunggah Data Masukan
    # ======================================================
    def get_upload_page_context(self, alert: dict | None = None) -> dict:
        dataset = self.get_current_dataset()
        if dataset is None:
            dataset = self.data_validation_controller.get_empty_dataset_bundle()

        status_by_key = {item["key"]: item for item in dataset.to_view_data()["datasets"]}

        return {
            "page_title": "Manajemen Data Masukan",
            "description": (
                "Kelola dan unggah data master yang diperlukan untuk proses penjadwalan. "
                "Pastikan semua data divalidasi sebelum melanjutkan ke tahap berikutnya."
            ),
            "upload_datasets": UPLOAD_DATASETS,
            "status_by_key": status_by_key,
            "dataset_view": dataset.to_view_data(),
            "alert": alert,
        }

    def upload_data(self, payloads: dict[str, list[UploadedCsvPayload]]) -> DatasetBundle:
        validated_dataset = self.data_validation_controller.validate_uploaded_data(payloads)
        self.set_current_dataset(validated_dataset)
        # Reset tahapan setelah upload baru agar konfigurasi lama tidak dipakai untuk dataset baru.
        app_state.current_class_opening = None
        app_state.current_classes = None
        app_state.current_sessions = None
        app_state.current_result = None
        return validated_dataset

    def get_current_dataset(self) -> DatasetBundle | None:
        return app_state.current_dataset

    def set_current_dataset(self, dataset: DatasetBundle) -> bool:
        app_state.current_dataset = dataset
        return True

    # ======================================================
    # UC-02 Mengelola Konfigurasi Pembukaan Kelas
    # ======================================================
    def get_class_opening_page_context(
        self,
        semester_active: str = "Ganjil",
        jenis_mk: str = "Semua",
        search: str = "",
        alert: dict | None = None,
    ) -> dict:
        dataset = self.get_current_dataset()
        configs: list[KonfigurasiPembukaanKelas] = []
        classes = app_state.current_classes
        sessions = app_state.current_sessions

        if dataset and dataset.is_valid():
            if not app_state.current_class_opening:
                configs = self.generate_class_opening(semester_active=semester_active)
            else:
                configs = list(app_state.current_class_opening)
                if configs and configs[0].semester_aktif.lower() != semester_active.lower():
                    configs = self.generate_class_opening(semester_active=semester_active)
        else:
            alert = alert or {
                "type": "error",
                "title": "Data belum valid",
                "message": "Unggah dan validasi seluruh data masukan sebelum mengelola konfigurasi kelas.",
            }

        filtered_configs = self.filter_class_opening(configs, jenis_mk=jenis_mk, search=search)
        summary = self.class_opening_controller.build_summary(configs, classes, sessions)

        return {
            "page_title": "Konfigurasi Pembukaan Kelas",
            "description": "Tinjau dan sesuaikan rekomendasi pembukaan kelas untuk setiap mata kuliah sebelum menjalankan algoritma penjadwalan.",
            "semester_active": semester_active,
            "jenis_mk": jenis_mk,
            "search": search,
            "configs": [config.to_dict() for config in filtered_configs],
            "all_configs_count": len(configs),
            "summary": summary,
            "is_dataset_ready": bool(dataset and dataset.is_valid()),
            "is_class_opening_saved": bool(app_state.current_classes is not None and app_state.current_sessions is not None),
            "alert": alert,
        }

    def generate_class_opening(self, semester_active: str = "Ganjil") -> list[KonfigurasiPembukaanKelas]:
        dataset = self.get_current_dataset()
        configs = self.class_opening_controller.generate_recommendation(
            dataset=dataset,
            semester_active=semester_active,
        )
        app_state.current_class_opening = configs
        app_state.current_classes = None
        app_state.current_sessions = None
        return configs

    def update_class_opening(self, form_data: dict[str, Any], semester_active: str = "Ganjil") -> bool:
        if not app_state.current_class_opening:
            self.generate_class_opening(semester_active=semester_active)

        configs = self.class_opening_controller.update_config_from_form(
            current_configs=list(app_state.current_class_opening),
            form_data=form_data,
        )

        has_error = any(config.errors for config in configs)
        if has_error:
            app_state.current_class_opening = configs
            return False

        classes = self.class_opening_controller.build_parallel_classes(configs)
        sessions = self.class_opening_controller.build_sessions(classes)
        self.class_opening_controller.save_active_config(configs, semester_active=semester_active)
        self.set_current_class_opening(configs, classes, sessions)
        return True

    def set_current_class_opening(self, configs, classes, sessions) -> bool:
        app_state.current_class_opening = configs
        app_state.current_classes = classes
        app_state.current_sessions = sessions
        app_state.current_result = None
        return True

    def get_current_class_opening(self):
        return app_state.current_class_opening

    def filter_class_opening(
        self,
        configs: list[KonfigurasiPembukaanKelas],
        jenis_mk: str = "Semua",
        search: str = "",
    ) -> list[KonfigurasiPembukaanKelas]:
        filtered = configs
        if jenis_mk and jenis_mk.lower() != "semua":
            filtered = [config for config in filtered if config.jenis_mk.lower() == jenis_mk.lower()]
        if search:
            keyword = search.strip().lower()
            filtered = [
                config
                for config in filtered
                if keyword in config.kode_mk.lower() or keyword in config.nama_mk.lower()
            ]
        return filtered
