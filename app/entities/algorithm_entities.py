"""Entity dan value object untuk parameter algoritma.

Tahap 4 mengimplementasikan ParameterAlgoritma sebagai value object sesuai
class diagram Bab 5. Objek ini bertanggung jawab memegang nilai parameter dan
melakukan validasi rentang nilai sebelum parameter disimpan sebagai
currentParameter.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# Batas validasi parameter dipusatkan di sini agar mudah diubah untuk demo
# atau pengujian. Nilai minimum generasi sengaja diturunkan agar admin dapat
# menjalankan demo cepat tanpa harus menunggu 50 generasi.
PARAMETER_LIMITS = {
    "pop_size_min": 10,
    "pop_size_max": 500,
    "max_generations_min": 1,
    "max_generations_max": 1000,
    "rate_min": 0.0,
    "rate_max": 1.0,
    "elitism_min": 1,
    "elitism_max": 10,
}


@dataclass
class ParameterValidationError:
    field: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"field": self.field, "message": self.message}


@dataclass
class ParameterAlgoritma:
    pop_size: int | None = 150
    max_generations: int | None = 300
    crossover_rate: float | None = 0.80
    mutation_rate: float | None = 0.20
    local_search_chance: float | None = 0.40
    elitism: int | None = 2
    seed: int | None = 42
    errors: list[ParameterValidationError] = field(default_factory=list)

    @classmethod
    def default(cls) -> "ParameterAlgoritma":
        return cls()

    @classmethod
    def from_input(cls, parameter_input: dict[str, Any]) -> "ParameterAlgoritma":
        """Membentuk objek parameter dari input form atau payload dictionary."""
        parameter = cls(
            pop_size=cls._parse_int(parameter_input.get("pop_size"), "pop_size"),
            max_generations=cls._parse_int(parameter_input.get("max_generations"), "max_generations"),
            crossover_rate=cls._parse_float(parameter_input.get("crossover_rate"), "crossover_rate"),
            mutation_rate=cls._parse_float(parameter_input.get("mutation_rate"), "mutation_rate"),
            local_search_chance=cls._parse_float(parameter_input.get("local_search_chance"), "local_search_chance"),
            elitism=cls._parse_int(parameter_input.get("elitism"), "elitism"),
            seed=cls._parse_optional_int(parameter_input.get("seed"), "seed"),
        )
        parameter.validate()
        return parameter

    @staticmethod
    def _empty(value: Any) -> bool:
        return value is None or str(value).strip() == ""

    @classmethod
    def _parse_int(cls, value: Any, field: str) -> int | None:
        if cls._empty(value):
            return None
        try:
            return int(str(value).strip())
        except Exception:
            return None

    @classmethod
    def _parse_optional_int(cls, value: Any, field: str) -> int | None:
        if cls._empty(value):
            return None
        return cls._parse_int(value, field)

    @classmethod
    def _parse_float(cls, value: Any, field: str) -> float | None:
        if cls._empty(value):
            return None
        try:
            return float(str(value).strip().replace(",", "."))
        except Exception:
            return None

    def validate(self) -> bool:
        """Validasi nilai parameter sesuai batas sistem web."""
        self.errors.clear()

        if self.pop_size is None:
            self._add_error("pop_size", "Ukuran populasi wajib berupa bilangan bulat.")
        elif not PARAMETER_LIMITS["pop_size_min"] <= self.pop_size <= PARAMETER_LIMITS["pop_size_max"]:
            self._add_error(
                "pop_size",
                f"Ukuran populasi harus berada pada rentang {PARAMETER_LIMITS['pop_size_min']} sampai {PARAMETER_LIMITS['pop_size_max']}.",
            )

        if self.max_generations is None:
            self._add_error("max_generations", "Jumlah generasi maksimum wajib berupa bilangan bulat.")
        elif not PARAMETER_LIMITS["max_generations_min"] <= self.max_generations <= PARAMETER_LIMITS["max_generations_max"]:
            self._add_error(
                "max_generations",
                f"Jumlah generasi maksimum harus berada pada rentang {PARAMETER_LIMITS['max_generations_min']} sampai {PARAMETER_LIMITS['max_generations_max']}.",
            )

        if self.crossover_rate is None:
            self._add_error("crossover_rate", "Crossover rate wajib berupa angka.")
        elif not PARAMETER_LIMITS["rate_min"] <= self.crossover_rate <= PARAMETER_LIMITS["rate_max"]:
            self._add_error("crossover_rate", "Nilai harus berada pada rentang 0.0 sampai 1.0.")

        if self.mutation_rate is None:
            self._add_error("mutation_rate", "Mutation rate wajib berupa angka.")
        elif not PARAMETER_LIMITS["rate_min"] <= self.mutation_rate <= PARAMETER_LIMITS["rate_max"]:
            self._add_error("mutation_rate", "Nilai harus berada pada rentang 0.0 sampai 1.0.")

        if self.local_search_chance is None:
            self._add_error("local_search_chance", "Peluang local search wajib berupa angka.")
        elif not PARAMETER_LIMITS["rate_min"] <= self.local_search_chance <= PARAMETER_LIMITS["rate_max"]:
            self._add_error("local_search_chance", "Nilai harus berada pada rentang 0.0 sampai 1.0.")

        if self.elitism is None:
            self._add_error("elitism", "Elitism wajib berupa bilangan bulat.")
        elif not PARAMETER_LIMITS["elitism_min"] <= self.elitism <= PARAMETER_LIMITS["elitism_max"]:
            self._add_error(
                "elitism",
                f"Elitism harus berada pada rentang {PARAMETER_LIMITS['elitism_min']} sampai {PARAMETER_LIMITS['elitism_max']}.",
            )

        if self.seed is not None and self.seed < 0:
            self._add_error("seed", "Seed tidak boleh bernilai negatif.")

        if (
            self.pop_size is not None
            and self.elitism is not None
            and self.elitism >= self.pop_size
        ):
            self._add_error("elitism", "Elitism harus lebih kecil dari ukuran populasi.")

        return self.is_valid()

    def _add_error(self, field: str, message: str) -> None:
        self.errors.append(ParameterValidationError(field=field, message=message))

    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def error_for(self, field: str) -> str | None:
        for error in self.errors:
            if error.field == field:
                return error.message
        return None

    def has_error(self, field: str) -> bool:
        return self.error_for(field) is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "pop_size": self.pop_size,
            "max_generations": self.max_generations,
            "crossover_rate": self.crossover_rate,
            "mutation_rate": self.mutation_rate,
            "local_search_chance": self.local_search_chance,
            "elitism": self.elitism,
            "seed": self.seed,
            "is_valid": self.is_valid(),
            "errors": [error.to_dict() for error in self.errors],
        }

    def to_engine_params(self) -> dict[str, Any]:
        """Konversi ke format parameter yang dipakai engine algoritma lama."""
        return {
            "pop_size": int(self.pop_size or 0),
            "max_generations": int(self.max_generations or 0),
            "crossover_rate": float(self.crossover_rate or 0),
            "mutation_rate": float(self.mutation_rate or 0),
            "ls_chance": float(self.local_search_chance or 0),
            "elitism": int(self.elitism or 0),
            "seed": int(self.seed or 0) if self.seed is not None else None,
            "use_local_search": True,
            "use_load_balancing": True,
            "model_name": "MA_FIHC_ROBINHOOD",
        }

    def to_summary_rows(self) -> list[dict[str, Any]]:
        return [
            {"label": "Ukuran Populasi", "field": "pop_size", "value": self.pop_size},
            {"label": "Jumlah Generasi Maksimum", "field": "max_generations", "value": self.max_generations},
            {"label": "Crossover Rate", "field": "crossover_rate", "value": self._format_float(self.crossover_rate)},
            {"label": "Mutation Rate", "field": "mutation_rate", "value": self._format_float(self.mutation_rate)},
            {"label": "Peluang Local Search", "field": "local_search_chance", "value": self._format_float(self.local_search_chance)},
            {"label": "Elitism", "field": "elitism", "value": self.elitism},
            {"label": "Seed", "field": "seed", "value": self.seed if self.seed is not None else "-"},
        ]

    @staticmethod
    def _format_float(value: float | None) -> str:
        if value is None:
            return "-"
        return f"{value:.2f}"
