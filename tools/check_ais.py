"""Pruebas reproducibles de AIS. Los ejemplos editables se ejecutan con opciones de línea de comandos."""
import argparse
from itertools import product
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from models.ais_engine import AISConfig, AISResult, AISEngine
from models.ais_problems import KNAPSACK_EXAMPLE_PATH, Knapsack, OneMax, load_knapsack_example


def show_result(name: str, result: AISResult) -> None:
    print(f"\n{name}")
    print(f"Vector: {list(result.vector)}")
    print(f"Valor: {result.value}")
    if result.weight is not None:
        print(f"Peso: {result.weight}")
    print(f"Historial desde la iteración 0: {list(result.history)}")


def check_history(result: AISResult, config: AISConfig) -> None:
    assert len(result.history) == config.iterations + 1
    assert result.history[-1] == result.value
    assert all(old <= new for old, new in zip(result.history, result.history[1:]))


def check_onemax() -> None:
    problem = OneMax(length=16)
    config = AISConfig()
    engine = AISEngine()
    result = engine.run(problem, config)
    assert result == engine.run(problem, config)
    assert result.vector == (1,) * problem.length
    assert result.value == problem.evaluate(result.vector) == problem.length
    assert result.weight is None
    check_history(result, config)
    show_result("Prueba OneMax", result)


def check_knapsack() -> None:
    # Caso fijo para que editar el JSON de ejemplo no cambie el resultado esperado.
    problem = Knapsack((2, 3, 4, 5, 7, 8, 9, 10), (6, 8, 9, 10, 13, 14, 17, 18), 17)
    config = AISConfig()
    result = AISEngine().run(problem, config)
    assert result.weight == problem.weight(result.vector) <= problem.capacity
    assert result.value == problem.evaluate(result.vector)

    # Sólo la prueba enumera las 2^8 combinaciones para verificar el óptimo de referencia.
    optimum = max(
        problem.evaluate(bits)
        for bits in product((0, 1), repeat=problem.length)
        if problem.weight(bits) <= problem.capacity
    )
    assert result.value == optimum == 37
    assert result.history[0] < result.value
    check_history(result, config)
    show_result(f"Prueba Mochila 0/1 · capacidad {problem.capacity}", result)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    examples = parser.add_mutually_exclusive_group()
    examples.add_argument("--longitud", type=int, help="Ejecuta OneMax con la longitud indicada.")
    examples.add_argument("--mochila", nargs="?", const=KNAPSACK_EXAMPLE_PATH, type=Path,
                          help="Ejecuta el JSON precargado o el archivo indicado.")
    args = parser.parse_args()
    try:
        if args.longitud is not None:
            problem = OneMax(length=args.longitud)
            show_result(f"OneMax · longitud {problem.length}", AISEngine().run(problem))
        elif args.mochila is not None:
            problem = load_knapsack_example(args.mochila)
            show_result(f"Mochila 0/1 · capacidad {problem.capacity}", AISEngine().run(problem))
        else:
            check_onemax()
            check_knapsack()
            print("\nPasaron las dos pruebas.")
    except (ValueError, OSError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
