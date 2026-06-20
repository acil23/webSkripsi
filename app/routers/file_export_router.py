"""Boundary layer untuk ekspor hasil penjadwalan.

Tahap 1 baru menyediakan placeholder halaman. Endpoint download CSV/ZIP akan
masuk pada Tahap 7.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.controllers.scheduling_controller import SchedulingController
from app.core.paths import TEMPLATE_DIR

router = APIRouter()
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
controller = SchedulingController()


@router.get("/ekspor-hasil", response_class=HTMLResponse)
def export_page(request: Request):
    context = controller.get_placeholder_context(
        title="Ekspor Hasil Penjadwalan",
        description="Ekspor jadwal, evaluasi, beban dosen, log konvergensi, dan ZIP akan diimplementasikan pada Tahap 7.",
    )
    return templates.TemplateResponse(
        "placeholder.html",
        {"request": request, "active_menu": "Hasil Penjadwalan", **context},
    )
