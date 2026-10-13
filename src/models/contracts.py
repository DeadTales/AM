"""Contratos independientes de Flet para conectar cualquier motor genético."""
from dataclasses import dataclass
import math
from typing import Callable, Protocol

Individual = tuple[float, ...]


@dataclass(frozen=True)
class Objective:
    """Nombre, fórmula, etiquetas, dominio por coordenada y evaluación del vector."""
    name: str
    expression: str
    labels: tuple[str, ...]
    bounds: tuple[tuple[float, float], ...]
    evaluate: Callable[[Individual], float]

    @property
    def dimensions(self) -> int:
        """Número de coordenadas de cada individuo."""
        return len(self.labels)


@dataclass(frozen=True)
class AlgorithmConfig:
    """Entrada al motor: población, objetivo, probabilidad [0,1], selección e iteraciones."""
    population: tuple[Individual, ...]
    objective: Objective
    mutation_rate: float
    selection: str
    generations: int


@dataclass(frozen=True)
class Generation:
    """Salida: índice desde cero, población y una puntuación por individuo."""
    index: int
    population: tuple[Individual, ...]
    scores: tuple[float, ...]


class EvolutionEngine(Protocol):
    """Implementar run(config)"""

    def run(self, config: AlgorithmConfig) -> list[Generation]:
        """Devuelve generaciones 0..config.generations; 0 es la población inicial."""
        ...


def validate_population(population, objective: Objective) -> tuple[Individual, ...]:
    """Normaliza vectores y rechaza cantidad, dimensión, valores o dominios inválidos."""
    if not 2 <= len(population) <= 200:
        raise ValueError("La población debe contener entre 2 y 200 individuos.")
    result = []
    for index, individual in enumerate(population):
        if len(individual) != objective.dimensions:
            raise ValueError(f"El individuo {index+1} requiere {objective.dimensions} coordenadas.")
        try:
            values = tuple(float(value) for value in individual)
        except (TypeError, ValueError):
            raise ValueError(f"El individuo {index+1} contiene un valor no numérico.") from None
        for label, value, (lower, upper) in zip(objective.labels, values, objective.bounds):
            if not math.isfinite(value) or not lower <= value <= upper:
                raise ValueError(f"Individuo {index+1}: {label} debe estar entre {lower:g} y {upper:g}.")
        result.append(values)
    return tuple(result)


def validate_generations(generations: list[Generation], config: AlgorithmConfig) -> None:
    """Verifica salida del motor antes de mostrarla, incluida la generación inicial."""
    if len(generations) != config.generations+1:
        raise ValueError("El motor debe devolver la generación 0 y todas las iteraciones solicitadas.")
    for index, generation in enumerate(generations):
        if generation.index != index:
            raise ValueError("Los índices de generación deben ser consecutivos desde cero.")
        population = validate_population(generation.population, config.objective)
        if len(population) != len(config.population) or len(generation.scores) != len(population):
            raise ValueError("El motor debe conservar el tamaño de población y devolver una puntuación por individuo.")
        if any(not math.isfinite(score) for score in generation.scores):
            raise ValueError("El motor devolvió puntuaciones no finitas.")
    if generations[0].population != config.population:
        raise ValueError("La generación 0 debe contener la población inicial aplicada.")
