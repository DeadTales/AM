"""Pruebas de la Persona 1: 15 funciones continuas y motor de Evolución Diferencial.

Ejecutar desde la raíz del proyecto:  python tools/check_de.py
Sólo usa src/models (no requiere Flet).
"""
from dataclasses import replace
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
from models.contracts import AlgorithmConfig, PSOConfig, validate_generations
from models.de_engine import DEConfig, DEEngine
from models.demo_engine import initial_population
from models.genetic_engine import GeneticEngine
from models.objectives import FIXED_DIMENSIONS, FUNCTIONS, VARIABLE_DIMENSIONS, get_objective
from models.pso_engine import PSOEngine

# Dominio y sentido esperados según el documento de funciones.
EXPECTED = {
    "parabola_1d": ((-3, 3), True), "sine_1d": ((0, 1), True), "linear_1d": ((0, 3), True),
    "exp_1d": ((-3, 3), True), "cosine_1d": ((-3, 3), True),
    "rastrigin": ((-5.12, 5.12), False), "himmelblau": ((-6, 6), False), "ackley": ((-5, 5), False),
    "schwefel": ((-500, 500), False), "eggholder": ((-512, 512), False), "griewank": ((-600, 600), False),
    "rosenbrock": ((-2, 2), False), "michalewicz": ((0, math.pi), False), "levy": ((-10, 10), False),
    "zakharov": ((-5, 10), False),
    "sphere": ((-5, 5), False),
}

# Óptimos conocidos (punto, valor) para comprobar que cada fórmula está bien escrita.
OPTIMA = {
    "parabola_1d": ((0,), 4.0), "sine_1d": ((0.05,), 2.0), "linear_1d": ((0,), 5.0),
    "exp_1d": ((0,), 1.0), "cosine_1d": ((0,), 3.0),
    "rastrigin": ((0, 0), 0.0), "himmelblau": ((3, 2), 0.0), "ackley": ((0, 0), 0.0),
    "schwefel": ((420.9687, 420.9687), 0.0), "eggholder": ((512, 404.2319), -959.6407),
    "griewank": ((0, 0), 0.0), "rosenbrock": ((1, 1), 0.0), "michalewicz": ((2.20, 1.57), -1.8013),
    "levy": ((1, 1), 0.0), "zakharov": ((0, 0), 0.0),
    "sphere": ((0, 0), 0.0),
}


def best(scores, maximize):
    return max(scores) if maximize else min(scores)


def check_registry():
    """Las 15 funciones originales y Sphere, con dominio, sentido y óptimo correctos."""
    assert len(FUNCTIONS) == 16
    assert [int(name.split(".")[0]) for name in FUNCTIONS.values()] == list(range(1, 17))
    assert set(FIXED_DIMENSIONS) | set(VARIABLE_DIMENSIONS) == set(FUNCTIONS)
    for key, (domain, maximize) in EXPECTED.items():
        objective = get_objective(key)
        assert all(b == domain for b in objective.bounds), key
        assert objective.maximize is maximize, key
        point, value = OPTIMA[key]
        assert abs(objective.evaluate(point) - value) < 1e-3, (key, objective.evaluate(point))
    print("✔ Registro: 16 funciones con dominio, sentido y óptimo correctos")


def check_dimensions():
    """Sphere, Schwefel y Griewank aceptan la dimensión elegida."""
    for key in VARIABLE_DIMENSIONS:
        for n in (1, 2, 3, 5, 10):
            objective = get_objective(key, n)
            assert objective.dimensions == n and len(objective.bounds) == n
            optimum = (420.9687,)*n if key == "schwefel" else (0.0,)*n
            assert abs(objective.evaluate(optimum)) < 1e-3*n, (key, n)
        for bad in (0, 11):
            try:
                get_objective(key, bad)
            except ValueError:
                pass
            else:
                raise AssertionError(f"{key} aceptó {bad} variables")
    assert get_objective("schwefel").dimensions == 2  # valor por defecto
    assert get_objective("ackley", 5).dimensions == 2  # fija: ignora el parámetro
    assert get_objective("griewank", 3).labels == ("x1", "x2", "x3")
    print("✔ Dimensión elegible en Sphere, Schwefel y Griewank (1–10)")


