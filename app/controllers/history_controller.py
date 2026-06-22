"""Control layer untuk riwayat jadwal.

Tahap 8 merealisasikan UC-07 Menyimpan Riwayat Jadwal dan UC-08 Melihat
Riwayat Jadwal. Controller ini mengambil currentResult dari SchedulingController,
membentuk RiwayatJadwal, menyimpannya melalui HistoryRepository, serta membangun
view data untuk daftar dan detail riwayat.
"""

from __future__ import annotations

from typing import Any

from app.controllers.scheduling_controller import SchedulingController
from app.entities.history_entities import RiwayatJadwal
from app.repositories.history_repository import HistoryRepository
from app.services.csv_exporter import CSVExporter
from app.services.visualization_service import VisualizationService


class HistoryController:
    def __init__(self):
        self.scheduling_controller = SchedulingController()
        self.history_repository = HistoryRepository()
        self.visualization_service = VisualizationService()
        self.csv_exporter = CSVExporter()

    # ======================================================
    # UC-07 Menyimpan Riwayat Jadwal
    # ======================================================
    def save_history(self, history_input: dict[str, Any]) -> RiwayatJadwal:
        nama_riwayat = str(history_input.get("nama_riwayat", "")).strip()
        if not nama_riwayat:
            raise ValueError("Nama riwayat wajib diisi.")
        if len(nama_riwayat) > 100:
            raise ValueError("Nama riwayat maksimal 100 karakter.")

        current_result = self.scheduling_controller.get_current_result()
        if not current_result or not current_result.is_ready_to_display():
            raise ValueError("Hasil penjadwalan belum tersedia. Jalankan eksekusi terlebih dahulu.")

        current_parameter = self.scheduling_controller.get_current_parameter()
        current_class_opening = self.scheduling_controller.get_current_class_opening() or []

        parameter_payload = current_parameter.to_dict() if current_parameter else dict(current_result.parameter or {})
        class_opening_payload = [config.to_dict() for config in current_class_opening]

        riwayat = RiwayatJadwal.create(
            nama_riwayat=nama_riwayat,
            result=current_result,
            parameter_payload=parameter_payload,
            class_opening_payload=class_opening_payload,
        )
        return self.history_repository.save(riwayat)

    # ======================================================
    # UC-08 Melihat Riwayat Jadwal
    # ======================================================
    def get_histories(self) -> list[RiwayatJadwal]:
        return self.history_repository.find_all()

    def get_history_detail(self, id_riwayat: str) -> RiwayatJadwal | None:
        return self.history_repository.find_by_id(id_riwayat)

    def delete_history(self, id_riwayat: str) -> bool:
        return self.history_repository.delete(id_riwayat)

    def get_history_page_context(
        self,
        search: str = "",
        status: str = "Semua Status",
        alert: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        histories = self.get_histories()
        summaries = [history.get_summary() for history in histories]
        filtered = self._filter_summaries(summaries, search=search, status=status)

        latest = summaries[0] if summaries else None
        feasible_count = sum(1 for item in summaries if item["is_feasible"])

        return {
            "page_title": "Riwayat Jadwal",
            "description": "Halaman ini digunakan untuk melihat dan mengelola riwayat penjadwalan yang telah disimpan.",
            "histories": filtered,
            "total_histories": len(summaries),
            "total_filtered": len(filtered),
            "latest_history": latest,
            "feasible_count": feasible_count,
            "search": search,
            "status": status,
            "alert": alert,
        }

    def get_history_detail_page_context(
        self,
        id_riwayat: str,
        alert: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        selected = self.get_history_detail(id_riwayat)
        if selected is None:
            return {
                "page_title": "Detail Riwayat Jadwal",
                "description": "Halaman ini menampilkan detail dari riwayat penjadwalan yang telah disimpan.",
                "has_history": False,
                "history": None,
                "summary": None,
                "result_view": None,
                "parameter_rows": [],
                "class_opening_preview": [],
                "alert": alert or {
                    "type": "error",
                    "title": "Riwayat tidak ditemukan",
                    "message": "Detail riwayat yang dipilih tidak dapat dimuat.",
                },
            }

        result = selected.result
        result_view = self.visualization_service.build_result_view_data(result)
        parameter_rows = self._build_parameter_rows(selected.parameter_payload or result.parameter)
        class_opening_preview = (selected.class_opening_payload or [])[:20]

        return {
            "page_title": "Detail Riwayat Jadwal",
            "description": "Halaman ini menampilkan detail dari riwayat penjadwalan yang telah disimpan.",
            "has_history": True,
            "history": selected,
            "summary": selected.get_summary(),
            "result_view": result_view,
            "parameter_rows": parameter_rows,
            "class_opening_preview": class_opening_preview,
            "class_opening_total": len(selected.class_opening_payload or []),
            "alert": alert,
        }

    def export_history_result(self, id_riwayat: str, export_type: str):
        selected = self.get_history_detail(id_riwayat)
        if selected is None:
            raise ValueError("Riwayat jadwal tidak ditemukan.")
        return self.csv_exporter.export_by_type(selected.result, export_type)

    def _filter_summaries(
        self,
        summaries: list[dict[str, Any]],
        search: str = "",
        status: str = "Semua Status",
    ) -> list[dict[str, Any]]:
        filtered = list(summaries)
        if search:
            keyword = search.strip().lower()
            filtered = [item for item in filtered if keyword in item["nama_riwayat"].lower()]
        if status == "Feasible":
            filtered = [item for item in filtered if item["is_feasible"]]
        elif status == "Masih Ada Konflik":
            filtered = [item for item in filtered if not item["is_feasible"]]
        return filtered

    def _build_parameter_rows(self, parameter_payload: dict[str, Any]) -> list[dict[str, Any]]:
        labels = [
            ("pop_size", "Ukuran Populasi"),
            ("max_generations", "Jumlah Generasi Maksimum"),
            ("crossover_rate", "Crossover Rate"),
            ("mutation_rate", "Mutation Rate"),
            ("local_search_chance", "Peluang Local Search"),
            ("ls_chance", "Peluang Local Search"),
            ("elitism", "Elitism"),
            ("seed", "Seed"),
        ]
        rows = []
        used_labels = set()
        for key, label in labels:
            if label in used_labels:
                continue
            if key in parameter_payload:
                rows.append({"label": label, "value": parameter_payload.get(key)})
                used_labels.add(label)
        return rows
