"""Control layer untuk UC-03 Mengatur Parameter Algoritma."""

from __future__ import annotations

from typing import Any

from app.core.app_state import app_state
from app.entities.algorithm_entities import ParameterAlgoritma


class ParameterController:
    def get_parameter(self) -> ParameterAlgoritma | None:
        return app_state.current_parameter

    def create_parameter(self, parameter_input: dict[str, Any]) -> ParameterAlgoritma:
        return ParameterAlgoritma.from_input(parameter_input)

    def validate_parameter(self, params: ParameterAlgoritma) -> bool:
        return params.validate()

    def save_parameter(self, parameter_input: dict[str, Any]) -> ParameterAlgoritma:
        parameter = self.create_parameter(parameter_input)
        if parameter.is_valid():
            self.set_current_parameter(parameter)
        return parameter

    def set_current_parameter(self, params: ParameterAlgoritma) -> bool:
        app_state.current_parameter = params
        # Hasil lama tidak boleh dipakai ketika parameter berubah.
        app_state.current_result = None
        return True
