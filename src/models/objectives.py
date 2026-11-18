"""Registro de las 15 funciones de prueba del documento "Funciones de Prueba para Algoritmos Evolutivos".

Funciones simples (1–5): 1D y de maximización.
Funciones complejas (6–15): 2D (Schwefel y Griewank en nD) y de minimización.
Cada función define nombre, fórmula, dominio por coordenada y evaluador.
"""
import math
from models.contracts import Individual, Objective

FUNCTIONS = {
    "parabola_1d": "1. Parabólica simple (1D)",
    "sine_1d": "2. Seno oscilante (1D)",
    "linear_1d": "3. Lineal con pendiente (1D)",
    "exp_1d": "4. Exponencial simple (1D)",
    "cosine_1d": "5. Coseno desplazado (1D)",
    "rastrigin": "6. Rastrigin (2D)",
    "himmelblau": "7. Himmelblau (2D)",
    "ackley": "8. Ackley (2D)",
    "schwefel": "9. Schwefel (nD)",
    "eggholder": "10. Eggholder (2D)",
    "griewank": "11. Griewank (nD)",
    "rosenbrock": "12. Rosenbrock (2D)",
    "michalewicz": "13. Michalewicz (2D)",
    "levy": "14. Lévy (2D)",
    "zakharov": "15. Zakharov (2D)",
}

# Funciones con dimensión fija. Las que no aparecen aquí (Schwefel y Griewank)
# permiten elegir la dimensión; la interfaz desbloquea el selector para ellas.
FIXED_DIMENSIONS = {
    "parabola_1d": 1,
    "sine_1d": 1,
    "linear_1d": 1,
    "exp_1d": 1,
    "cosine_1d": 1,
    "rastrigin": 2,
    "himmelblau": 2,
    "ackley": 2,
    "eggholder": 2,
    "rosenbrock": 2,
    "michalewicz": 2,
    "levy": 2,
    "zakharov": 2,
}

# Funciones nD: rango permitido (mínimo, máximo) de variables y valor por defecto.
# Las gráficas actuales dibujan 1D y 2D; dimensiones mayores se pueden ejecutar
# en los motores, pero la interfaz necesitará opciones adicionales para elegirlas.
VARIABLE_DIMENSIONS = {
    "schwefel": (1, 10),
    "griewank": (1, 10),
}
DEFAULT_DIMENSIONS = 2

# Parámetro m de Michalewicz. El documento no fija su valor; se usa el estándar m = 10.
MICHALEWICZ_M = 10


