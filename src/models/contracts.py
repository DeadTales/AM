"""Contratos independientes de Flet para conectar cualquier motor genético."""
from dataclasses import dataclass
import math
from typing import Callable

Individual = tuple[float, ...]


@dataclass(frozen=True)
class Objective:
    """Nombre, fórmula, etiquetas, dominio por coordenada y evaluación del vector."""
    name: str
    expression: str
    labels: tuple[str, ...]
    bounds: tuple[tuple[float, float], ...]
    evaluate: Callable[[Individual], float]
    maximize: bool = False

    @property
    def dimensions(self) -> int:
        """Número de coordenadas de cada individuo."""
        return len(self.labels)


@dataclass(frozen=True)
class AlgorithmConfig:
    """Entrada al motor: población, objetivo, probabilidades [0,1], selección e iteraciones."""
    population: tuple[Individual, ...]
    objective: Objective
    mutation_rate: float
    selection: str
    generations: int
    crossover_rate: float = 0.8
    seed: int | None = None

    def validate(self) -> None:
        validate_population(self.population, self.objective)
        if type(self.generations) is not int or not 1 <= self.generations <= 500:
            raise ValueError("El número de generaciones debe ser un entero entre 1 y 500.")
        for label, value in (("Tasa de cruza", self.crossover_rate), ("Tasa de mutación", self.mutation_rate)):
            if not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f"{label} debe estar entre 0 y 1.")
        if self.selection not in ("torneo", "ruleta", "elitista"):
            raise ValueError("Selecciona un método de selección válido.")
        if self.seed is not None and (type(self.seed) is not int or not 0 <= self.seed <= 2**32-1):
            raise ValueError("La semilla debe ser un entero entre 0 y 4294967295.")


@dataclass(frozen=True)
class Generation:
    """Salida: índice desde cero, población y una puntuación por individuo."""
    index: int
    population: tuple[Individual, ...]
    scores: tuple[float, ...]


@dataclass(frozen=True)
class PSOConfig:
    """Entrada PSO sin parámetros genéticos; generations representa iteraciones de movimiento."""
    population: tuple[Individual, ...]
    objective: Objective
    generations: int
    inertia: float = 0.7
    cognitive: float = 1.5
    social: float = 1.5
    seed: int = 42
    velocity_limit: float = 0.2

    def validate(self) -> None:
        """Exige posiciones válidas, 1–500 iteraciones y coeficientes finitos en rangos de la UI."""
        validate_population(self.population, self.objective)
        if not isinstance(self.generations, int) or not 1 <= self.generations <= 500:
            raise ValueError("Las iteraciones deben ser enteros entre 1 y 500.")
        for label, value, upper in (("w", self.inertia, 2), ("c1", self.cognitive, 4), ("c2", self.social, 4)):
            if not math.isfinite(value) or not 0 <= value <= upper:
                raise ValueError(f"{label} debe estar entre 0 y {upper}.")
        if not isinstance(self.seed, int) or not 0 <= self.seed <= 2**32-1:
            raise ValueError("La semilla debe ser un entero entre 0 y 4294967295.")
        if not math.isfinite(self.velocity_limit) or not 0 < self.velocity_limit <= 1:
            raise ValueError("El límite de velocidad debe ser mayor que 0 y hasta el 100 % del intervalo.")

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


def validate_generations(generations: list[Generation], config: AlgorithmConfig | PSOConfig, *, allow_partial=False) -> None:
    """Verifica salida del motor antes de mostrarla, incluida la generación inicial."""
    if not (1 <= len(generations) <= config.generations+1 if allow_partial else len(generations) == config.generations+1):
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


@dataclass(frozen=True)
class ACOParameter:
    """Descripción de un parámetro ACO para la interfaz: etiqueta, explicación, tipo, rango y valor inicial."""
    label: str
    help: str
    kind: type
    minimum: float
    maximum: float
    default: float


