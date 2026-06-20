"""Definisi path utama agar penyimpanan file konsisten di seluruh aplikasi."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
APP_DIR = BASE_DIR / "app"
DATA_DIR = BASE_DIR / "data"

INPUT_DIR = DATA_DIR / "input"
UPLOADED_DIR = DATA_DIR / "uploaded"
OUTPUT_DIR = DATA_DIR / "output"
EXPORT_DIR = DATA_DIR / "export"
DB_DIR = DATA_DIR / "db"

TEMPLATE_DIR = APP_DIR / "templates"
STATIC_DIR = APP_DIR / "static"


def ensure_directories() -> None:
    """Membuat direktori kerja yang dibutuhkan aplikasi."""
    for directory in [INPUT_DIR, UPLOADED_DIR, OUTPUT_DIR, EXPORT_DIR, DB_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
