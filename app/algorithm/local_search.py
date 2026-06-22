import random
import re


class LocalSearch:
    def __init__(
        self,
        fitness_calculator,
        candidates,
        pref_info,
        dosen_hierarchy,
        mk_hierarchy,
        fairness_dosen=None,
        allowed_dosen=None,
    ):
        self.fitness_calc = fitness_calculator
        self.candidates = candidates
        self.pref_info = pref_info
        self.dosen_hierarchy = dosen_hierarchy
        self.mk_hierarchy = mk_hierarchy
        self.fairness_dosen = set(fairness_dosen or [])
        self.allowed_dosen = set(allowed_dosen or [])

    def normalize_name(self, name):
        if not isinstance(name, str):
            return ""

        text = name.lower()
        titles = [
            "prof.", "dr.", "drs.", "dra.", "ir.", "eng.", "h.", "hj.",
            "s.kom.", "s.t.", "m.t.", "m.kom.", "m.sc.", "m.cs.", "m.eng.",
            "ph.d.", "ph.d", "mba.", "mba"
        ]

        for title in titles:
            text = text.replace(title, "")

        text = text.split(",")[0]
        text = re.sub(r"[^a-z0-9 ]+", " ", text)
        return " ".join(text.split())

    def is_known_hierarchy_value(self, value):
        if value is None:
            return False

        text = str(value).strip().lower()
        return text not in {"", "-", "nan", "none", "tidak tersedia", "n/a", "null"}

    def is_known_dosen(self, dosen_name):
        text = str(dosen_name).strip().lower()
        return text and "unknown" not in text and "belum" not in text

    def is_fairness_dosen(self, dosen_name):
        if not self.is_known_dosen(dosen_name):
            return False

        if self.fairness_dosen:
            return dosen_name in self.fairness_dosen

        return True

    def is_dosen_busy(self, chromosome, dosen_name, slot_id, ignore_gene=None):
        for gene in chromosome:
            if ignore_gene is not None and gene is ignore_gene:
                continue

            if gene["dosen"] == dosen_name:
                if self.fitness_calc.check_overlap(gene["slot_id"], slot_id):
                    return True

        return False

    def _same_hierarchy(self, d_h, mk_h, level):
        dosen_value = d_h.get(level)
        mk_value = mk_h.get(level)

        return (
            self.is_known_hierarchy_value(dosen_value)
            and self.is_known_hierarchy_value(mk_value)
            and str(dosen_value).strip().lower() == str(mk_value).strip().lower()
        )

    def find_best_replacement_candidate(self, kode_mk, target_underload_dosens):
        """
        Mencari kandidat pengganti untuk Robin Hood.
        Target hanya diambil dari dosen yang masuk underloaded fairness set.
        """
        labels = {
            1: "Sesuai Preferensi",
            2: "Kecocokan Ranting Ilmu",
            3: "Kecocokan Cabang Ilmu",
            4: "Kecocokan Bidang Ilmu",
        }

        target_underload_dosens = [
            d for d in target_underload_dosens
            if self.is_fairness_dosen(d)
        ]

        if not target_underload_dosens:
            return None, 99, "Tidak Ada Kandidat"

        # P1: kandidat preferensi yang juga underloaded.
        pref_candidates = self.candidates.get(kode_mk, [])
        p1_matches = [d for d in pref_candidates if d in target_underload_dosens]

        if p1_matches:
            chosen = random.choice(p1_matches)
            prio = self.pref_info.get((chosen, kode_mk), {}).get("prioritas", 1)
            return chosen, prio, labels[1]

        # P2-P4: fallback hierarki.
        mk_h = self.mk_hierarchy.get(kode_mk)
        if not mk_h:
            return None, 99, "Hierarki MK Tidak Ada"

        levels = [
            ("ranting", 2, labels[2]),
            ("cabang", 3, labels[3]),
            ("bidang", 4, labels[4]),
        ]

        for level, priority, label in levels:
            matches = []

            for dosen in target_underload_dosens:
                d_h = self.dosen_hierarchy.get(self.normalize_name(dosen))
                if not d_h:
                    continue

                if self._same_hierarchy(d_h, mk_h, level):
                    matches.append(dosen)

            if matches:
                return random.choice(matches), priority, label

        return None, 99, "Dosen Cadangan Tidak Cocok"

    def resolve_conflicts(self, individual, all_slots, all_rooms):
        """
        FIHC: memperbaiki konflik hard constraint dengan perubahan slot/ruang.
        """
        max_repair_attempts = 30

        for _ in range(max_repair_attempts):
            current_fitness, conflicts = self.fitness_calc.calculate(individual.chromosome)

            if not conflicts:
                break

            problematic_indices = []
            for i, gene in enumerate(individual.chromosome):
                for msg in conflicts:
                    if gene["nama_mk"] in msg or gene["dosen"] in msg:
                        problematic_indices.append(i)
                        break

            if not problematic_indices:
                break

            idx = random.choice(problematic_indices)
            gene = individual.chromosome[idx]

            for _ in range(50):
                old_slot = gene["slot_id"]
                old_room = gene["room_id"]

                gene["slot_id"] = random.choice(all_slots)["slot_id"]
                gene["room_id"] = random.choice(all_rooms)["room_id"]

                new_fitness, _ = self.fitness_calc.calculate(individual.chromosome)

                if new_fitness > current_fitness:
                    current_fitness = new_fitness
                    break

                gene["slot_id"] = old_slot
                gene["room_id"] = old_room

        return individual

    def apply_load_balancing(self, individual):
        """
        Robin Hood Load Balancing.

        Aturan penting:
        - Workload yang diratakan hanya dosen dengan Dihitung Dalam Fairness = Ya.
        - Dosen lintas departemen tetap boleh muncul di jadwal, tetapi tidak menjadi target Robin Hood.
        - Perubahan TIDAK boleh memperburuk hard constraint.
        - Perubahan diterima jika hard_penalty tidak naik dan total_penalty tidak naik.
        """
        workload = {}

        for gene in individual.chromosome:
            dosen = gene["dosen"]
            if self.is_fairness_dosen(dosen):
                workload[dosen] = workload.get(dosen, 0) + int(gene["sks"])

        if not workload:
            return individual

        avg_load = sum(workload.values()) / len(workload)
        tolerance = 1

        overloaded = [d for d, w in workload.items() if w > avg_load + tolerance]
        underloaded = [d for d, w in workload.items() if w < avg_load - tolerance]

        if not overloaded or not underloaded:
            return individual

        current_detail = self.fitness_calc.calculate_detail(individual.chromosome)

        for _ in range(30):
            if not overloaded or not underloaded:
                break

            rich_dosen = random.choice(overloaded)

            movable_genes = [
                gene for gene in individual.chromosome
                if gene["dosen"] == rich_dosen
            ]

            if not movable_genes:
                continue

            gene_target = random.choice(movable_genes)

            target_dosen, priority, method_label = self.find_best_replacement_candidate(
                gene_target["kode_mk"],
                underloaded,
            )

            if not target_dosen:
                continue

            old_dosen = gene_target["dosen"]
            old_priority = gene_target.get("dosen_priority", 99)
            old_method = gene_target.get("metode_pemilihan", "Inisialisasi Awal")
            old_slot = gene_target["slot_id"]

            # Jika target sibuk, coba geser slot gen target.
            if self.is_dosen_busy(
                individual.chromosome,
                target_dosen,
                gene_target["slot_id"],
                ignore_gene=gene_target,
            ):
                available_slots = list(self.fitness_calc.slot_details.keys())
                random.shuffle(available_slots)

                for test_slot in available_slots[:5]:
                    if not self.is_dosen_busy(
                        individual.chromosome,
                        target_dosen,
                        test_slot,
                        ignore_gene=gene_target,
                    ):
                        gene_target["slot_id"] = test_slot
                        break

            # Jika tetap sibuk, batalkan.
            if self.is_dosen_busy(
                individual.chromosome,
                target_dosen,
                gene_target["slot_id"],
                ignore_gene=gene_target,
            ):
                gene_target["slot_id"] = old_slot
                continue

            gene_target["dosen"] = target_dosen
            gene_target["dosen_priority"] = priority
            gene_target["metode_pemilihan"] = method_label

            new_detail = self.fitness_calc.calculate_detail(individual.chromosome)

            hard_not_worse = new_detail["hard_penalty"] <= current_detail["hard_penalty"]
            total_not_worse = new_detail["total_penalty"] <= current_detail["total_penalty"]

            if hard_not_worse and total_not_worse:
                sks = int(gene_target["sks"])
                workload[rich_dosen] -= sks
                workload[target_dosen] = workload.get(target_dosen, 0) + sks
                current_detail = new_detail
            else:
                gene_target["dosen"] = old_dosen
                gene_target["dosen_priority"] = old_priority
                gene_target["metode_pemilihan"] = old_method
                gene_target["slot_id"] = old_slot

            overloaded = [d for d, w in workload.items() if w > avg_load + tolerance]
            underloaded = [d for d, w in workload.items() if w < avg_load - tolerance]

        return individual
