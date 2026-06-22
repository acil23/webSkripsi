"""Control layer utama untuk alur penjadwalan.

Tahap 5 menambahkan orkestrasi UC-04 Mengeksekusi Penjadwalan dengan
membungkus engine Memetic Algorithm lama melalui GAEngineService. Controller ini
menjaga prasyarat eksekusi, menjalankan engine, dan menyimpan currentResult ke
AppState agar dapat digunakan pada Tahap 6.
"""

from __future__ import annotations

from typing import Any
import threading

from app.controllers.class_opening_controller import ClassOpeningController
from app.controllers.data_validation_controller import DataValidationController
from app.controllers.parameter_controller import ParameterController
from app.core.app_state import app_state
from app.core.config import config
from app.core.paths import UPLOADED_DIR
from app.entities.algorithm_entities import ParameterAlgoritma
from app.entities.class_opening_entities import KonfigurasiPembukaanKelas
from app.entities.dataset_bundle import DatasetBundle
from app.entities.result_entities import PenjadwalanResult
from app.schemas.parameter_schema import PARAMETER_FIELDS
from app.schemas.upload_schema import UPLOAD_DATASETS
from app.services.data_loader_service import UploadedCsvPayload
from app.services.csv_exporter import CSVExporter
from app.services.ga_engine_service import GAEngineService
from app.services.visualization_service import VisualizationService


