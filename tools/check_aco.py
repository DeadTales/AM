"""Ejemplos y pruebas del motor ACO (persona 3): TSP y asignación de tareas a recursos.

Uso:  python tools/check_aco.py            (pruebas + resumen del historial)
      python tools/check_aco.py --completo (imprime el historial de todas las iteraciones)

Cada ejemplo muestra la configuración, la mejor solución, su costo y el historial por
iteración. Además compara contra el óptimo exacto (Held-Karp para TSP y fuerza bruta para
la asignación) y verifica restricciones, semilla, datos editados y validaciones.
"""
from dataclasses import replace
from itertools import product
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
# Imprime en UTF-8 aunque la salida sea cp1252 (panel de salida de VS Code / Windows)
sys.stdout.reconfigure(encoding="utf-8")
from models.aco_engine import ACOEngine, best_history, best_solution
from models.categorical import AssignmentProblem, TSPProblem, default_assignment, default_tsp
from models.contracts import ACO_PARAMETERS, ACOConfig, validate_aco_generations

FULL = "--completo" in sys.argv


def tsp_optimum(problem: TSPProblem) -> float:
    """Distancia óptima exacta por programación dinámica de Held-Karp (O(n²·2ⁿ))."""
    n, start = problem.size, problem.start
    others = [c for c in range(n) if c != start]
    best = {(1 << k, k): problem.distance(start, c) for k, c in enumerate(others)}
    for mask in range(1, 1 << len(others)):
        for last in range(len(others)):
            if (mask, last) not in best:
                continue
            for nxt in range(len(others)):
                if mask & (1 << nxt):
                    continue
                key = (mask | (1 << nxt), nxt)
                value = best[(mask, last)] + problem.distance(others[last], others[nxt])
                if value < best.get(key, float("inf")):
                    best[key] = value
    full = (1 << len(others)) - 1
    return min(best[(full, k)] + problem.distance(c, start) for k, c in enumerate(others))


def assignment_optimum(problem: AssignmentProblem) -> tuple[tuple[int, ...], float]:
    """Mejor asignación factible por fuerza bruta (solo para instancias pequeñas)."""
    feasible = (a for a in product(range(problem.resources), repeat=problem.size) if problem.is_feasible(a))
    best = min(feasible, key=problem.total_cost)
    return best, problem.total_cost(best)


