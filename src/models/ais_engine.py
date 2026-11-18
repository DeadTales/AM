"""Motor de selección clonal para OneMax y Mochila 0/1, independiente de Flet."""
from dataclasses import dataclass
from random import Random

from models.ais_problems import BitVector, Knapsack, OneMax


@dataclass(frozen=True)
class AISConfig:
    """Tamaño de población, número de ciclos, máximo de clones por seleccionado y semilla."""

    population_size: int = 32
    iterations: int = 40
    max_clones: int = 8
    seed: int | None = 4

    def __post_init__(self) -> None:
        for name, value, minimum in (
            ("population_size", self.population_size, 2),
            ("iterations", self.iterations, 1),
            ("max_clones", self.max_clones, 1),
        ):
            if type(value) is not int or value < minimum:
                raise ValueError(f"{name} debe ser un entero mayor o igual a {minimum}.")
        if self.seed is not None and type(self.seed) is not int:
            raise ValueError("La semilla debe ser un entero o None.")


@dataclass(frozen=True)
class AISResult:
    """Mejor vector, valor total e historial acumulado desde la población inicial."""

    vector: BitVector
    value: int
    history: tuple[int, ...]
    weight: int | None = None


class AISEngine:
    """Selecciona candidatos por afinidad, clona, hipermuta y conserva los mejores."""

    def run(self, problem: OneMax | Knapsack, config: AISConfig = AISConfig()) -> AISResult:
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
        selected_count = max(1, config.population_size // 4)
        newcomers = max(1, config.population_size // 10)

        for _ in range(config.iterations):
            best_value, worst_value = population[0][0], population[-1][0]
            span = best_value - worst_value
            clones = []
            for rank, (value, vector) in enumerate(population[:selected_count], start=1):
                # Los candidatos de mayor rango producen más clones. La tasa por bit
                # disminuye con la afinidad para hacer ajustes más pequeños cerca del mejor.
                clone_count = max(1, config.max_clones // rank)
                relative_affinity = (value - worst_value) / span if span else 1.0
                mutation_rate = min(1.0, (1 + 3 * (1 - relative_affinity)) / problem.length)
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

        value, vector = population[0]
        weight = problem.weight(vector) if isinstance(problem, Knapsack) else None
        return AISResult(vector, value, tuple(history), weight)
