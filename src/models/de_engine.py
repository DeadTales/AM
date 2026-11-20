"""Motor de Evolución Diferencial (DE) para funciones continuas de 1 a n variables.

Sigue el mismo contrato que GeneticEngine y PSOEngine: recibe una configuración y
devuelve list[Generation] con la generación 0 (población inicial) y cada iteración.
DEConfig vive en este archivo para no modificar contracts.py (componente global).

Esquema por iteración, para cada individuo objetivo x_i:
    1. Mutación:     v = x_r1 + F · (x_r2 − x_r3)          (rand/1)
                     v = x_best + F · (x_r1 − x_r2)        (best/1)
    2. Cruza binomial: u_j = v_j si rand() < CR o j = j_rand; si no, u_j = x_i,j
    3. Selección voraz: u reemplaza a x_i si es igual o mejor (según max/min).
"""
from dataclasses import dataclass
import math
import random

from models.contracts import Generation, Individual, Objective, validate_population

STRATEGIES = ("rand/1/bin", "best/1/bin")


@dataclass(frozen=True)
class DEConfig:
    """Entrada DE: población inicial, objetivo, iteraciones, F, CR, estrategia y semilla."""
    population: tuple[Individual, ...]
    objective: Objective
    generations: int
    mutation_factor: float = 0.8   # F: escala del vector diferencia, en [0, 2]
    crossover_rate: float = 0.9    # CR: probabilidad de tomar la coordenada del mutante, en [0, 1]
    strategy: str = "rand/1/bin"
    seed: int = 42

    def validate(self) -> None:
        """Exige población válida (mín. 4), 1–500 iteraciones, F∈[0,2], CR∈[0,1], estrategia y semilla."""
        validate_population(self.population, self.objective)
        # rand/1 necesita el individuo objetivo y tres distintos a él.
        if len(self.population) < 4:
            raise ValueError("Evolución Diferencial requiere al menos 4 individuos.")
        if not isinstance(self.generations, int) or not 1 <= self.generations <= 500:
            raise ValueError("El número de generaciones debe ser un entero entre 1 y 500.")
        if not math.isfinite(self.mutation_factor) or not 0 <= self.mutation_factor <= 2:
            raise ValueError("F debe estar entre 0 y 2.")
        if not math.isfinite(self.crossover_rate) or not 0 <= self.crossover_rate <= 1:
            raise ValueError("CR debe estar entre 0 y 1.")
        if self.strategy not in STRATEGIES:
            raise ValueError(f"Estrategia no reconocida: {self.strategy}. Use {', '.join(STRATEGIES)}.")
        if not isinstance(self.seed, int) or not 0 <= self.seed <= 2**32-1:
            raise ValueError("La semilla debe ser un entero entre 0 y 4294967295.")


class DEEngine:
    """Implementa Evolución Diferencial (rand/1/bin o best/1/bin) mediante run(config)."""
    is_demo = False

    def run(self, config: DEConfig, should_stop=None, on_generation=None) -> list[Generation]:
        """Ejecuta DE durante config.generations iteraciones y devuelve el historial completo."""
        # 1. Validar parámetros antes de ejecutar.
        config.validate()
        self.stop_reason = f"Límite de generaciones alcanzado ({config.generations})."

        objective = config.objective
        maximize = objective.maximize
        rng = random.Random(config.seed)  # Misma semilla → misma ejecución.
        size = len(config.population)

        # 2. Estado inicial (generación 0): población aplicada y su evaluación.
        population: list[Individual] = [tuple(float(v) for v in ind) for ind in config.population]
        scores: list[float] = [objective.evaluate(ind) for ind in population]
        generations: list[Generation] = [
            Generation(index=0, population=tuple(population), scores=tuple(scores))
        ]

        # 3. Ciclo principal.
        if on_generation:
            on_generation(generations[0])
        for iteration in range(1, config.generations + 1):
            if should_stop and should_stop():
                self.stop_reason = f"Detenido por el usuario tras {iteration - 1} generaciones."
                break
            best_idx = self._best_index(scores, maximize)
            next_population = list(population)
            next_scores = list(scores)

            for i, target in enumerate(population):
                # 3a. Mutación: vector donante a partir de individuos distintos de i.
                mutant = self._mutate(i, population, best_idx, config, rng)
                # 3b. Cruza binomial entre el objetivo y el mutante.
                trial = self._crossover(target, mutant, config.crossover_rate, rng)
                # 3c. Reparar coordenadas fuera del dominio.
                trial = self._repair(trial, target, objective)
                # 3d. Selección voraz: el hijo entra si no es peor que el objetivo.
                trial_score = objective.evaluate(trial)
                if self._is_better_or_equal(trial_score, scores[i], maximize):
                    next_population[i] = trial
                    next_scores[i] = trial_score

            # La población se reemplaza al final de la iteración (versión síncrona clásica).
            population, scores = next_population, next_scores
            generations.append(
                Generation(index=iteration, population=tuple(population), scores=tuple(scores))
            )
            if on_generation:
                on_generation(generations[-1])

        return generations

    def _mutate(
        self,
        target_idx: int,
        population: list[Individual],
        best_idx: int,
        config: DEConfig,
        rng: random.Random,
    ) -> list[float]:
        """Construye el vector mutante v según la estrategia elegida."""
        candidates = [j for j in range(len(population)) if j != target_idx]
        r1, r2, r3 = rng.sample(candidates, 3)
        f = config.mutation_factor
        if config.strategy == "best/1/bin":
            base, a, b = population[best_idx], population[r1], population[r2]
        else:  # rand/1/bin
            base, a, b = population[r1], population[r2], population[r3]
        return [base[d] + f * (a[d] - b[d]) for d in range(len(base))]

    def _crossover(
        self, target: Individual, mutant: list[float], cr: float, rng: random.Random
    ) -> list[float]:
        """Cruza binomial; j_rand garantiza que al menos una coordenada venga del mutante."""
        dims = len(target)
        j_rand = rng.randrange(dims)
        return [
            mutant[d] if (rng.random() < cr or d == j_rand) else target[d]
            for d in range(dims)
        ]

    def _repair(self, trial: list[float], target: Individual, objective: Objective) -> Individual:
        """Si una coordenada sale del dominio, la coloca a la mitad entre el objetivo y el límite violado.

        Esto mantiene diversidad cerca de los bordes, a diferencia de recortar al límite,
        que acumula individuos justo en la frontera.
        """
        repaired = []
        for value, parent, (low, high) in zip(trial, target, objective.bounds):
            if value < low:
                value = (parent + low) / 2.0
            elif value > high:
                value = (parent + high) / 2.0
            repaired.append(min(high, max(low, value)))
        return tuple(repaired)

    @staticmethod
    def _is_better_or_equal(candidate: float, current: float, maximize: bool) -> bool:
        """Compara evaluaciones según el sentido de optimización."""
        return candidate >= current if maximize else candidate <= current

    @staticmethod
    def _best_index(scores: list[float], maximize: bool) -> int:
        """Índice del mejor individuo según max/min."""
        if maximize:
            return max(range(len(scores)), key=lambda i: scores[i])
        return min(range(len(scores)), key=lambda i: scores[i])
