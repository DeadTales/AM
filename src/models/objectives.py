"""Registro de cinco funciones provisionales de una o dos variables."""
import math
from models.contracts import Individual, Objective

FUNCTIONS = {"sphere": "Esfera", "rastrigin": "Rastrigin", "ackley": "Ackley", "quartic": "Cuártica", "wave": "Ondulada"}


def get_objective(key: str, dimensions: int) -> Objective:
    """Crea objetivo por clave y número de variables, etiquetadas x e y."""
    if dimensions not in (1, 2):
        raise ValueError("Las funciones de ejemplo admiten una o dos variables.")
    labels = ("x", "y")[:dimensions]
    domains = {"sphere": (-5, 5), "rastrigin": (-5.12, 5.12), "ackley": (-5, 5), "quartic": (-2, 4), "wave": (-6, 6)}
    expressions = {"sphere": "Σ vᵢ²", "rastrigin": "10d + Σ [vᵢ² − 10 cos(2πvᵢ)]", "ackley": "−20 exp(−0.2 √media(vᵢ²)) − exp(media(cos(2πvᵢ))) + 20 + e", "quartic": "Σ [vᵢ⁴ − 3vᵢ³ + 2]", "wave": "Σ [sin(3vᵢ) + 0.1vᵢ²]"}

    def evaluate(values: Individual) -> float:
        """Evalúa el vector completo; todos los ejemplos se minimizan."""
        if key == "sphere":
            return sum(v*v for v in values)
        if key == "rastrigin":
            return 10*dimensions+sum(v*v-10*math.cos(2*math.pi*v) for v in values)
        if key == "ackley":
            return -20*math.exp(-0.2*math.sqrt(sum(v*v for v in values)/dimensions))-math.exp(sum(math.cos(2*math.pi*v) for v in values)/dimensions)+20+math.e
        if key == "quartic":
            return sum(v**4-3*v**3+2 for v in values)
        return sum(math.sin(3*v)+0.1*v*v for v in values)

    return Objective(FUNCTIONS[key], "f("+", ".join(labels)+") = "+expressions[key], labels, (domains[key],)*dimensions, evaluate)