class SchedulingController:
    def __init__(self):
        self.data_validation_controller = DataValidationController()
        self.class_opening_controller = ClassOpeningController()
        self.parameter_controller = ParameterController()
        self.ga_engine_service = GAEngineService()
        self.visualization_service = VisualizationService()
        self.csv_exporter = CSVExporter()

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
        # Reset tahapan setelah upload baru agar konfigurasi/parameter/hasil lama tidak bias.
        app_state.current_class_opening = None
        app_state.current_classes = None
        app_state.current_sessions = None
        app_state.current_result = None
        app_state.execution_status = {}
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
        app_state.current_result = None
        app_state.execution_status = {}
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
        app_state.execution_status = {}
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

    # ======================================================
    # UC-03 Mengatur Parameter Algoritma
    # ======================================================
    def get_parameter_page_context(
        self,
        draft_parameter: ParameterAlgoritma | None = None,
        alert: dict | None = None,
    ) -> dict:
        current_parameter = self.get_current_parameter()
        parameter = draft_parameter or current_parameter or ParameterAlgoritma.default()
        is_saved = bool(current_parameter and current_parameter.is_valid())
        dataset_ready = bool(app_state.current_dataset and app_state.current_dataset.is_valid())
        class_opening_ready = bool(app_state.current_sessions)

        return {
            "page_title": "Pengaturan Parameter Algoritma",
            "description": "Halaman ini digunakan untuk mengatur parameter algoritma sebelum menjalankan proses optimasi penjadwalan.",
            "parameter_fields": PARAMETER_FIELDS,
            "parameter": parameter,
            "summary_rows": parameter.to_summary_rows(),
            "is_parameter_valid": parameter.is_valid(),
            "is_parameter_saved": is_saved,
            "is_dataset_ready": dataset_ready,
            "is_class_opening_ready": class_opening_ready,
            "algorithm_label": config.active_algorithm,
            "alert": alert,
        }

    def save_parameters(self, parameter_input: dict[str, Any]) -> ParameterAlgoritma:
        app_state.current_result = None
        app_state.execution_status = {}
        return self.parameter_controller.save_parameter(parameter_input)

    def get_current_parameter(self) -> ParameterAlgoritma | None:
        return self.parameter_controller.get_parameter()

    # ======================================================
    # UC-04 Mengeksekusi Penjadwalan
    # ======================================================
    def check_execution_prerequisites(self) -> dict[str, Any]:
        dataset_ready = bool(app_state.current_dataset and app_state.current_dataset.is_valid())
        class_opening_saved = bool(app_state.current_class_opening and app_state.current_classes is not None)
        parameter = self.get_current_parameter()
        parameter_valid = bool(parameter and parameter.is_valid())
        sessions_formed = bool(app_state.current_sessions)

        items = [
            {"label": "Data Masukan Valid", "ready": dataset_ready},
            {"label": "Konfigurasi Pembukaan Kelas Tersimpan", "ready": class_opening_saved},
            {"label": "Parameter Algoritma Valid", "ready": parameter_valid},
            {"label": "Sesi Perkuliahan Terbentuk", "ready": sessions_formed},
        ]
        return {
            "items": items,
            "is_complete": all(item["ready"] for item in items),
            "dataset_ready": dataset_ready,
            "class_opening_saved": class_opening_saved,
            "parameter_valid": parameter_valid,
            "sessions_formed": sessions_formed,
        }

    def get_execution_page_context(self, alert: dict | None = None) -> dict:
        prerequisites = self.check_execution_prerequisites()
        current_parameter = self.get_current_parameter()
        current_result = self.get_current_result()
        status = app_state.execution_status or {
            "state": "idle",
            "label": "Belum Berjalan",
            "progress": 0,
            "current_generation": 0,
            "max_generations": current_parameter.max_generations if current_parameter else 0,
            "best_fitness": None,
            "total_conflict": None,
            "duration": None,
        }

        summary = None
        if current_result and current_result.is_ready_to_display():
            summary = current_result.to_summary()

        return {
            "page_title": "Eksekusi Penjadwalan",
            "description": "Halaman ini digunakan untuk menjalankan optimasi penjadwalan menggunakan Memetic Algorithm.",
            "algorithm_label": config.active_algorithm,
            "prerequisites": prerequisites,
            "parameter": current_parameter,
            "execution_status": status,
            "result_summary": summary,
            "total_sessions": len(app_state.current_sessions or []),
            "total_classes": len(app_state.current_classes or []),
            "semester_active": self._get_active_semester(),
            "alert": alert,
        }

    def start_scheduling_execution(self) -> None:
        """Memulai eksekusi secara background agar halaman web tidak menunggu proses panjang."""
        current_state = (app_state.execution_status or {}).get("state")
        if current_state == "running":
            raise ValueError("Proses penjadwalan sedang berjalan. Tunggu hingga proses selesai sebelum menjalankan ulang.")

        prerequisite = self.check_execution_prerequisites()
        if not prerequisite["is_complete"]:
            missing = [item["label"] for item in prerequisite["items"] if not item["ready"]]
            raise ValueError("Prasyarat eksekusi belum lengkap: " + ", ".join(missing))

        semester_active = self._get_active_semester()
        parameter = self.get_current_parameter()
        app_state.current_result = None
        app_state.execution_status = {
            "state": "running",
            "label": "Sedang Berjalan",
            "progress": 1,
            "current_generation": 0,
            "max_generations": parameter.max_generations if parameter else 0,
            "best_fitness": None,
            "total_conflict": None,
            "duration": None,
        }

        thread = threading.Thread(
            target=self._run_execution_worker,
            args=(parameter, semester_active),
            daemon=True,
        )
        thread.start()

    def _run_execution_worker(self, parameter: ParameterAlgoritma, semester_active: str) -> None:
        def on_progress(event: dict[str, Any]) -> None:
            max_generations = int(event.get("max_generations", parameter.max_generations or 1) or 1)
            generation = int(event.get("generation", 0))
            progress = max(1, min(99, int((generation / max_generations) * 100)))
            app_state.execution_status = {
                "state": "running",
                "label": "Sedang Berjalan",
                "progress": progress,
                "current_generation": generation,
                "max_generations": max_generations,
                "best_fitness": event.get("best_fitness"),
                "total_conflict": event.get("total_conflict"),
                "duration": None,
            }

        try:
            result = self.ga_engine_service.execute(
                parameter=parameter,
                semester_active=semester_active,
                data_dir=UPLOADED_DIR,
                class_config_path=UPLOADED_DIR / f"Konfigurasi_Pembukaan_Kelas_{semester_active}.csv",
                progress_callback=on_progress,
            )
            self.set_current_result(result)
            last_log = result.log_konvergensi[-1] if result.log_konvergensi else None
            app_state.execution_status = {
                "state": "finished",
                "label": "Eksekusi Selesai",
                "progress": 100,
                "current_generation": last_log.generasi if last_log else parameter.max_generations,
                "max_generations": parameter.max_generations,
                "best_fitness": result.evaluasi.fitness,
                "total_conflict": result.evaluasi.total_conflict,
                "duration": result.evaluasi.waktu_komputasi,
            }
        except Exception as exc:
            app_state.execution_status = {
                "state": "failed",
                "label": "Eksekusi Gagal",
                "progress": 0,
                "current_generation": 0,
                "max_generations": parameter.max_generations if parameter else 0,
                "best_fitness": None,
                "total_conflict": None,
                "duration": None,
                "error": str(exc),
            }

    def execute_scheduling(self) -> PenjadwalanResult:
        """Eksekusi sinkron untuk kebutuhan pengujian internal/service, bukan jalur utama UI."""
        prerequisite = self.check_execution_prerequisites()
        if not prerequisite["is_complete"]:
            missing = [item["label"] for item in prerequisite["items"] if not item["ready"]]
            raise ValueError("Prasyarat eksekusi belum lengkap: " + ", ".join(missing))

        semester_active = self._get_active_semester()
        parameter = self.get_current_parameter()
        result = self.ga_engine_service.execute(
            parameter=parameter,
            semester_active=semester_active,
            data_dir=UPLOADED_DIR,
            class_config_path=UPLOADED_DIR / f"Konfigurasi_Pembukaan_Kelas_{semester_active}.csv",
        )
        self.set_current_result(result)
        return result

    def set_current_result(self, result: PenjadwalanResult) -> bool:
        app_state.current_result = result
        return True

    def get_current_result(self) -> PenjadwalanResult | None:
        return app_state.current_result


    # ======================================================
    # UC-05 Melihat Hasil Jadwal dan Evaluasi
    # ======================================================
    def get_result_page_context(self, alert: dict | None = None) -> dict:
        current_result = self.get_current_result()
        if not current_result or not current_result.is_ready_to_display():
            return {
                "page_title": "Hasil Jadwal dan Evaluasi",
                "description": "Halaman ini menampilkan hasil jadwal yang dihasilkan dan evaluasi dari Memetic Algorithm.",
                "has_result": False,
                "result_view": None,
                "alert": alert or {
                    "type": "info",
                    "title": "Hasil belum tersedia",
                    "message": "Jalankan proses eksekusi penjadwalan terlebih dahulu sebelum melihat hasil.",
                },
            }

        result_view = self.visualization_service.build_result_view_data(current_result)
        return {
            "page_title": "Hasil Jadwal dan Evaluasi",
            "description": "Halaman ini menampilkan hasil jadwal yang dihasilkan dan evaluasi dari Memetic Algorithm.",
            "has_result": True,
            "result_view": result_view,
            "alert": alert,
        }

    def get_result_api_data(self) -> dict[str, Any]:
        current_result = self.get_current_result()
        if not current_result or not current_result.is_ready_to_display():
            return {"has_result": False, "message": "Hasil jadwal belum tersedia."}
        return {
            "has_result": True,
            "data": self.visualization_service.build_result_view_data(current_result),
        }


    # ======================================================
    # UC-06 Mengekspor Hasil Penjadwalan
    # ======================================================
    def get_export_page_context(self, alert: dict | None = None) -> dict:
        current_result = self.get_current_result()
        has_result = bool(current_result and current_result.is_ready_to_display())
        export_manifest = self.csv_exporter.get_export_manifest(current_result) if has_result else []
        summary = current_result.to_summary() if has_result else None

        return {
            "page_title": "Ekspor Hasil Penjadwalan",
            "description": "Halaman ini digunakan untuk mengunduh data hasil penjadwalan dan data evaluasi yang telah dihasilkan.",
            "has_result": has_result,
            "summary": summary,
            "export_manifest": export_manifest,
            "alert": alert or (
                {
                    "type": "success",
                    "title": "Hasil tersedia",
                    "message": "Data hasil penjadwalan siap diekspor."
                } if has_result else {
                    "type": "info",
                    "title": "Hasil belum tersedia",
                    "message": "Ekspor hanya dapat dilakukan setelah proses penjadwalan selesai."
                }
            ),
        }

    def export_result(self, export_type: str):
        current_result = self.get_current_result()
        if not current_result or not current_result.is_ready_to_display():
            raise ValueError("Hasil penjadwalan belum tersedia. Jalankan eksekusi penjadwalan terlebih dahulu.")
        return self.csv_exporter.export_by_type(current_result, export_type)


    def _get_active_semester(self) -> str:
        configs = app_state.current_class_opening or []
        if configs:
            return configs[0].semester_aktif
        return "Ganjil"
