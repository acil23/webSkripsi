import numpy as np


class FitnessCalculator:
    """
    Fitness berbasis inverse penalty untuk evaluasi jadwal.

    Hard constraint yang dihitung:
    1. Kapasitas ruang.
    2. Tabrakan ruang pada waktu beririsan.
    3. Tabrakan dosen pada waktu beririsan.

    Soft constraint yang dihitung:
    1. Penalti pemilihan dosen berdasarkan prioritas/metode.
    2. Fairness beban SKS, hanya untuk dosen yang masuk fairness_dosen.
    """

    def __init__(self, slots, rooms, fairness_dosen=None):
        self.rooms = {r["room_id"]: r for r in rooms}
        self.fairness_dosen = set(fairness_dosen or [])

        self.slot_details = {}
        for slot in slots:
            start_min = self._time_to_minutes(slot["Mulai"])
            end_min = self._time_to_minutes(slot["Selesai"])
            self.slot_details[slot["slot_id"]] = {
                "hari": slot["Hari"],
                "start": start_min,
                "end": end_min,
            }

        # Bobot hard constraint.
        self.WEIGHT_HARD = 10000

        # Bobot soft constraint preferensi/pemilihan dosen.
        self.WEIGHT_PREF_PRIO_1 = 0
        self.WEIGHT_PREF_PRIO_2 = 2
        self.WEIGHT_PREF_PRIO_3 = 5
        self.WEIGHT_PREF_PRIO_4 = 10
        self.WEIGHT_PREF_UNKNOWN = 50

        # Bobot fairness beban dosen.
        self.FAIRNESS_STD_THRESHOLD = 2.5
        self.WEIGHT_FAIR_LINEAR = 50
        self.WEIGHT_FAIR_CUBIC = 100

    def _time_to_minutes(self, time_str):
        hour, minute = map(int, str(time_str).split(":")[:2])
        return hour * 60 + minute

    def check_overlap(self, slot1_id, slot2_id):
        """True jika dua slot berada di hari sama dan waktunya beririsan."""
        if slot1_id == slot2_id:
            return True

        s1 = self.slot_details[slot1_id]
        s2 = self.slot_details[slot2_id]

        if s1["hari"] != s2["hari"]:
            return False

        return (s1["start"] < s2["end"]) and (s2["start"] < s1["end"])

    def _preference_penalty(self, priority):
        try:
            priority = int(priority)
        except Exception:
            priority = 99

        if priority == 1:
            return self.WEIGHT_PREF_PRIO_1
        if priority == 2:
            return self.WEIGHT_PREF_PRIO_2
        if priority == 3:
            return self.WEIGHT_PREF_PRIO_3
        if priority == 4:
            return self.WEIGHT_PREF_PRIO_4

        return self.WEIGHT_PREF_UNKNOWN

    def _is_known_dosen(self, dosen_name):
        text = str(dosen_name).strip().lower()
        return text and "unknown" not in text and "belum" not in text

    def _include_in_fairness(self, dosen_name):
        """
        Jika fairness_dosen diberikan, fairness hanya dihitung untuk dosen dalam set tersebut.
        Jika tidak diberikan, fallback menghitung semua dosen valid agar kompatibel dengan kode lama.
        """
        if not self._is_known_dosen(dosen_name):
            return False

        if self.fairness_dosen:
            return dosen_name in self.fairness_dosen

        return True

    def calculate(self, chromosome):
        detail = self.calculate_detail(chromosome)
        return detail["fitness"], detail["conflicts"]

    def calculate_detail(self, chromosome):
        conflicts = []

        hard_penalty = 0
        preference_penalty = 0
        fairness_penalty = 0

        genes_by_room = {}
        genes_by_dosen = {}
        fairness_workload = {}
        all_workload = {}

        for gene in chromosome:
            room_id = gene["room_id"]
            dosen_name = gene["dosen"]

            # 1. Kapasitas ruang.
            room_capacity = int(self.rooms[room_id]["Kapasitas"])
            jumlah_mhs = int(gene.get("jumlah_mhs", 0))

            if jumlah_mhs > room_capacity:
                hard_penalty += self.WEIGHT_HARD
                conflicts.append(
                    f"[Kapasitas] {gene['nama_mk']} kelas {gene.get('parallel', '-')} "
                    f"jumlah {jumlah_mhs} > kapasitas {room_capacity}"
                )

            # 2. Penalti preferensi/metode pengampu.
            preference_penalty += self._preference_penalty(gene.get("dosen_priority", 99))

            genes_by_room.setdefault(room_id, []).append(gene)
            genes_by_dosen.setdefault(dosen_name, []).append(gene)

            # Workload seluruh dosen valid, untuk pelaporan tambahan.
            if self._is_known_dosen(dosen_name):
                all_workload[dosen_name] = all_workload.get(dosen_name, 0) + int(gene["sks"])

            # Workload fairness hanya dosen internal/yang ditandai dihitung fairness.
            if self._include_in_fairness(dosen_name):
                fairness_workload[dosen_name] = fairness_workload.get(dosen_name, 0) + int(gene["sks"])

        # 3. Tabrakan ruang.
        for room_id, class_list in genes_by_room.items():
            for i in range(len(class_list)):
                for j in range(i + 1, len(class_list)):
                    g1 = class_list[i]
                    g2 = class_list[j]
                    if self.check_overlap(g1["slot_id"], g2["slot_id"]):
                        hard_penalty += self.WEIGHT_HARD
                        conflicts.append(
                            f"[Tabrakan Ruang] {g1['nama_mk']} kelas {g1.get('parallel', '-')} "
                            f"vs {g2['nama_mk']} kelas {g2.get('parallel', '-')}"
                        )

        # 4. Tabrakan dosen.
        for dosen_name, class_list in genes_by_dosen.items():
            if not self._is_known_dosen(dosen_name):
                continue

            for i in range(len(class_list)):
                for j in range(i + 1, len(class_list)):
                    g1 = class_list[i]
                    g2 = class_list[j]
                    if self.check_overlap(g1["slot_id"], g2["slot_id"]):
                        hard_penalty += self.WEIGHT_HARD
                        conflicts.append(
                            f"[Tabrakan Dosen] {dosen_name}: {g1['nama_mk']} kelas {g1.get('parallel', '-')} "
                            f"vs {g2['nama_mk']} kelas {g2.get('parallel', '-')}"
                        )

        # 5. Fairness beban SKS.
        fairness_loads = list(fairness_workload.values())
        std_dev = float(np.std(fairness_loads)) if fairness_loads else 0.0
        avg_sks = float(np.mean(fairness_loads)) if fairness_loads else 0.0
        min_sks = int(np.min(fairness_loads)) if fairness_loads else 0
        max_sks = int(np.max(fairness_loads)) if fairness_loads else 0

        if fairness_loads:
            if std_dev > self.FAIRNESS_STD_THRESHOLD:
                fairness_penalty += (std_dev ** 3) * self.WEIGHT_FAIR_CUBIC
            else:
                fairness_penalty += std_dev * self.WEIGHT_FAIR_LINEAR

        total_penalty = hard_penalty + preference_penalty + fairness_penalty
        fitness = 1.0 / (1.0 + total_penalty)

        return {
            "fitness": fitness,
            "conflicts": conflicts,
            "total_penalty": float(total_penalty),
            "hard_penalty": float(hard_penalty),
            "preference_penalty": float(preference_penalty),
            "fairness_penalty": float(fairness_penalty),
            "std_dev": std_dev,
            "avg_sks": avg_sks,
            "min_sks": min_sks,
            "max_sks": max_sks,
            "jumlah_dosen_fairness": len(fairness_workload),
            "fairness_workload": fairness_workload,
            "all_workload": all_workload,
            "total_conflicts": len(conflicts),
            "capacity_conflicts": sum(1 for c in conflicts if "[Kapasitas]" in c),
            "room_conflicts": sum(1 for c in conflicts if "[Tabrakan Ruang]" in c),
            "lecturer_conflicts": sum(1 for c in conflicts if "[Tabrakan Dosen]" in c),
        }

    def evaluate_detail(self, chromosome):
        """Wrapper untuk kompatibilitas dengan main_ga."""
        detail = self.calculate_detail(chromosome)
        detail_without_large_maps = dict(detail)
        detail_without_large_maps.pop("conflicts", None)
        detail_without_large_maps.pop("fairness_workload", None)
        detail_without_large_maps.pop("all_workload", None)
        return detail_without_large_maps