def get_objective(key: str, dimensions: int | None = None) -> Objective:
    """Crea objetivo por clave con sus cotas, fórmula y dimensión.

    Para funciones de dimensión fija se ignora `dimensions`. Para Schwefel y Griewank
    se usa `dimensions` (por defecto 2) dentro del rango de VARIABLE_DIMENSIONS.
    """
    if key not in FUNCTIONS:
        raise ValueError(f"Función no reconocida: {key}")

    if key in FIXED_DIMENSIONS:
        dimensions = FIXED_DIMENSIONS[key]
    else:
        low_dim, high_dim = VARIABLE_DIMENSIONS[key]
        dimensions = DEFAULT_DIMENSIONS if dimensions is None else dimensions
        if not isinstance(dimensions, int) or not low_dim <= dimensions <= high_dim:
            raise ValueError(f"{FUNCTIONS[key]} admite entre {low_dim} y {high_dim} variables.")

    # Etiquetas x, y para 1D/2D (como usa la interfaz); x1..xn para más dimensiones.
    labels = ("x", "y")[:dimensions] if dimensions <= 2 else tuple(f"x{i+1}" for i in range(dimensions))

    # Dominio por coordenada, tomado del documento (el mismo para todas las coordenadas).
    domains = {
        "parabola_1d": (-3.0, 3.0),
        "sine_1d": (0.0, 1.0),
        "linear_1d": (0.0, 3.0),
        "exp_1d": (-3.0, 3.0),
        "cosine_1d": (-3.0, 3.0),
        "rastrigin": (-5.12, 5.12),
        "himmelblau": (-6.0, 6.0),
        "ackley": (-5.0, 5.0),
        "schwefel": (-500.0, 500.0),
        "eggholder": (-512.0, 512.0),
        "griewank": (-600.0, 600.0),
        "rosenbrock": (-2.0, 2.0),
        "michalewicz": (0.0, math.pi),
        "levy": (-10.0, 10.0),
        "zakharov": (-5.0, 10.0),
    }

    expressions = {
        "parabola_1d": "−x² + 4   [Maximización]",
        "sine_1d": "sin(10πx) + 1   [Maximización]",
        "linear_1d": "−2x + 5   [Maximización]",
        "exp_1d": "e^(−x²)   [Maximización]",
        "cosine_1d": "cos(5x) + 2   [Maximización]",
        "rastrigin": "20 + (x² − 10cos(2πx)) + (y² − 10cos(2πy))   [Minimización]",
        "himmelblau": "(x² + y − 11)² + (x + y² − 7)²   [Minimización]",
        "ackley": "−20 exp(−0.2√(0.5(x²+y²))) − exp(0.5(cos(2πx)+cos(2πy))) + 20 + e   [Minimización]",
        "schwefel": f"418.9829·{dimensions} − Σ xᵢ sin(√|xᵢ|)   [Minimización]",
        "eggholder": "−(y+47) sin(√|x/2+y+47|) − x sin(√|x−(y+47)|)   [Minimización]",
        "griewank": "1 + (1/4000) Σ xᵢ² − Π cos(xᵢ/√i)   [Minimización]",
        "rosenbrock": "(1−x)² + 100(y−x²)²   [Minimización]",
        "michalewicz": f"−(sin(x)·sin(x²/π)^(2m) + sin(y)·sin(2y²/π)^(2m)), m = {MICHALEWICZ_M}   [Minimización]",
        "levy": "sin²(πw₁) + (w₁−1)²(1+10sin²(πw₁+1)) + (w₂−1)²(1+sin²(2πw₂)), wᵢ = 1+(xᵢ−1)/4   [Minimización]",
        "zakharov": "x² + y² + (0.5x+0.5y)² + (0.5x+0.5y)⁴   [Minimización]",
    }

    # Las 5 funciones simples (1D) son de maximización; las 10 complejas, de minimización.
    maximize = key in ("parabola_1d", "sine_1d", "linear_1d", "exp_1d", "cosine_1d")

    def evaluate(values: Individual) -> float:
        """Evalúa el vector de coordenadas según la función seleccionada."""
        # ---------- Funciones simples (1D, maximización) ----------
        if key == "parabola_1d":
            # Máximo global f = 4 en x = 0.
            x = values[0]
            return -(x * x) + 4.0
        if key == "sine_1d":
            x = values[0]
            return math.sin(10 * math.pi * x) + 1.0
        if key == "linear_1d":
            # Monótona decreciente: máximo f = 5 en el extremo x = 0.
            x = values[0]
            return -2.0 * x + 5.0
        if key == "exp_1d":
            x = values[0]
            return math.exp(-(x * x))
        if key == "cosine_1d":
            # Máximos f = 3 donde cos(5x) = 1 (x = 0, ±2π/5, ...).
            x = values[0]
            return math.cos(5.0 * x) + 2.0

        # ---------- Funciones complejas (minimización) ----------
        if key == "rastrigin":
            # Mínimo global f = 0 en (0, 0).
            x, y = values[0], values[1]
            return (20.0 + (x * x - 10.0 * math.cos(2 * math.pi * x))
                    + (y * y - 10.0 * math.cos(2 * math.pi * y)))
        if key == "himmelblau":
            # Cuatro mínimos globales con f = 0, por ejemplo (3, 2).
            x, y = values[0], values[1]
            return (x * x + y - 11.0) ** 2 + (x + y * y - 7.0) ** 2
        if key == "ackley":
            d = len(values)
            sum_sq = sum(v * v for v in values)
            sum_cos = sum(math.cos(2 * math.pi * v) for v in values)
            return -20.0 * math.exp(-0.2 * math.sqrt(sum_sq / d)) - math.exp(sum_cos / d) + 20.0 + math.e
        if key == "schwefel":
            # nD. Mínimo global f ≈ 0 en xᵢ ≈ 420.9687 (cerca del borde del dominio).
            n = len(values)
            return 418.9829 * n - sum(v * math.sin(math.sqrt(abs(v))) for v in values)
        if key == "eggholder":
            x, y = values[0], values[1]
            term1 = -(y + 47.0) * math.sin(math.sqrt(abs(x / 2.0 + (y + 47.0))))
            term2 = -x * math.sin(math.sqrt(abs(x - (y + 47.0))))
            return term1 + term2
        if key == "griewank":
            # nD. Mínimo global f = 0 en el origen. El índice i empieza en 1.
            sum_sq = sum(v * v for v in values) / 4000.0
            prod_cos = math.prod(math.cos(v / math.sqrt(i)) for i, v in enumerate(values, start=1))
            return 1.0 + sum_sq - prod_cos
        if key == "rosenbrock":
            x, y = values[0], values[1]
            return (1.0 - x) ** 2 + 100.0 * ((y - x * x) ** 2)
        if key == "michalewicz":
            # Mínimo global f ≈ −1.8013 en (2.20, 1.57) con m = 10.
            x, y = values[0], values[1]
            two_m = 2 * MICHALEWICZ_M
            return -(math.sin(x) * math.sin(x * x / math.pi) ** two_m
                     + math.sin(y) * math.sin(2.0 * y * y / math.pi) ** two_m)
        if key == "levy":
            # Mínimo global f = 0 en (1, 1). wᵢ = 1 + (xᵢ − 1)/4 (definición estándar,
            # el documento usa wᵢ sin definirlo). La sumatoria va de i = 1 a n − 1.
            w = [1.0 + (v - 1.0) / 4.0 for v in values]
            first = math.sin(math.pi * w[0]) ** 2
            middle = sum((wi - 1.0) ** 2 * (1.0 + 10.0 * math.sin(math.pi * wi + 1.0) ** 2) for wi in w[:-1])
            last = (w[-1] - 1.0) ** 2 * (1.0 + math.sin(2.0 * math.pi * w[-1]) ** 2)
            return first + middle + last
        if key == "zakharov":
            # Mínimo global f = 0 en el origen. Se sigue la fórmula del documento,
            # (0.5x + 0.5y); la versión estándar usa Σ 0.5·i·xᵢ = 0.5x + 1.0y.
            # Nota: el documento la llama multimodal, pero tiene un único mínimo.
            x, y = values[0], values[1]
            s = 0.5 * x + 0.5 * y
            return x * x + y * y + s ** 2 + s ** 4
        raise ValueError(f"Sin evaluador para: {key}")

    return Objective(
        name=FUNCTIONS[key],
        expression="f(" + ", ".join(labels) + ") = " + expressions[key],
        labels=labels,
        bounds=(domains[key],) * dimensions,
        evaluate=evaluate,
        maximize=maximize,
    )
