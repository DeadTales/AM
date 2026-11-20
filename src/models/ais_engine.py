"""Motor de selección clonal para OneMax y Mochila 0/1, independiente de Flet."""
from dataclasses import dataclass
import math
from random import Random
from models.contracts import Generation

from models.ais_problems import BitVector, Knapsack, OneMax


@dataclass(frozen=True)
class AISConfig:
    """Tamaño de población, número de ciclos, máximo de clones por seleccionado y semilla."""

    population_size: int = 32
    iterations: int = 40
    max_clones: int = 8
    seed: int | None = 4
    cloning_rate: float = 1.0
    mutation_rate: float | None = None
    selection_fraction: float = 0.25
    diversity_fraction: float = 0.1

    def __post_init__(self) -> None:
        for name, value, minimum in (
            ("Número de anticuerpos", self.population_size, 2),
            ("Número de iteraciones", self.iterations, 1),
            ("Máximo de clones por anticuerpo", self.max_clones, 1),
        ):
            if type(value) is not int or value < minimum:
                raise ValueError(f"{name} debe ser un entero mayor o igual a {minimum}.")
        if self.seed is not None and type(self.seed) is not int:
            raise ValueError("La semilla debe ser un entero o None.")
        for label, value in (("Tasa de clonación", self.cloning_rate),
                             ("Selección clonal", self.selection_fraction),
                             ("Fracción de renovación", self.diversity_fraction)):
            if not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f"{label} debe estar entre 0 y 1.")
        if self.selection_fraction == 0 or self.diversity_fraction == 1:
            raise ValueError("Selecciona una fracción clonal mayor que 0 y una renovación menor que 1.")
        if self.mutation_rate is not None and (not math.isfinite(self.mutation_rate) or not 0 <= self.mutation_rate <= 1):
            raise ValueError("La tasa de mutación debe estar entre 0 y 1, o vacía para usar 1/longitud.")


@dataclass(frozen=True)
class AISResult:
    """Mejor vector, valor total e historial acumulado desde la población inicial."""

    vector: BitVector
    value: int
    history: tuple[int, ...]
    weight: int | None = None
    generations: tuple[Generation, ...] = ()
    stop_reason: str = ""


class AISEngine:
    """Selecciona candidatos por afinidad, clona, hipermuta y conserva los mejores."""

    def run(self, problem: OneMax | Knapsack, config: AISConfig = AISConfig(), should_stop=None, on_generation=None) -> AISResult:
        """Maximiza el valor objetivo y devuelve el mejor candidato evaluado."""
        rng = Random(config.seed)

        def evaluate_candidate(vector: BitVector) -> tuple[int, BitVector]:
            # Inicialización, clones y reemplazos pasan por la misma regla de capacidad.
            if isinstance(problem, Knapsack):
                vector = problem.repair(vector, rng)
            return problem.evaluate(vector), vector

        def random_candidate() -> tuple[int, BitVector]:
            vector = tuple(rng.getrandbits(1) for _ in range(problem.length))
            return evaluate_candidate(vector)

        def affinity(candidate: tuple[int, BitVector]) -> int:
            return candidate[0]

        population = [random_candidate() for _ in range(config.population_size)]
        population.sort(key=affinity, reverse=True)
        history = [population[0][0]]
        selected_count = max(1, int(config.population_size * config.selection_fraction))
        newcomers = min(config.population_size - 1, max(1, int(config.population_size * config.diversity_fraction))) if config.diversity_fraction else 0
        mutation_base = 1 / problem.length if config.mutation_rate is None else config.mutation_rate
        generations = [Generation(0, tuple(vector for _, vector in population), tuple(value for value, _ in population))]
        self.stop_reason = f"Límite de iteraciones alcanzado ({config.iterations})."
        if on_generation:
            on_generation(generations[0])

        for iteration in range(1, config.iterations + 1):
            if should_stop and should_stop():
                self.stop_reason = f"Detenido por el usuario tras {iteration - 1} iteraciones."
                break
            best_value, worst_value = population[0][0], population[-1][0]
            span = best_value - worst_value
            clones = []
            for rank, (value, vector) in enumerate(population[:selected_count], start=1):
                # Los candidatos de mayor rango producen más clones. La tasa por bit
                # disminuye con la afinidad para hacer ajustes más pequeños cerca del mejor.
                clone_count = max(1, int(config.max_clones * config.cloning_rate) // rank) if config.cloning_rate else 0
                relative_affinity = (value - worst_value) / span if span else 1.0
                mutation_rate = min(1.0, mutation_base * (1 + 3 * (1 - relative_affinity)))
                for _ in range(clone_count):
                    clone = tuple(1 - bit if rng.random() < mutation_rate else bit for bit in vector)
                    clones.append(evaluate_candidate(clone))

            # Reservar espacio para candidatos nuevos mantiene diversidad y preserva al mejor.
            survivors = config.population_size - newcomers
            candidates = sorted(population + clones, key=affinity, reverse=True)
            population = candidates[:survivors]
            population.extend(random_candidate() for _ in range(newcomers))
            population.sort(key=affinity, reverse=True)
            history.append(population[0][0])
            generations.append(Generation(iteration, tuple(vector for _, vector in population), tuple(value for value, _ in population)))
            if on_generation:
                on_generation(generations[-1])

        value, vector = population[0]
        weight = problem.weight(vector) if isinstance(problem, Knapsack) else None
        return AISResult(vector, value, tuple(history), weight, tuple(generations), self.stop_reason)
