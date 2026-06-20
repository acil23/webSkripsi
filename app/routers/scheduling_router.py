"""Boundary layer untuk halaman utama alur penjadwalan."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.controllers.scheduling_controller import SchedulingController
from app.core.paths import TEMPLATE_DIR

router = APIRouter()
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
controller = SchedulingController()


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    context = controller.get_dashboard_context()
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "active_menu": "Dashboard",
            **context,
        },
    )


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_alias(request: Request):
    context = controller.get_dashboard_context()
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "active_menu": "Dashboard",
            **context,
        },
    )


@router.get("/unggah-data", response_class=HTMLResponse)
def upload_data_page(request: Request):
    context = controller.get_placeholder_context(
        title="Manajemen Data Masukan",
        description="Halaman upload CSV dan validasi data akan diimplementasikan pada Tahap 2.",
    )
    return templates.TemplateResponse(
        "placeholder.html",
        {"request": request, "active_menu": "Unggah Data", **context},
    )


@router.get("/konfigurasi-kelas", response_class=HTMLResponse)
def class_opening_page(request: Request):
    context = controller.get_placeholder_context(
        title="Konfigurasi Pembukaan Kelas",
        description="Tabel rekomendasi dan penyimpanan konfigurasi kelas akan diimplementasikan pada Tahap 3.",
    )
    return templates.TemplateResponse(
        "placeholder.html",
        {"request": request, "active_menu": "Konfigurasi Kelas", **context},
    )


@router.get("/parameter-algoritma", response_class=HTMLResponse)
def parameter_page(request: Request):
    context = controller.get_placeholder_context(
        title="Pengaturan Parameter Algoritma",
        description="Form parameter dan validasi algoritma akan diimplementasikan pada Tahap 4.",
    )
    return templates.TemplateResponse(
        "placeholder.html",
        {"request": request, "active_menu": "Parameter Algoritma", **context},
    )


@router.get("/eksekusi-penjadwalan", response_class=HTMLResponse)
def execution_page(request: Request):
    context = controller.get_placeholder_context(
        title="Eksekusi Penjadwalan",
        description="Checklist prasyarat dan integrasi Memetic Algorithm akan diimplementasikan pada Tahap 5.",
    )
    return templates.TemplateResponse(
        "placeholder.html",
        {"request": request, "active_menu": "Eksekusi Penjadwalan", **context},
    )


@router.get("/hasil-penjadwalan", response_class=HTMLResponse)
def result_page(request: Request):
    context = controller.get_placeholder_context(
        title="Hasil Jadwal dan Evaluasi",
        description="Tabel jadwal, metrik evaluasi, grafik konvergensi, dan beban dosen akan diimplementasikan pada Tahap 6.",
    )
    return templates.TemplateResponse(
        "placeholder.html",
        {"request": request, "active_menu": "Hasil Penjadwalan", **context},
    )
