"""State sementara aplikasi.

State ini dipakai untuk menjaga alur bertahap sesuai rancangan Bab 5:
currentDataset, currentParameter, currentClassOpening, currentSessions, dan
currentResult. Pada Tahap 2, field yang mulai digunakan adalah current_dataset.
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
