"""State sementara aplikasi.

State ini dipakai untuk menjaga alur bertahap sesuai rancangan Bab 5:
currentDataset, currentParameter, currentClassOpening, currentSessions, dan
currentResult. Tahap 4 sudah menggunakan current_dataset, current_class_opening, current_sessions, dan current_parameter.
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
