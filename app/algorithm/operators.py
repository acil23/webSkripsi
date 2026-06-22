import copy
import random


def tournament_selection(population, k=3):
    candidates = random.sample(population, k)
    return max(candidates, key=lambda individual: individual.fitness)


def crossover(parent1, parent2, crossover_rate=0.8):
    if random.random() > crossover_rate:
        return copy.deepcopy(parent1), copy.deepcopy(parent2)

    child1 = copy.deepcopy(parent1)
    child2 = copy.deepcopy(parent2)

    for i in range(len(parent1.chromosome)):
        if random.random() < 0.5:
            child1.chromosome[i], child2.chromosome[i] = child2.chromosome[i], child1.chromosome[i]

    child1.fitness = 0.0
    child1.conflicts = []
    child2.fitness = 0.0
    child2.conflicts = []

    return child1, child2


def mutation(individual, all_slots, all_rooms, candidates, pref_info, mutation_rate=0.1):
    """
    Mutasi ringan:
    - ganti slot,
    - ganti ruang,
    - ganti dosen dari kandidat preferensi yang sudah difilter oleh data_loader.
    """
    for gene in individual.chromosome:
        if random.random() >= mutation_rate:
            continue

        choice = random.random()

        if choice < 0.4:
            gene["slot_id"] = random.choice(all_slots)["slot_id"]

        elif choice < 0.8:
            gene["room_id"] = random.choice(all_rooms)["room_id"]

        else:
            kode_mk = gene["kode_mk"]
            possible_dosen = candidates.get(kode_mk, [])

            if len(possible_dosen) > 1:
                new_dosen = random.choice(possible_dosen)
                gene["dosen"] = new_dosen

                info = pref_info.get((new_dosen, kode_mk), {})
                gene["dosen_priority"] = info.get("prioritas", 99)
                gene["metode_pemilihan"] = "Mutasi Preferensi"

    individual.fitness = 0.0
    individual.conflicts = []
