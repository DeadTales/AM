"""Ejemplo de uso del motor ACO con los datos de prueba de data/.

Uso:  python examples/probar_aco.py

Ejecuta ACO sobre:
  1. TSP con las ciudades y coordenadas de data/tsp.json.
  2. Asignación de tareas con los costos y capacidades de data/asignacion.json.

Para cada uno muestra la configuración, la mejor solución encontrada, su costo y el historial
del mejor costo por iteración, empezando en la iteración 0 (inicialización). Todo se calcula
al ejecutar el algoritmo; nada está escrito de antemano.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
# Imprime en UTF-8 aunque la salida sea cp1252 (panel de salida de VS Code / Windows)
sys.stdout.reconfigure(encoding="utf-8")
from models.aco_engine import ACOEngine, best_history, best_solution
from models.categorical import load_assignment, load_tsp
from models.contracts import ACOConfig


def ejecutar(titulo: str, config: ACOConfig) -> None:
    """Corre ACO con la configuración dada e imprime los resultados que devuelve el motor."""
    engine = ACOEngine()
    generations = engine.run(config)                     # una entrada por iteración (0..N)
    solution, cost, found_at = best_solution(generations)  # mejor solución de toda la ejecución
    history = best_history(generations)                  # mejor costo acumulado por iteración
    problem = config.problem

    print(f"\n{'=' * 64}\n{titulo}\n{'=' * 64}")
    print(f"Problema: {problem.name}")
    print(f"Función objetivo: {problem.expression}")
    print(f"Configuración: hormigas={config.ants}, iteraciones={config.generations}, α={config.alpha}, "
          f"β={config.beta}, ρ={config.rho}, Q={config.q}, τ0={config.initial_pheromone or 'automática'}, "
          f"paciencia={config.patience or 'desactivada'}, semilla={config.seed}")
    print(f"\nMejor solución: {solution}")
    print(f"               {problem.describe(solution)}")
    print(f"Costo: {cost:.4f}  (encontrada en la iteración {found_at})")
    if problem.kind == "assignment":
        loads = problem.loads(solution)
        print("Carga por recurso: " + ", ".join(
            f"{name}={load:g}/{cap:g}" for name, load, cap in zip(problem.resource_labels, loads, problem.capacities)))
        print(f"Respeta capacidades: {'sí' if problem.is_feasible(solution) else 'no'}")
    print(f"Iteraciones ejecutadas: {len(generations) - 1}")
    print(f"Motivo de término: {engine.stop_reason}")

    print("\nHistorial del mejor costo por iteración (0 = inicialización):")
    for generation, best in zip(generations, history):
        print(f"  iteración {generation.index:>3}: {best:.4f}")


if __name__ == "__main__":
    ejecutar("ACO · Viajante (TSP)",
             ACOConfig(load_tsp(), ants=20, generations=60, alpha=1.0, beta=3.0, rho=0.3, q=1.0, seed=42))
    ejecutar("ACO · Asignación de tareas a recursos",
             ACOConfig(load_assignment(), ants=15, generations=50, alpha=1.0, beta=2.0, rho=0.3, q=1.0, seed=42))
