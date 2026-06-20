"""State sementara aplikasi.

Pada Tahap 1, state ini belum digunakan untuk data penjadwalan.
File ini disiapkan agar tahap berikutnya dapat menyimpan currentDataset,
currentParameter, currentClassOpening, dan currentResult sesuai rancangan Bab 5.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AppState:
    current_dataset: Any | None = None
    current_parameter: Any | None = None
    current_class_opening: Any | None = None
    current_classes: Any | None = None
    current_sessions: Any | None = None
    current_result: Any | None = None
    execution_status: dict[str, Any] = field(default_factory=dict)


app_state = AppState()