def print_report(title: str, config: ACOConfig, engine: ACOEngine, generations) -> None:
    """Configuración, mejor solución, costo e historial por iteración."""
    problem = config.problem
    solution, score, found_at = best_solution(generations)
    history = best_history(generations)
    print(f"\n{'='*72}\n{title}\n{'='*72}")
    print(f"Problema: {problem.name}   |   {problem.expression}")
    print(f"Configuración: hormigas={config.ants}, iteraciones={config.generations}, α={config.alpha}, "
          f"β={config.beta}, ρ={config.rho}, Q={config.q}, τ0={config.initial_pheromone or 'automática'}, "
          f"paciencia={config.patience or 'desactivada'}, semilla={config.seed}")
    print(f"Mejor solución (vector): {solution}")
    print(f"Mejor solución (legible): {problem.describe(solution)}")
    print(f"Costo: {score:.4f}   (encontrada en la iteración {found_at})")
    print(f"Motivo de término: {engine.stop_reason}")
    print("Historial (iteración: mejor de la iteración | mejor acumulado | promedio):")
    n = len(generations) - 1
    checkpoints = {0, n // 3, 2 * n // 3, n}  # inicio, un tercio, dos tercios y final
    for generation, accumulated in zip(generations, history):
        if FULL or generation.index in checkpoints or generation.index % 10 == 0:
            mean = sum(generation.scores) / len(generation.scores)
            mark = "  ◄" if generation.index in checkpoints else ""
            print(f"  {generation.index:>4}: {min(generation.scores):10.4f} | {accumulated:10.4f} | {mean:10.4f}{mark}")
    if not FULL:
        print("  (usa --completo para ver todas las iteraciones; ◄ = inicio, 1/3, 2/3 y final)")


def check_tsp() -> None:
    """Ejemplo TSP: ruta válida, regreso al inicio, distancia correcta y cercana al óptimo."""
    problem = default_tsp()
    config = ACOConfig(problem, ants=20, generations=60, alpha=1.0, beta=3.0, rho=0.3, q=1.0, seed=42)
    engine = ACOEngine()
    generations = engine.run(config)
    validate_aco_generations(generations, config)
    print_report("Ejemplo 1 · ACO sobre TSP (10 ciudades)", config, engine, generations)

    route, score, _ = best_solution(generations)
    problem.check_route(route)  # cada ciudad exactamente una vez y empieza en el inicio
    closed = problem.closed_route(route)
    assert closed[0] == closed[-1] == problem.start, "La ruta no regresa al inicio"
    manual = sum(problem.distance(a, b) for a, b in zip(closed, closed[1:]))
    assert abs(manual - score) < 1e-9, "La distancia total no coincide"
    optimum = tsp_optimum(problem)
    print(f"Óptimo exacto (Held-Karp): {optimum:.4f}   brecha: {100*(score/optimum-1):.2f} %")
    assert score <= optimum * 1.05, "ACO quedó a más de 5 % del óptimo"
    history = best_history(generations)
    assert all(b <= a for a, b in zip(history, history[1:])), "El mejor acumulado debe ser no creciente"
    assert generations == ACOEngine().run(config), "Misma semilla debe dar el mismo resultado"

    # Coordenadas editadas: el usuario mueve una ciudad y agrega otra
    edited = TSPProblem(problem.coordinates[:9] + ((10.0, 10.0), (50.0, 30.0)))
    edited_config = replace(config, problem=edited, generations=40)
    edited_gens = ACOEngine().run(edited_config)
    validate_aco_generations(edited_gens, edited_config)
    edited_route, edited_score, _ = best_solution(edited_gens)
    print(f"Coordenadas editadas (11 ciudades): {edited.describe(edited_route)} = {edited_score:.4f} "
          f"(óptimo {tsp_optimum(edited):.4f})")


# Instancia pequeña (8 tareas × 3 recursos) solo para pruebas: con 3⁸ = 6561 combinaciones se
# puede calcular el óptimo exacto por fuerza bruta. El ejemplo de data/asignacion.json es más grande.
SMALL_ASSIGNMENT = AssignmentProblem(
    costs=((9.0, 4.0, 7.0), (6.0, 8.0, 3.0), (5.0, 3.0, 9.0), (8.0, 6.0, 4.0),
           (4.0, 9.0, 6.0), (7.0, 5.0, 8.0), (3.0, 7.0, 5.0), (6.0, 4.0, 6.0)),
    demands=(4.0, 3.0, 5.0, 2.0, 4.0, 3.0, 2.0, 5.0),
    capacities=(10.0, 10.0, 9.0),
)


def check_assignment() -> None:
    """Ejemplo asignación (data/asignacion.json): respeta capacidades y el costo baja durante la búsqueda."""
    problem = default_assignment()
    config = ACOConfig(problem, ants=15, generations=50, alpha=1.0, beta=2.0, rho=0.3, q=1.0, seed=42)
    engine = ACOEngine()
    generations = engine.run(config)
    validate_aco_generations(generations, config)
    print_report(f"Ejemplo 2 · ACO sobre asignación ({problem.size} tareas, {problem.resources} recursos)", config, engine, generations)

    assignment, score, found_at = best_solution(generations)
    loads = problem.loads(assignment)
    print("Carga por recurso: " + ", ".join(f"{name}={load:g}/{cap:g}" for name, load, cap in zip(problem.resource_labels, loads, problem.capacities)))
    assert problem.is_feasible(assignment), "La mejor asignación excede alguna capacidad"
    assert score == problem.total_cost(assignment), "Una solución factible no debe tener penalización"
    history = best_history(generations)
    assert history[-1] < history[0] and found_at > 0, "La colonia debería mejorar la solución inicial"
    print(f"Mejora: iteración 0 = {history[0]:g} → final = {history[-1]:g}")

    # Instancia pequeña: ACO alcanza el óptimo exacto de fuerza bruta
    small = SMALL_ASSIGNMENT
    small_config = replace(config, problem=small)
    small_solution, small_score, _ = best_solution(ACOEngine().run(small_config))
    optimum_vector, optimum = assignment_optimum(small)
    print(f"Instancia de prueba 8×3: ACO {small_solution} = {small_score:g}; óptimo exacto {optimum_vector} = {optimum:g}")
    assert small_score == optimum, "ACO no alcanzó el óptimo en la instancia pequeña"
    problem = small

    # Una solución infactible siempre se evalúa peor que cualquier factible
    overloaded = (1,) * problem.size
    assert not problem.is_feasible(overloaded) and problem.evaluate(overloaded) > sum(max(r) for r in problem.costs)

    # Datos editados: el usuario cambia capacidades y un costo
    edited = replace(problem, capacities=(12.0, 8.0, 10.0), costs=((1.0, 4.0, 7.0),) + problem.costs[1:])
    edited_config = replace(config, problem=edited)
    edited_solution, edited_score, _ = best_solution(ACOEngine().run(edited_config))
    print(f"Datos editados: {edited_solution} = {edited_score:g} (óptimo {assignment_optimum(edited)[1]:g})")


def check_validation_and_stop() -> None:
    """Rechaza datos/parámetros inválidos y permite detener la ejecución."""
    base = ACOConfig(default_tsp(), ants=5, generations=10)
    invalid = (
        replace(base, ants=1), replace(base, generations=0), replace(base, rho=1.0),
        replace(base, alpha=float("nan")), replace(base, seed=-1), replace(base, ants=True),
        replace(base, initial_pheromone=-1.0), replace(base, patience=-1), replace(base, patience=2.5),
        replace(base, problem=TSPProblem(((0.0, 0.0), (1.0, 1.0)))),
        replace(base, problem=TSPProblem(((0.0, 0.0), (1.0, 1.0), (0.0, 0.0)))),
        replace(base, problem=replace(default_assignment(), capacities=(1.0, 1.0, 1.0))),
        replace(base, problem=replace(default_assignment(), demands=(4.0,))),
    )
    for config in invalid:
        try:
            ACOEngine().run(config)
        except ValueError:
            continue
        raise AssertionError(f"Se aceptó una configuración inválida: {config}")
    try:
        default_tsp().check_route((0, 1, 1, 3, 4, 5, 6, 7, 8, 9))
    except ValueError:
        pass
    else:
        raise AssertionError("Se aceptó una ruta con ciudad repetida")

    calls = iter(range(100))
    engine = ACOEngine()
    partial = engine.run(base, should_stop=lambda: next(calls) >= 4)
    assert len(partial) == 4 and "Detenido" in engine.stop_reason

    # Etiquetas, explicaciones y valores iniciales de cada parámetro coinciden con ACOConfig
    defaults = ACOConfig(default_tsp())
    for name, spec in ACO_PARAMETERS.items():
        assert spec.label and spec.help and getattr(defaults, name) == spec.default, name
    print("\nValidaciones: parámetros, datos inválidos, rutas repetidas y botón Detener verificados.")


def check_initial_pheromone_and_convergence() -> None:
    """La feromona inicial cambia la búsqueda y la paciencia detiene por convergencia anticipada."""
    config = ACOConfig(default_tsp(), ants=10, generations=100, seed=7)
    automatic = ACOEngine().run(config)
    manual_config = replace(config, initial_pheromone=5.0)
    manual = ACOEngine().run(manual_config)
    validate_aco_generations(manual, manual_config)
    assert manual != automatic, "La feromona inicial no tuvo efecto"
    print(f"\nFeromona inicial: automática → {best_solution(automatic)[1]:.4f}, τ0=5 → {best_solution(manual)[1]:.4f}")

    early_config = replace(config, patience=15)
    engine = ACOEngine()
    early = engine.run(early_config)
    validate_aco_generations(early, early_config)
    assert len(early) < config.generations + 1 and "Convergencia anticipada" in engine.stop_reason
    history = best_history(early)
    assert history[-1] == history[-1 - early_config.patience], "Paró aunque el mejor costo seguía mejorando"
    print(f"Convergencia anticipada: {engine.stop_reason} ({len(early)-1} de {config.generations} iteraciones)")


if __name__ == "__main__":
    check_tsp()
    check_assignment()
    check_validation_and_stop()
    check_initial_pheromone_and_convergence()
    print("\nTodas las pruebas de ACO pasaron.")