# Etiquetas, explicaciones y rangos de cada campo de ACOConfig (la interfaz puede leerlos de aquí).
ACO_PARAMETERS: dict[str, ACOParameter] = {
    "ants": ACOParameter("Número de hormigas", "Soluciones que se construyen en cada iteración.", int, 2, 200, 20),
    "generations": ACOParameter("Número de iteraciones", "Máximo de iteraciones de la colonia.", int, 1, 500, 100),
    "initial_pheromone": ACOParameter("Feromona inicial (τ0)", "Feromona con la que empiezan todas las opciones. 0 = automática (hormigas·Q / costo de una solución voraz).", float, 0, 1000, 0.0),
    "alpha": ACOParameter("Influencia de feromona (α)", "Exponente de τ: valores altos siguen más lo aprendido por la colonia.", float, 0, 10, 1.0),
    "beta": ACOParameter("Influencia heurística (β)", "Exponente de η = 1/distancia o 1/costo: valores altos prefieren la opción más barata inmediata.", float, 0, 10, 3.0),
    "rho": ACOParameter("Evaporación (ρ)", "Fracción de feromona que se pierde en cada iteración; evita quedarse con rutas viejas.", float, 0.01, 0.99, 0.3),
    "q": ACOParameter("Depósito (Q)", "Cantidad de feromona que deposita una hormiga: Q / costo de su solución.", float, 0.01, 1000, 1.0),
    "patience": ACOParameter("Paciencia de convergencia", "Detiene antes si el mejor costo no mejora en este número de iteraciones seguidas. 0 = desactivada.", int, 0, 500, 0),
    "seed": ACOParameter("Semilla", "Fija la aleatoriedad para repetir exactamente la misma ejecución.", int, 0, 2**32-1, 42),
}


@dataclass(frozen=True)
class ACOConfig:
    """Entrada ACO para problemas categóricos (TSP o asignación de models/categorical.py).

    generations son las iteraciones de la colonia; ants el número de hormigas por iteración.
    alpha pondera la feromona τ, beta la heurística η, rho es la evaporación y q la cantidad depositada.
    initial_pheromone es τ0 (0 = automática) y patience activa la convergencia anticipada (0 = desactivada).
    Las etiquetas y explicaciones de cada campo están en ACO_PARAMETERS.
    """
    problem: object
    ants: int = 20
    generations: int = 100
    alpha: float = 1.0
    beta: float = 3.0
    rho: float = 0.3
    q: float = 1.0
    seed: int = 42
    initial_pheromone: float = 0.0
    patience: int = 0

    def validate(self) -> None:
        """Valida el problema y que cada parámetro tenga el tipo y rango de ACO_PARAMETERS."""
        self.problem.validate()
        for name, spec in ACO_PARAMETERS.items():
            value = getattr(self, name)
            if spec.kind is int:
                valid_type = isinstance(value, int) and not isinstance(value, bool)
            else:
                valid_type = isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
            if not valid_type or not spec.minimum <= value <= spec.maximum:
                kind = "un entero" if spec.kind is int else "un número"
                raise ValueError(f"{spec.label} debe ser {kind} entre {spec.minimum:g} y {spec.maximum:g}.")


def validate_aco_generations(generations: list[Generation], config: ACOConfig) -> None:
    """Verifica la salida ACO: pasos 0..k (k ≤ N si hubo convergencia o detención), una solución y su evaluación por hormiga."""
    if not 1 <= len(generations) <= config.generations+1:
        raise ValueError("El motor debe devolver la iteración 0 y como máximo todas las iteraciones solicitadas.")
    problem = config.problem
    for index, generation in enumerate(generations):
        if generation.index != index:
            raise ValueError("Los índices de iteración deben ser consecutivos desde cero.")
        if len(generation.population) != config.ants or len(generation.scores) != config.ants:
            raise ValueError("Cada iteración debe contener una solución y una evaluación por hormiga.")
        for solution, score in zip(generation.population, generation.scores):
            if not math.isfinite(score) or abs(problem.evaluate(solution)-score) > 1e-6:
                raise ValueError("Una evaluación no coincide con la solución reportada.")
