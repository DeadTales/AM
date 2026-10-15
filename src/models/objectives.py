"""Registro exclusivo de las 5 funciones asignadas para la actividad."""
import math
from models.contracts import Individual, Objective

FUNCTIONS = {
    "sine_1d": "2. Seno oscilante (1D)",
    "exp_1d": "4. Exponencial simple (1D)",
    "ackley": "8. Ackley (2D)",
    "eggholder": "10. Eggholder (2D)",
    "rosenbrock": "12. Rosenbrock (2D)",
}

FIXED_DIMENSIONS = {
    "sine_1d": 1,
    "exp_1d": 1,
    "ackley": 2,
    "eggholder": 2,
    "rosenbrock": 2,
}


def get_objective(key: str, dimensions: int | None = None) -> Objective:
    """Crea objetivo por clave con sus cotas, fórmula y dimensión fija."""
    if key not in FUNCTIONS:
        raise ValueError(f"Función no reconocida: {key}")

    dimensions = FIXED_DIMENSIONS[key]
    labels = ("x", "y")[:dimensions]

    domains = {
        "sine_1d": (0.0, 1.0),
        "exp_1d": (-3.0, 3.0),
        "ackley": (-5.0, 5.0),
        "eggholder": (-512.0, 512.0),
        "rosenbrock": (-2.0, 2.0),
    }

    expressions = {
        "sine_1d": "sin(10πx) + 1   [Maximización]",
        "exp_1d": "e^(−x²)   [Maximización]",
        "ackley": "−20 exp(−0.2√(0.5(x²+y²))) − exp(0.5(cos(2πx)+cos(2πy))) + 20 + e   [Minimización]",
        "eggholder": "−(y+47) sin(√|x/2+y+47|) − x sin(√|x−(y+47)|)   [Minimización]",
        "rosenbrock": "(1−x)² + 100(y−x²)²   [Minimización]",
    }

    maximize = key in ("sine_1d", "exp_1d")

    def evaluate(values: Individual) -> float:
        """Evalúa el vector de coordenadas según la función seleccionada."""
        if key == "sine_1d":
            x = values[0]
            return math.sin(10 * math.pi * x) + 1.0
        if key == "exp_1d":
            x = values[0]
            return math.exp(-(x * x))
        if key == "ackley":
            d = len(values)
            sum_sq = sum(v * v for v in values)
            sum_cos = sum(math.cos(2 * math.pi * v) for v in values)
            return -20.0 * math.exp(-0.2 * math.sqrt(sum_sq / d)) - math.exp(sum_cos / d) + 20.0 + math.e
        if key == "eggholder":
            x, y = values[0], values[1]
            term1 = -(y + 47.0) * math.sin(math.sqrt(abs(x / 2.0 + (y + 47.0))))
            term2 = -x * math.sin(math.sqrt(abs(x - (y + 47.0))))
            return term1 + term2
        if key == "rosenbrock":
            x, y = values[0], values[1]
            return (1.0 - x) ** 2 + 100.0 * ((y - x * x) ** 2)
        raise ValueError(f"Sin evaluador para: {key}")

    return Objective(
        name=FUNCTIONS[key],
        expression="f(" + ", ".join(labels) + ") = " + expressions[key],
        labels=labels,
        bounds=(domains[key],) * dimensions,
        evaluate=evaluate,
        maximize=maximize,
    )