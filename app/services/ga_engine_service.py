"""Service integrasi Memetic Algorithm dengan aplikasi web.

Service ini membungkus kode algoritma lama agar dapat dipanggil dari
SchedulingController tanpa mengubah logika inti GA, FIHC, dan Robin Hood.
"""

from __future__ import annotations

import random
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.algorithm.data_loader import load_all_data
from app.algorithm.ga_engine import GeneticAlgorithm
from app.core.paths import UPLOADED_DIR
from app.entities.algorithm_entities import ParameterAlgoritma
from app.entities.result_entities import (
    BebanDosen,
    EvaluasiJadwal,
    Jadwal,
    JadwalItem,
    LogKonvergensi,
    PenjadwalanResult,
)


class GAEngineService:
    """Adapter service dari kode algoritma eksperimental ke use case web UC-04."""

    def execute(
        self,
        parameter: ParameterAlgoritma,
        semester_active: str,
        data_dir: Path = UPLOADED_DIR,
        class_config_path: Path | None = None,
        progress_callback=None,
    ) -> PenjadwalanResult:
        if parameter is None or not parameter.is_valid():
            raise ValueError("Parameter algoritma belum valid.")

        params = parameter.to_engine_params()
        params["semester_active"] = semester_active
        if progress_callback is not None:
            params["progress_callback"] = progress_callback
        seed = params.get("seed")
        if seed is not None:
            random.seed(int(seed))
            np.random.seed(int(seed))

        class_config_path = class_config_path or data_dir / f"Konfigurasi_Pembukaan_Kelas_{semester_active}.csv"
        if not class_config_path.exists():
            raise FileNotFoundError(f"Konfigurasi pembukaan kelas belum tersedia: {class_config_path.name}")

        start_time = time.time()
        data = load_all_data(
            data_dir=str(data_dir),
            semester_active=semester_active,
            class_config_path=str(class_config_path),
        )

        engine = GeneticAlgorithm(data, params)
        best_individual = engine.run()
        duration = time.time() - start_time

        detail = engine.fitness_calc.calculate_detail(best_individual.chromosome)
        jadwal = self._build_jadwal(best_individual.chromosome, data)
        evaluasi = self._build_evaluasi(detail, best_individual, duration)
        beban_dosen = self._build_beban_dosen(best_individual.chromosome, data.get("fairness_dosen", []))
        logs = self._build_logs(engine.history_fitness, engine.history_conflicts)

        return PenjadwalanResult(
            jadwal=jadwal,
            evaluasi=evaluasi,
            beban_dosen=beban_dosen,
            log_konvergensi=logs,
            parameter=parameter.to_dict(),
            semester_active=semester_active,
            model_name=params.get("model_name", "MA_FIHC_ROBINHOOD"),
        )

    def _build_jadwal(self, chromosome: list[dict[str, Any]], data: dict[str, Any]) -> Jadwal:
        slots_lookup = {slot["slot_id"]: slot for slot in data["slots"]}
        rooms_lookup = {room["room_id"]: room for room in data["rooms"]}
        items: list[JadwalItem] = []

        for index, gene in enumerate(chromosome, start=1):
            slot = slots_lookup[gene["slot_id"]]
            room = rooms_lookup[gene["room_id"]]
            items.append(
                JadwalItem(
                    item_id=f"JDL-{index:04d}",
                    class_id=gene["class_id"],
                    kode_mk=str(gene["kode_mk"]),
                    mata_kuliah=str(gene["nama_mk"]),
                    sks=int(gene["sks"]),
                    kelas=str(gene.get("parallel", "-")),
                    dosen=str(gene["dosen"]),
                    hari=str(slot["Hari"]),
                    jam_mulai=str(slot["Mulai"]),
                    jam_selesai=str(slot["Selesai"]),
                    ruang=str(room["Ruang"]),
                    kapasitas_ruang=int(room["Kapasitas"]),
                    jumlah_mahasiswa=int(gene.get("jumlah_mhs", 0)),
                    jenis_mk=str(gene.get("jenis_mk", "-")),
                    semester=str(gene.get("semester", "-")),
                    prioritas_dosen=int(gene.get("dosen_priority", 99)),
                    metode_pemilihan=str(gene.get("metode_pemilihan", "-")),
                )
            )

        hari_order = {"senin": 1, "selasa": 2, "rabu": 3, "kamis": 4, "jumat": 5, "sabtu": 6}
        items.sort(key=lambda item: (hari_order.get(item.hari.lower(), 99), item.jam_mulai, item.ruang, item.kode_mk, item.kelas))

        return Jadwal(
            jadwal_id=f"JADWAL-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            generated_at=datetime.now(),
            items=items,
        )

    def _build_evaluasi(self, detail: dict[str, Any], best_individual: Any, duration: float) -> EvaluasiJadwal:
        return EvaluasiJadwal(
            total_conflict=int(len(best_individual.conflicts)),
            fitness=float(best_individual.fitness),
            total_penalty=float(detail.get("total_penalty", 0.0)),
            hard_penalty=float(detail.get("hard_penalty", 0.0)),
            preference_penalty=float(detail.get("preference_penalty", 0.0)),
            fairness_penalty=float(detail.get("fairness_penalty", 0.0)),
            standar_deviasi_beban=float(detail.get("std_dev", 0.0)),
            waktu_komputasi=float(duration),
            capacity_conflicts=int(detail.get("capacity_conflicts", 0)),
            room_conflicts=int(detail.get("room_conflicts", 0)),
            lecturer_conflicts=int(detail.get("lecturer_conflicts", 0)),
            avg_sks=float(detail.get("avg_sks", 0.0)),
            min_sks=int(detail.get("min_sks", 0)),
            max_sks=int(detail.get("max_sks", 0)),
            jumlah_dosen_fairness=int(detail.get("jumlah_dosen_fairness", 0)),
        )

    def _build_beban_dosen(self, chromosome: list[dict[str, Any]], fairness_dosen: list[str] | set[str]) -> list[BebanDosen]:
        fairness_set = set(fairness_dosen or [])
        by_dosen: dict[str, dict[str, Any]] = {}

        for gene in chromosome:
            dosen = str(gene.get("dosen", ""))
            if not dosen or "Unknown" in dosen or "Belum" in dosen:
                continue
            row = by_dosen.setdefault(
                dosen,
                {
                    "total_sks": 0,
                    "jumlah_sesi": 0,
                    "mk_unik": set(),
                    "dihitung_fairness": dosen in fairness_set if fairness_set else True,
                },
            )
            row["total_sks"] += int(gene.get("sks", 0))
            row["jumlah_sesi"] += 1
            row["mk_unik"].add(str(gene.get("kode_mk", "")))

        workloads = [
            BebanDosen(
                dosen=dosen,
                total_sks=int(value["total_sks"]),
                jumlah_sesi=int(value["jumlah_sesi"]),
                jumlah_mk_unik=len(value["mk_unik"]),
                dihitung_fairness=bool(value["dihitung_fairness"]),
            )
            for dosen, value in by_dosen.items()
        ]
        workloads.sort(key=lambda item: (not item.dihitung_fairness, -item.total_sks, item.dosen))
        return workloads

    def _build_logs(self, history_fitness: list[float], history_conflicts: list[int]) -> list[LogKonvergensi]:
        return [
            LogKonvergensi(
                generasi=index,
                best_fitness=float(fitness),
                total_conflict=int(conflict),
            )
            for index, (fitness, conflict) in enumerate(zip(history_fitness, history_conflicts), start=1)
        ]
