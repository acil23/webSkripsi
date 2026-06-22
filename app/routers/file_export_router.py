"""Boundary layer untuk ekspor hasil penjadwalan.

Tahap 7 merealisasikan UC-06 Mengekspor Hasil Penjadwalan melalui halaman
Ekspor Hasil dan endpoint download CSV/ZIP. Router ini tetap bertindak sebagai
boundary layer, sedangkan pembentukan file didelegasikan kepada SchedulingController
lalu CSVExporter.
"""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from app.controllers.scheduling_controller import SchedulingController
from app.core.paths import TEMPLATE_DIR

router = APIRouter()
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
controller = SchedulingController()


@router.get("/ekspor-hasil", response_class=HTMLResponse)
def export_page(request: Request):
    context = controller.get_export_page_context()
    return templates.TemplateResponse(
        "ekspor_hasil.html",
        {"request": request, "active_menu": "Hasil Penjadwalan", **context},
    )


def _download_export(export_type: str, media_type: str) -> FileResponse:
    try:
        file_path = Path(controller.export_result(export_type))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not file_path.exists():
        raise HTTPException(status_code=500, detail="Berkas ekspor gagal dibentuk.")

    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type=media_type,
    )


@router.get("/export/schedule")
def export_schedule():
    return _download_export("schedule", "text/csv")


@router.get("/export/evaluation")
def export_evaluation():
    return _download_export("evaluation", "text/csv")


@router.get("/export/workload")
def export_workload():
    return _download_export("workload", "text/csv")


@router.get("/export/convergence-log")
def export_convergence_log():
    return _download_export("convergence_log", "text/csv")


@router.get("/export/package")
def export_package():
    return _download_export("package", "application/zip")