def check_all_algorithms():
    """Cada función se ejecuta con DE, GA y PSO, y el resultado pasa la validación de la interfaz."""
    cases = [(key, None) for key in FUNCTIONS] + [("schwefel", 5), ("griewank", 5)]
    print(f"\n{'Función':<28}{'Inicial':>12}{'DE':>12}{'GA':>12}{'PSO':>12}")
    for key, dims in cases:
        objective = get_objective(key, dims)
        population = tuple(initial_population(20, objective))
        iters = 60
        runs = {
            "DE": (DEEngine(), DEConfig(population, objective, iters, seed=1)),
            "GA": (GeneticEngine(seed=1), AlgorithmConfig(population, objective, 0.2, "torneo", iters)),
            "PSO": (PSOEngine(), PSOConfig(population, objective, iters, seed=1)),
        }
        start = best(tuple(objective.evaluate(p) for p in population), objective.maximize)
        results = {}
        for name, (engine, config) in runs.items():
            generations = engine.run(config)
            validate_generations(generations, config)
            results[name] = best(generations[-1].scores, objective.maximize)
        # DE y GA conservan al mejor, así que nunca empeoran respecto al inicio.
        for name in ("DE", "GA"):
            assert (results[name] >= start) if objective.maximize else (results[name] <= start), (key, name)
        label = objective.name + (f" n={dims}" if dims else "")
        print(f"{label:<28}{start:>12.5g}" + "".join(f"{results[n]:>12.5g}" for n in ("DE", "GA", "PSO")))
    print("✔ Las 16 funciones (y Schwefel/Griewank en 5D) corren con DE, GA y PSO")


def check_de_engine():
    """Reproducibilidad, monotonía, dominio, efecto de parámetros y validación."""
    engine = DEEngine()
    objective = get_objective("rastrigin")
    config = DEConfig(tuple(initial_population(20, objective)), objective, 40)
    generations = engine.run(config)
    assert generations == engine.run(config), "misma semilla debe dar mismo resultado"
    assert generations != engine.run(replace(config, seed=7))
    history = [min(g.scores) for g in generations]
    assert all(b <= a for a, b in zip(history, history[1:])), "el mejor nunca empeora"
    assert history[-1] < history[0]
    assert all(g.scores == tuple(objective.evaluate(p) for p in g.population) for g in generations)
    for changed in (replace(config, mutation_factor=0.3), replace(config, crossover_rate=0.2),
                    replace(config, strategy="best/1/bin")):
        assert engine.run(changed)[-1].population != generations[-1].population
    # best/1 converge en una función unimodal hasta casi el óptimo.
    sphere_like = get_objective("zakharov")
    result = engine.run(DEConfig(tuple(initial_population(20, sphere_like)), sphere_like, 150, strategy="best/1/bin"))
    assert min(result[-1].scores) < 1e-6
    # Configuraciones inválidas.
    small = tuple(initial_population(3, objective))
    for bad in (replace(config, population=small), replace(config, generations=0),
                replace(config, mutation_factor=2.5), replace(config, crossover_rate=-0.1),
                replace(config, strategy="otra"), replace(config, seed=-1)):
        try:
            engine.run(bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"configuración inválida aceptada: {bad}")
    print("✔ DE: reproducible, monótono, respeta dominio, sensible a F/CR/estrategia y valida entradas")


if __name__ == "__main__":
    check_registry()
    check_dimensions()
    check_de_engine()
    check_all_algorithms()
    print("\nTodas las pruebas de la Persona 1 pasaron.")
