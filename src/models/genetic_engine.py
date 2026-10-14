"""Motor de Algoritmo Genético real para optimización en 1D y 2D."""
import random
from models.contracts import AlgorithmConfig, Generation, Individual, Objective


class GeneticEngine:
    """Implementa selección, cruza, mutación y elitismo cumpliendo EvolutionEngine."""

    def __init__(self, seed: int | None = None):
        """Permite semilla opcional; si es None usa entropía del sistema."""
        self.seed = seed

    def run(self, config: AlgorithmConfig) -> list[Generation]:
        """Ejecuta el algoritmo evolutivo durante config.generations iteraciones."""
        rng = random.Random(self.seed)
        objective = config.objective
        pop_size = len(config.population)
        maximize = objective.maximize

        current_pop: tuple[Individual, ...] = tuple(config.population)
        current_scores: tuple[float, ...] = tuple(objective.evaluate(ind) for ind in current_pop)

        generations: list[Generation] = [
            Generation(index=0, population=current_pop, scores=current_scores)
        ]

        for gen_idx in range(1, config.generations + 1):
            # 1. Identificar al mejor individuo actual (Elitismo)
            best_idx = (
                max(range(pop_size), key=lambda i: current_scores[i])
                if maximize
                else min(range(pop_size), key=lambda i: current_scores[i])
            )
            elite = current_pop[best_idx]

            # 2. Selección de padres
            parents = self._select_parents(
                current_pop, current_scores, config.selection, maximize, rng
            )

            # 3. Cruza y Mutación para generar la nueva población
            next_pop: list[Individual] = [elite]  # Conservamos al mejor individuo

            while len(next_pop) < pop_size:
                p1 = rng.choice(parents)
                p2 = rng.choice(parents)

                if rng.random() < config.crossover_rate:
                    child1, child2 = self._crossover(p1, p2, objective, rng)
                else:
                    child1, child2 = p1, p2

                child1 = self._mutate(child1, config.mutation_rate, objective, rng)
                next_pop.append(child1)

                if len(next_pop) < pop_size:
                    child2 = self._mutate(child2, config.mutation_rate, objective, rng)
                    next_pop.append(child2)

            current_pop = tuple(next_pop)
            current_scores = tuple(objective.evaluate(ind) for ind in current_pop)
            generations.append(
                Generation(index=gen_idx, population=current_pop, scores=current_scores)
            )

        return generations

    def _select_parents(
        self,
        population: tuple[Individual, ...],
        scores: tuple[float, ...],
        method: str,
        maximize: bool,
        rng: random.Random,
    ) -> list[Individual]:
        """Selecciona padres según el método configurado: torneo, ruleta o elitista."""
        n = len(population)

        if method == "elitista":
            order = sorted(
                range(n), key=lambda i: scores[i], reverse=maximize
            )
            top_k = max(2, n // 2)
            elite_pool = [population[i] for i in order[:top_k]]
            return [rng.choice(elite_pool) for _ in range(n)]

        if method == "ruleta":
            if maximize:
                min_s = min(scores)
                weights = [(s - min_s) + 1e-6 for s in scores]
            else:
                max_s = max(scores)
                weights = [(max_s - s) + 1e-6 for s in scores]
            return rng.choices(population, weights=weights, k=n)

        # Por defecto: Torneo binario/ternario
        k = min(3, n)
        selected: list[Individual] = []
        for _ in range(n):
            contenders = rng.sample(range(n), k)
            winner = (
                max(contenders, key=lambda i: scores[i])
                if maximize
                else min(contenders, key=lambda i: scores[i])
            )
            selected.append(population[winner])
        return selected

    def _crossover(
        self,
        p1: Individual,
        p2: Individual,
        objective: Objective,
        rng: random.Random,
    ) -> tuple[Individual, Individual]:
        """Cruza BLX-alfa acotada al dominio de cada variable."""
        c1, c2 = [], []
        alpha = 0.25
        for v1, v2, (low, high) in zip(p1, p2, objective.bounds):
            lo, hi = min(v1, v2), max(v1, v2)
            span = hi - lo
            ext_low = max(low, lo - alpha * span)
            ext_high = min(high, hi + alpha * span)
            c1.append(rng.uniform(ext_low, ext_high))
            c2.append(rng.uniform(ext_low, ext_high))
        return tuple(c1), tuple(c2)

    def _mutate(
        self,
        individual: Individual,
        mutation_rate: float,
        objective: Objective,
        rng: random.Random,
    ) -> Individual:
        """Mutación gaussiana por coordenada con recorte (clamping) a los límites."""
        mutated = []
        for val, (low, high) in zip(individual, objective.bounds):
            if rng.random() < mutation_rate:
                sigma = (high - low) * 0.1
                val = val + rng.gauss(0.0, sigma)
                val = max(low, min(high, val))
            mutated.append(val)
        return tuple(mutated)