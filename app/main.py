"""Entry point aplikasi web Sistem Penjadwalan Mata Kuliah."""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.core.config import config
from app.core.paths import STATIC_DIR, ensure_directories
from app.routers import file_export_router, history_router, scheduling_router

ensure_directories()

app = FastAPI(title=config.app_name)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.include_router(scheduling_router.router)
app.include_router(file_export_router.router)
app.include_router(history_router.router)
