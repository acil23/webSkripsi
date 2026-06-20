"""Boundary layer untuk riwayat jadwal."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.controllers.history_controller import HistoryController
from app.core.paths import TEMPLATE_DIR

router = APIRouter()
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
controller = HistoryController()


@router.get("/riwayat-jadwal", response_class=HTMLResponse)
def history_page(request: Request):
    context = controller.get_history_placeholder_context()
    return templates.TemplateResponse(
        "placeholder.html",
        {"request": request, "active_menu": "Riwayat Jadwal", **context},
    )


@router.get("/riwayat-jadwal/{id_riwayat}", response_class=HTMLResponse)
def history_detail_page(request: Request, id_riwayat: str):
    context = controller.get_history_detail_placeholder_context()
    return templates.TemplateResponse(
        "placeholder.html",
        {
            "request": request,
            "active_menu": "Riwayat Jadwal",
            "id_riwayat": id_riwayat,
            **context,
        },
    )
