import copy
import random

from app.algorithm.individual import Individual
from app.algorithm.fitness import FitnessCalculator
from app.algorithm import operators as ops
from app.algorithm.local_search import LocalSearch


class GeneticAlgorithm:
    def __init__(self, data, params):
        self.data = data
        self.params = params

        self.classes = data["classes"]
        self.slots = data["slots"]
        self.rooms = data["rooms"]
        self.candidates = data["candidates"]
        self.pref_info = data["pref_info"]
        self.dosen_hierarchy = data.get("dosen_hierarchy", {})
        self.mk_hierarchy = data.get("mk_hierarchy", {})
        self.allowed_dosen = set(data.get("allowed_dosen", []))
        self.fairness_dosen = set(data.get("fairness_dosen", []))

        self.use_local_search = bool(params.get("use_local_search", True))
        self.use_load_balancing = bool(params.get("use_load_balancing", True))
        # Callback opsional untuk integrasi web. Tidak mengubah logika algoritma;
        # hanya mengirim status generasi ke controller.
        self.progress_callback = params.get("progress_callback")

        self.fitness_calc = FitnessCalculator(
            self.slots,
            self.rooms,
            fairness_dosen=self.fairness_dosen,
        )

        self.ls_engine = LocalSearch(
            fitness_calculator=self.fitness_calc,
            candidates=self.candidates,
            pref_info=self.pref_info,
            dosen_hierarchy=self.dosen_hierarchy,
            mk_hierarchy=self.mk_hierarchy,
            fairness_dosen=self.fairness_dosen,
            allowed_dosen=self.allowed_dosen,
        )

        self.population = []
        self.best_individual = None
        self.history_fitness = []
        self.history_conflicts = []

    def initialize_population(self):
        print(">>> Inisialisasi populasi awal...")
        self.population = []

        for _ in range(self.params["pop_size"]):
            individual = Individual(self.classes, self.slots, self.rooms)
            individual.initialize_random()
            individual.compute_fitness(self.fitness_calc)
            self.population.append(individual)

        self.population.sort(key=lambda x: x.fitness, reverse=True)
        self.best_individual = copy.deepcopy(self.population[0])

    def _apply_memetic_steps(self, child):
        """
        Menerapkan FIHC dan/atau Robin Hood sesuai konfigurasi model.

        Urutan untuk model MA:
        1. FIHC memperbaiki konflik.
        2. Robin Hood meratakan beban tanpa memperburuk hard constraint.
        3. FIHC ringan dijalankan ulang untuk membersihkan konflik yang masih tersisa
           akibat perubahan slot pada tahap balancing.
        """
        ls_chance = self.params.get("ls_chance", 0.1)

        if random.random() >= ls_chance:
            return child

        if self.use_local_search:
            self.ls_engine.resolve_conflicts(child, self.slots, self.rooms)

        if self.use_load_balancing:
            self.ls_engine.apply_load_balancing(child)

            # Post-repair: menjaga agar tahap balancing tidak meninggalkan konflik yang sebenarnya masih bisa diperbaiki.
            if self.use_local_search:
                self.ls_engine.resolve_conflicts(child, self.slots, self.rooms)

        return child

    def evolve_generation(self):
        new_population = []

        elitism_count = self.params.get("elitism", 1)
        new_population.extend(copy.deepcopy(self.population[:elitism_count]))

        while len(new_population) < self.params["pop_size"]:
            parent1 = ops.tournament_selection(self.population)
            parent2 = ops.tournament_selection(self.population)

            child1, child2 = ops.crossover(
                parent1,
                parent2,
                self.params["crossover_rate"],
            )

            ops.mutation(
                child1,
                self.slots,
                self.rooms,
                self.candidates,
                self.pref_info,
                self.params["mutation_rate"],
            )
            ops.mutation(
                child2,
                self.slots,
                self.rooms,
                self.candidates,
                self.pref_info,
                self.params["mutation_rate"],
            )

            self._apply_memetic_steps(child1)
            self._apply_memetic_steps(child2)

            child1.compute_fitness(self.fitness_calc)
            child2.compute_fitness(self.fitness_calc)

            new_population.append(child1)
            if len(new_population) < self.params["pop_size"]:
                new_population.append(child2)

        new_population.sort(key=lambda x: x.fitness, reverse=True)
        self.population = new_population

        if self.population[0].fitness > self.best_individual.fitness:
            self.best_individual = copy.deepcopy(self.population[0])

    def run(self):
        self.initialize_population()

        max_generations = self.params["max_generations"]
        model_label = self.params.get("model_name", "MODEL")

        print(f"\n🚀 Menjalankan {model_label} - {max_generations} generasi")
        print(f"   FIHC          : {self.use_local_search}")
        print(f"   Robin Hood    : {self.use_load_balancing}")
        print(f"   Fairness dosen: {len(self.fairness_dosen)} dosen")
        print("-" * 70)

        for generation in range(1, max_generations + 1):
            self.evolve_generation()

            # Log memakai best-so-far agar grafik konvergensi stabil.
            self.history_fitness.append(self.best_individual.fitness)
            self.history_conflicts.append(len(self.best_individual.conflicts))

            if self.progress_callback:
                self.progress_callback({
                    "generation": generation,
                    "max_generations": max_generations,
                    "best_fitness": self.best_individual.fitness,
                    "total_conflict": len(self.best_individual.conflicts),
                })

            if generation % 10 == 0 or generation == 1:
                best_now = self.population[0]
                print(
                    f"Gen {generation:4} | "
                    f"Konflik best-now: {len(best_now.conflicts):3} | "
                    f"Konflik best-so-far: {len(self.best_individual.conflicts):3} | "
                    f"Fit: {self.best_individual.fitness:.6f}"
                )

        return self.best_individual
