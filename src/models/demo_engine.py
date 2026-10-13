"""Motor ilustrativo reemplazable; no implementa selección, cruce ni mutación."""
import itertools
import random
from models.contracts import AlgorithmConfig, Generation, Individual, Objective


def initial_population(size: int, objective: Objective) -> list[Individual]:
    """Genera size vectores reproducibles dentro de los límites de cada coordenada."""
    if not 2 <= size <= 200:
        raise ValueError("La cantidad para generar debe estar entre 2 y 200.")
    rng = random.Random(42)
    return [tuple(rng.uniform(lower, upper) for lower, upper in objective.bounds) for _ in range(size)]


class DemoEngine:
    """Implementación ilustrativa de EvolutionEngine que puedes reemplazar por tu motor."""

    def run(self, config: AlgorithmConfig) -> list[Generation]:
        """Interpola hacia un mínimo muestreado; selección y mutación no actúan."""
        objective = config.objective
        axes = [[lower+(upper-lower)*i/60 for i in range(61)] for lower, upper in objective.bounds]
        target = min(itertools.product(*axes), key=objective.evaluate)
        result = []
        for index in range(config.generations+1):
            progress = index/config.generations
            population = config.population if index == 0 else tuple(tuple(v+(t-v)*progress for v, t in zip(individual, target)) for individual in config.population)
            result.append(Generation(index, population, tuple(objective.evaluate(individual) for individual in population)))
        return result
