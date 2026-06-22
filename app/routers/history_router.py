"""Boundary layer untuk riwayat jadwal."""

from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.controllers.history_controller import HistoryController
from app.core.paths import TEMPLATE_DIR

router = APIRouter()
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
controller = HistoryController()


def _alert_query(alert_type: str, title: str, message: str) -> str:
    return f"alert_type={quote(alert_type)}&alert_title={quote(title)}&alert_message={quote(message)}"


def _read_alert_from_query(request: Request) -> dict | None:
    alert_type = request.query_params.get("alert_type")
    if not alert_type:
        return None
    return {
        "type": alert_type,
        "title": request.query_params.get("alert_title", "Informasi"),
        "message": request.query_params.get("alert_message", ""),
    }


@router.post("/history/save")
def save_history(nama_riwayat: str = Form(...)):
    try:
        saved = controller.save_history({"nama_riwayat": nama_riwayat})
    except ValueError as exc:
        query = _alert_query("error", "Gagal menyimpan riwayat", str(exc))
        return RedirectResponse(url=f"/hasil-penjadwalan?{query}", status_code=303)

    query = _alert_query("success", "Riwayat tersimpan", f"{saved.nama_riwayat} berhasil disimpan.")
    return RedirectResponse(url=f"/riwayat-jadwal?{query}", status_code=303)


@router.get("/riwayat-jadwal", response_class=HTMLResponse)
def history_page(
    request: Request,
    search: str = "",
    status: str = "Semua Status",
):
    alert = _read_alert_from_query(request)
    context = controller.get_history_page_context(search=search, status=status, alert=alert)
    return templates.TemplateResponse(
        "riwayat_jadwal.html",
        {"request": request, "active_menu": "Riwayat Jadwal", **context},
    )


@router.get("/riwayat-jadwal/{id_riwayat}", response_class=HTMLResponse)
def history_detail_page(request: Request, id_riwayat: str):
    alert = _read_alert_from_query(request)
    context = controller.get_history_detail_page_context(id_riwayat, alert=alert)
    return templates.TemplateResponse(
        "detail_riwayat.html",
        {
            "request": request,
            "active_menu": "Riwayat Jadwal",
            "id_riwayat": id_riwayat,
            **context,
        },
    )


@router.post("/history/{id_riwayat}/delete")
def delete_history(id_riwayat: str):
    deleted = controller.delete_history(id_riwayat)
    if deleted:
        query = _alert_query("success", "Riwayat dihapus", "Riwayat jadwal berhasil dihapus.")
    else:
        query = _alert_query("error", "Riwayat tidak ditemukan", "Riwayat jadwal tidak dapat dihapus.")
    return RedirectResponse(url=f"/riwayat-jadwal?{query}", status_code=303)


def _download_history_export(id_riwayat: str, export_type: str, media_type: str) -> FileResponse:
    try:
        file_path = Path(controller.export_history_result(id_riwayat, export_type))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if not file_path.exists():
        raise HTTPException(status_code=500, detail="Berkas ekspor riwayat gagal dibentuk.")
    return FileResponse(path=str(file_path), filename=file_path.name, media_type=media_type)


@router.get("/history/{id_riwayat}/export/schedule")
def export_history_schedule(id_riwayat: str):
    return _download_history_export(id_riwayat, "schedule", "text/csv")


@router.get("/history/{id_riwayat}/export/evaluation")
def export_history_evaluation(id_riwayat: str):
    return _download_history_export(id_riwayat, "evaluation", "text/csv")


@router.get("/history/{id_riwayat}/export/workload")
def export_history_workload(id_riwayat: str):
    return _download_history_export(id_riwayat, "workload", "text/csv")


@router.get("/history/{id_riwayat}/export/convergence-log")
def export_history_log(id_riwayat: str):
    return _download_history_export(id_riwayat, "convergence_log", "text/csv")


@router.get("/history/{id_riwayat}/export/package")
def export_history_package(id_riwayat: str):
    return _download_history_export(id_riwayat, "package", "application/zip")
