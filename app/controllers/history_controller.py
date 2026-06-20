"""Control layer untuk riwayat jadwal.

Pada Tahap 1, controller ini baru menyediakan placeholder halaman riwayat.
Implementasi SQLite dan HistoryRepository akan dilakukan pada Tahap 8.
"""


class HistoryController:
    def get_history_placeholder_context(self) -> dict:
        return {
            "page_title": "Riwayat Jadwal",
            "description": "Halaman ini akan digunakan untuk melihat dan mengelola riwayat penjadwalan yang telah disimpan.",
        }

    def get_history_detail_placeholder_context(self) -> dict:
        return {
            "page_title": "Detail Riwayat Jadwal",
            "description": "Halaman ini akan menampilkan detail dari riwayat penjadwalan yang telah disimpan.",
        }
