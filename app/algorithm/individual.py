import random


class Individual:
    def __init__(self, all_classes, all_slots, all_rooms):
        self.all_classes = all_classes
        self.all_slots = all_slots
        self.all_rooms = all_rooms

        self.chromosome = []
        self.fitness = 0.0
        self.conflicts = []

    def initialize_random(self):
        self.chromosome = []

        for kelas in self.all_classes:
            random_slot = random.choice(self.all_slots)
            random_room = random.choice(self.all_rooms)

            gene = {
                "class_id": kelas["class_id"],
                "slot_id": random_slot["slot_id"],
                "room_id": random_room["room_id"],
                "kode_mk": kelas["kode_mk"],
                "nama_mk": kelas["nama_mk"],
                "sks": kelas["sks"],
                "sks_asli": kelas.get("sks_asli", kelas["sks"]),
                "dosen": kelas["dosen"],
                "jumlah_mhs": kelas["jumlah_mhs"],
                "semester": kelas.get("semester", 0),
                "parallel": kelas.get("parallel", "-"),
                "jenis_mk": kelas.get("jenis_mk", "-"),
                "estimasi_peserta_mk": kelas.get("estimasi_peserta_mk", 0),
                "jumlah_kelas_final_mk": kelas.get("jumlah_kelas_final_mk", 0),
                "dosen_priority": kelas.get("dosen_priority", 99),
                "metode_pemilihan": kelas.get("metode_pemilihan", "Inisialisasi Awal"),
                "is_split": kelas.get("is_split", False),
            }

            self.chromosome.append(gene)

    def compute_fitness(self, fitness_calculator):
        score, conflict_list = fitness_calculator.calculate(self.chromosome)
        self.fitness = score
        self.conflicts = conflict_list
        return self.fitness

    def __str__(self):
        return f"Individu | Fit: {self.fitness:.6f} | Konflik: {len(self.conflicts)}"
