"""Konfigurasi dasar aplikasi web penjadwalan."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    app_name: str = "Sistem Penjadwalan Mata Kuliah"
    institution_name: str = "Fakultas Ilmu Komputer Universitas Brawijaya"
    active_algorithm: str = "Memetic Algorithm"
    admin_role: str = "Admin Program Studi"
    admin_subtitle: str = "Admin"


config = AppConfig()
