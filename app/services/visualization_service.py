"""Service visualisasi hasil penjadwalan.

Service ini membentuk data grafik berbasis SVG agar halaman hasil dan detail
riwayat tetap dapat menampilkan visualisasi tanpa CDN/Chart.js. Tahap 9.4
menambahkan informasi sumbu, judul, legenda, dan anotasi agar grafik yang
diunduh tetap dapat dipahami sebagai gambar mandiri.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Any

from app.entities.result_entities import LogKonvergensi, PenjadwalanResult


@dataclass
class ChartSeries:
    label: str
    points: str
    raw_points: list[dict[str, float | int]]
    min_value: float
    max_value: float
    last_value: float


class VisualizationService:
    """Membentuk data tampilan grafik dan ringkasan hasil."""

    CHART_WIDTH = 900
    CHART_HEIGHT = 520
    PLOT_LEFT = 92
    PLOT_RIGHT = 34
    PLOT_TOP = 86
    PLOT_BOTTOM = 82

    def build_convergence_log(self, result: PenjadwalanResult) -> list[dict[str, Any]]:
        return [log.to_dict() for log in result.get_log_konvergensi()]

    def generate_convergence_chart(self, logs: list[LogKonvergensi]) -> dict[str, Any]:
        """Membentuk data SVG untuk fitness, konflik, dan penalty per generasi."""
        if not logs:
            return {
                "has_data": False,
                "fitness": None,
                "conflict": None,
                "penalty": None,
                "total_generations": 0,
            }

        fitness_values = [float(log.best_fitness or 0.0) for log in logs]
        conflict_values = [float(log.total_conflict or 0.0) for log in logs]
        penalty_values = [float(log.total_penalty or 0.0) for log in logs]
        generations = [int(log.generasi) for log in logs]

        fitness_series = self._build_series("Fitness", generations, fitness_values)
        conflict_series = self._build_series("Total Konflik", generations, conflict_values)
        penalty_series = self._build_series("Total Penalty", generations, penalty_values)

        fitness_series["plot"] = self._build_line_plot(
            title="Grafik Peningkatan Nilai Fitness",
            x_label="Generasi",
            y_label="Nilai Fitness",
            legend_label="Nilai Fitness",
            x_values=generations,
            y_values=fitness_values,
            stroke="#2563eb",
            annotation_type="fitness_max",
        )
        conflict_series["plot"] = self._build_line_plot(
            title="Grafik Penurunan Konflik (Hard Constraints)",
            x_label="Generasi",
            y_label="Total Konflik",
            legend_label="Jumlah Konflik",
            x_values=generations,
            y_values=conflict_values,
            stroke="#ef4444",
            annotation_type="conflict_zero",
            force_integer_y=True,
        )
        penalty_series["plot"] = self._build_line_plot(
            title="Grafik Perubahan Total Penalty",
            x_label="Generasi",
            y_label="Total Penalty",
            legend_label="Total Penalty",
            x_values=generations,
            y_values=penalty_values,
            stroke="#7c3aed",
            annotation_type="penalty_min",
        )

        return {
            "has_data": True,
            "total_generations": len(logs),
            "fitness": fitness_series,
            "conflict": conflict_series,
            "penalty": penalty_series,
        }

    def build_workload_rows(self, result: PenjadwalanResult) -> list[dict[str, Any]]:
        rows = [item.to_dict() for item in result.get_beban_dosen()]
        return sorted(
            rows,
            key=lambda row: (
                0 if row.get("dihitung_fairness") else 1,
                -int(row.get("total_sks") or 0),
                str(row.get("dosen") or ""),
            ),
        )

    def build_schedule_rows(self, result: PenjadwalanResult) -> list[dict[str, Any]]:
        rows = result.get_jadwal().to_rows()
        day_order = {
            "senin": 1,
            "selasa": 2,
            "rabu": 3,
            "kamis": 4,
            "jumat": 5,
            "sabtu": 6,
        }
        return sorted(
            rows,
            key=lambda row: (
                day_order.get(str(row.get("hari", "")).lower(), 99),
                str(row.get("jam_mulai", "")),
                str(row.get("ruang", "")),
                str(row.get("kode_mk", "")),
                str(row.get("kelas", "")),
            ),
        )

    def build_metric_cards(self, result: PenjadwalanResult) -> list[dict[str, str]]:
        evaluasi = result.get_evaluasi()
        return [
            {
                "label": "Fitness",
                "value": f"{evaluasi.fitness:.6f}",
                "icon": "↗",
                "tone": "teal",
            },
            {
                "label": "Total Penalty",
                "value": f"{evaluasi.total_penalty:.4f}",
                "icon": "▣",
                "tone": "blue",
            },
            {
                "label": "Total Konflik",
                "value": str(evaluasi.total_conflict),
                "icon": "◇",
                "tone": "green" if evaluasi.total_conflict == 0 else "orange",
            },
            {
                "label": "Standar Deviasi Beban",
                "value": f"{evaluasi.standar_deviasi_beban:.4f}",
                "icon": "♎",
                "tone": "purple",
            },
            {
                "label": "Waktu Komputasi",
                "value": self.format_duration(evaluasi.waktu_komputasi),
                "icon": "◷",
                "tone": "teal",
            },
        ]

    def build_result_view_data(self, result: PenjadwalanResult) -> dict[str, Any]:
        schedule_rows = self.build_schedule_rows(result)
        workload_rows = self.build_workload_rows(result)
        chart = self.generate_convergence_chart(result.get_log_konvergensi())
        evaluasi = result.get_evaluasi()

        return {
            "is_ready": result.is_ready_to_display(),
            "summary": result.to_summary(),
            "metrics": self.build_metric_cards(result),
            "evaluation": evaluasi.to_dict(),
            "schedule_rows": schedule_rows,
            "schedule_preview_rows": schedule_rows[:25],
            "workload_rows": workload_rows,
            "workload_preview_rows": workload_rows[:12],
            "convergence_chart": chart,
            "penalty_chart": self._build_penalty_bar_chart(evaluasi.to_dict()),
            "workload_chart": self._build_workload_bar_chart(workload_rows),
            "convergence_logs": self.build_convergence_log(result),
            "total_schedule_rows": len(schedule_rows),
            "total_workload_rows": len(workload_rows),
            "feasibility_label": "Feasible" if evaluasi.is_feasible() else "Masih Ada Konflik",
            "feasibility_class": "feasible" if evaluasi.is_feasible() else "not-feasible",
            "formatted_duration": self.format_duration(evaluasi.waktu_komputasi),
        }

    def _build_series(self, label: str, x_values: list[int], y_values: list[float]) -> dict[str, Any]:
        min_y = min(y_values)
        max_y = max(y_values)
        span_y = max(max_y - min_y, 1e-12)
        min_x = min(x_values)
        max_x = max(x_values)
        span_x = max(max_x - min_x, 1)

        coords: list[str] = []
        raw_points: list[dict[str, float | int]] = []
        for x, y in zip(x_values, y_values):
            svg_x = ((x - min_x) / span_x) * 100
            svg_y = 100 - (((y - min_y) / span_y) * 90 + 5)
            coords.append(f"{svg_x:.2f},{svg_y:.2f}")
            raw_points.append({"x": x, "y": y, "svg_x": svg_x, "svg_y": svg_y})

        return {
            "label": label,
            "points": " ".join(coords),
            "raw_points": raw_points,
            "min_value": min_y,
            "max_value": max_y,
            "last_value": y_values[-1],
        }

    def _build_line_plot(
        self,
        *,
        title: str,
        x_label: str,
        y_label: str,
        legend_label: str,
        x_values: list[int],
        y_values: list[float],
        stroke: str,
        annotation_type: str | None = None,
        force_integer_y: bool = False,
    ) -> dict[str, Any]:
        width = self.CHART_WIDTH
        height = self.CHART_HEIGHT
        left = self.PLOT_LEFT
        right = self.PLOT_RIGHT
        top = self.PLOT_TOP
        bottom = self.PLOT_BOTTOM
        plot_width = width - left - right
        plot_height = height - top - bottom

        min_x = min(x_values)
        max_x = max(x_values)
        span_x = max(max_x - min_x, 1)

        min_y_raw = min(y_values)
        max_y_raw = max(y_values)
        y_min = 0.0 if min_y_raw >= 0 else min_y_raw
        y_max = max_y_raw
        if y_max == y_min:
            y_max = y_min + (1.0 if force_integer_y else max(abs(y_min) * 0.1, 1e-6))
        y_padding = (y_max - y_min) * 0.08
        y_max = y_max + y_padding
        if min_y_raw < 0:
            y_min = y_min - y_padding
        span_y = max(y_max - y_min, 1e-12)

        def to_x(value: float) -> float:
            return left + ((value - min_x) / span_x) * plot_width

        def to_y(value: float) -> float:
            return top + (1 - ((value - y_min) / span_y)) * plot_height

        points = " ".join(
            f"{to_x(float(x)):.2f},{to_y(float(y)):.2f}" for x, y in zip(x_values, y_values)
        )

        x_ticks = []
        for value in self._build_x_ticks(min_x, max_x):
            x_ticks.append({"value": value, "x": round(to_x(value), 2), "label": str(value)})

        y_ticks = []
        for value in self._build_y_ticks(y_min, y_max, force_integer=force_integer_y):
            y_ticks.append({
                "value": value,
                "y": round(to_y(value), 2),
                "label": self._format_tick(value, integer=force_integer_y),
            })

        annotation = self._build_line_annotation(
            annotation_type=annotation_type,
            x_values=x_values,
            y_values=y_values,
            to_x=to_x,
            to_y=to_y,
            left=left,
            right=right,
            top=top,
            width=width,
            plot_height=plot_height,
        )

        return {
            "title": title,
            "x_label": x_label,
            "y_label": y_label,
            "legend_label": legend_label,
            "stroke": stroke,
            "view_box": f"0 0 {width} {height}",
            "width": width,
            "height": height,
            "left": left,
            "right": right,
            "top": top,
            "bottom": bottom,
            "plot_width": plot_width,
            "plot_height": plot_height,
            "plot_right": width - right,
            "plot_bottom": height - bottom,
            "points": points,
            "x_ticks": x_ticks,
            "y_ticks": y_ticks,
            "annotation": annotation,
        }

    def _build_line_annotation(
        self,
        *,
        annotation_type: str | None,
        x_values: list[int],
        y_values: list[float],
        to_x: Any,
        to_y: Any,
        left: float,
        right: float,
        top: float,
        width: float,
        plot_height: float,
    ) -> dict[str, Any] | None:
        if not annotation_type:
            return None

        target_index: int | None = None
        lines: list[str] = []
        color = "#1e3a8a"

        if annotation_type == "fitness_max":
            max_fit = max(y_values)
            target_index = y_values.index(max_fit)
            lines = ["Fitness Tertinggi", f"Generasi ke-{x_values[target_index]}"]
            color = "#1e3a8a"
        elif annotation_type == "conflict_zero":
            zero_indices = [idx for idx, value in enumerate(y_values) if value == 0]
            if not zero_indices:
                return None
            target_index = zero_indices[0]
            lines = ["Konvergensi (0 Konflik)", f"Generasi ke-{x_values[target_index]}"]
            color = "#991b1b"
        elif annotation_type == "penalty_min":
            min_penalty = min(y_values)
            target_index = y_values.index(min_penalty)
            lines = ["Penalty Terendah", f"Generasi ke-{x_values[target_index]}"]
            color = "#5b21b6"

        if target_index is None:
            return None

        px = to_x(float(x_values[target_index]))
        py = to_y(float(y_values[target_index]))

        # Letakkan teks di sisi yang paling aman agar tidak terpotong tepi grafik.
        if px > width * 0.68:
            tx = max(left + 24, px - 260)
        else:
            tx = min(width - right - 260, px + 160)
        if py < top + 70:
            ty = py + 58
        else:
            ty = max(top + 40, py - 70)

        return {
            "x1": round(tx, 2),
            "y1": round(ty + 10, 2),
            "x2": round(px, 2),
            "y2": round(py, 2),
            "text_x": round(tx, 2),
            "text_y": round(ty, 2),
            "lines": lines,
            "color": color,
        }

    def _build_penalty_bar_chart(self, evaluation: dict[str, Any]) -> dict[str, Any]:
        bars = [
            {"label": "Hard", "value": float(evaluation.get("hard_penalty") or 0.0), "class": "hard"},
            {"label": "Preferensi", "value": float(evaluation.get("preference_penalty") or 0.0), "class": "preference"},
            {"label": "Fairness", "value": float(evaluation.get("fairness_penalty") or 0.0), "class": "fairness"},
        ]
        chart = self._build_bar_chart(bars, value_key="value")
        chart["plot"] = self._build_bar_plot(
            title="Grafik Komposisi Penalty",
            x_label="Komponen Penalty",
            y_label="Nilai Penalty",
            bars=bars,
        )
        return chart

    def _build_workload_bar_chart(self, workload_rows: list[dict[str, Any]]) -> dict[str, Any]:
        top_rows = sorted(workload_rows, key=lambda row: int(row.get("total_sks") or 0), reverse=True)[:10]
        bars = [
            {
                "label": str(row.get("dosen") or "-"),
                "value": float(row.get("total_sks") or 0),
                "class": "workload",
            }
            for row in top_rows
        ]
        chart = self._build_bar_chart(bars, value_key="value")
        chart["plot"] = self._build_bar_plot(
            title="Grafik Distribusi Beban Dosen",
            x_label="Dosen (10 Beban SKS Tertinggi)",
            y_label="Total SKS",
            bars=bars,
            truncate_labels=True,
        )
        return chart

    def _build_bar_chart(self, bars: list[dict[str, Any]], value_key: str = "value") -> dict[str, Any]:
        if not bars:
            return {"has_data": False, "bars": [], "max_value": 0.0, "total": 0.0}

        values = [float(item.get(value_key) or 0.0) for item in bars]
        max_value = max(max(values), 1e-12)
        chart_bars: list[dict[str, Any]] = []
        width = 80 / max(len(bars), 1)
        gap = min(2.0, width * 0.22)
        bar_width = max(width - gap, 2.0)

        for index, item in enumerate(bars):
            value = float(item.get(value_key) or 0.0)
            height = (value / max_value) * 82 if max_value else 0
            x = 10 + index * width + gap / 2
            y = 92 - height
            chart_bars.append(
                {
                    "label": item.get("label", "-"),
                    "value": value,
                    "class": item.get("class", "bar"),
                    "x": round(x, 2),
                    "y": round(y, 2),
                    "width": round(bar_width, 2),
                    "height": round(height, 2),
                }
            )

        return {
            "has_data": True,
            "bars": chart_bars,
            "max_value": max_value,
            "total": sum(values),
        }

    def _build_bar_plot(
        self,
        *,
        title: str,
        x_label: str,
        y_label: str,
        bars: list[dict[str, Any]],
        truncate_labels: bool = False,
    ) -> dict[str, Any]:
        width = self.CHART_WIDTH
        height = self.CHART_HEIGHT
        left = self.PLOT_LEFT
        right = self.PLOT_RIGHT
        top = self.PLOT_TOP
        bottom = 110 if truncate_labels else self.PLOT_BOTTOM
        plot_width = width - left - right
        plot_height = height - top - bottom
        plot_bottom = height - bottom

        values = [float(item.get("value") or 0.0) for item in bars]
        max_value = max(max(values) if values else 0.0, 1e-12)
        y_max = max_value * 1.15 if max_value > 0 else 1.0

        def to_y(value: float) -> float:
            return top + (1 - (value / y_max)) * plot_height

        y_ticks = []
        for value in self._build_y_ticks(0.0, y_max, force_integer=False):
            y_ticks.append({"value": value, "y": round(to_y(value), 2), "label": self._format_tick(value)})

        count = max(len(bars), 1)
        step = plot_width / count
        bar_width = min(step * 0.58, 80)
        plot_bars: list[dict[str, Any]] = []
        for index, item in enumerate(bars):
            value = float(item.get("value") or 0.0)
            x_center = left + step * index + step / 2
            bar_height = plot_bottom - to_y(value)
            raw_label = str(item.get("label") or "-")
            label = self._shorten_label(raw_label, 18 if truncate_labels else 14)
            plot_bars.append(
                {
                    "label": label,
                    "full_label": raw_label,
                    "value": value,
                    "value_label": self._format_tick(value),
                    "class": item.get("class", "bar"),
                    "x": round(x_center - bar_width / 2, 2),
                    "y": round(to_y(value), 2),
                    "width": round(bar_width, 2),
                    "height": round(max(bar_height, 0.0), 2),
                    "label_x": round(x_center, 2),
                }
            )

        return {
            "title": title,
            "x_label": x_label,
            "y_label": y_label,
            "view_box": f"0 0 {width} {height}",
            "width": width,
            "height": height,
            "left": left,
            "right": right,
            "top": top,
            "bottom": bottom,
            "plot_width": plot_width,
            "plot_height": plot_height,
            "plot_right": width - right,
            "plot_bottom": plot_bottom,
            "bars": plot_bars,
            "y_ticks": y_ticks,
            "rotate_labels": truncate_labels,
        }

    @staticmethod
    def _build_x_ticks(min_x: int, max_x: int, max_ticks: int = 6) -> list[int]:
        if min_x == max_x:
            return [min_x]
        span = max_x - min_x
        step = max(1, ceil(span / max(1, max_ticks - 1)))
        ticks = [min_x]
        value = min_x + step
        while value < max_x:
            ticks.append(value)
            value += step
        if ticks[-1] != max_x:
            ticks.append(max_x)
        return ticks[: max_ticks + 1]

    @staticmethod
    def _build_y_ticks(min_y: float, max_y: float, max_ticks: int = 5, force_integer: bool = False) -> list[float]:
        if max_y <= min_y:
            return [min_y, max_y]
        step = (max_y - min_y) / max(1, max_ticks - 1)
        ticks = [min_y + step * idx for idx in range(max_ticks)]
        if force_integer:
            unique = []
            for tick in ticks:
                rounded = int(round(tick))
                if rounded not in unique:
                    unique.append(rounded)
            if int(round(max_y)) not in unique:
                unique.append(int(round(max_y)))
            return [float(item) for item in unique]
        return ticks

    @staticmethod
    def _format_tick(value: float, integer: bool = False) -> str:
        if integer:
            return str(int(round(value)))
        abs_value = abs(value)
        if abs_value >= 1000:
            return f"{value:,.0f}".replace(",", ".")
        if 0 < abs_value < 0.001:
            return f"{value:.6f}"
        if abs_value < 10:
            return f"{value:.4f}".rstrip("0").rstrip(".")
        return f"{value:.2f}".rstrip("0").rstrip(".")

    @staticmethod
    def _shorten_label(value: str, max_length: int) -> str:
        clean = " ".join(value.split())
        if len(clean) <= max_length:
            return clean
        return clean[: max_length - 1] + "…"

    @staticmethod
    def format_duration(seconds: float | int | None) -> str:
        if seconds is None:
            return "-"
        total_seconds = int(round(float(seconds)))
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"00:{minutes:02d}:{secs:02d}"
