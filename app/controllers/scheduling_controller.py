"""Control layer utama untuk alur penjadwalan.

Tahap 1 hanya menyediakan data tampilan dashboard dan halaman placeholder.
Method lain akan ditambahkan bertahap pada tahap upload, konfigurasi kelas,
parameter algoritma, eksekusi, dan hasil penjadwalan.
"""

from app.core.config import config


class SchedulingController:
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
