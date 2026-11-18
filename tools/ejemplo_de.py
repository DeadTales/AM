"""Ejemplo de Evolución Diferencial: configuración, mejor solución e historial por iteración.

Uso (desde la raíz del proyecto):
    python tools/ejemplo_de.py                      # Rastrigin 2D (valores por defecto)
    python tools/ejemplo_de.py schwefel 5           # Schwefel con 5 variables
    python tools/ejemplo_de.py griewank 3 --iter 100 --F 0.5 --CR 0.9 --seed 7 --estrategia best/1/bin

Imprime el resultado y guarda el historial en ejemplos/de_<función>.csv y .json.
"""
import argparse
import csv
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
from models.de_engine import STRATEGIES, DEConfig, DEEngine
from models.demo_engine import initial_population
from models.objectives import FUNCTIONS, get_objective


def main():
    parser = argparse.ArgumentParser(description="Ejemplo de Evolución Diferencial")
    parser.add_argument("funcion", nargs="?", default="rastrigin", choices=list(FUNCTIONS))
    parser.add_argument("dimension", nargs="?", type=int, default=None, help="Sólo Schwefel y Griewank")
    parser.add_argument("--poblacion", type=int, default=20)
    parser.add_argument("--iter", type=int, default=50)
    parser.add_argument("--F", type=float, default=0.8)
    parser.add_argument("--CR", type=float, default=0.9)
    parser.add_argument("--estrategia", default="rand/1/bin", choices=STRATEGIES)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    # 1. Configuración
    objective = get_objective(args.funcion, args.dimension)
    population = tuple(initial_population(args.poblacion, objective))
    config = DEConfig(population, objective, args.iter, args.F, args.CR, args.estrategia, args.seed)
    choose = max if objective.maximize else min

    print("=== Configuración ===")
    print(f"Función:      {objective.name}  ({'maximización' if objective.maximize else 'minimización'})")
    print(f"Fórmula:      {objective.expression}")
    print(f"Variables:    {objective.dimensions}  · dominio {objective.bounds[0]} por coordenada")
    print(f"Población:    {len(population)} individuos (generados con semilla 42)")
    print(f"Iteraciones:  {config.generations}")
    print(f"F = {config.mutation_factor} · CR = {config.crossover_rate} · estrategia {config.strategy} · semilla {config.seed}")

    # 2. Ejecución
    generations = DEEngine().run(config)

    # 3. Historial por iteración: mejor, promedio y peor de la población, y mejor individuo.
    rows = []
    for g in generations:
        best_i = g.scores.index(choose(g.scores))
        rows.append({
            "iteracion": g.index,
            "mejor": g.scores[best_i],
            "promedio": statistics.fmean(g.scores),
            "peor": (min if objective.maximize else max)(g.scores),
            "mejor_individuo": list(g.population[best_i]),
        })

    print("\n=== Historial por iteración ===")
    print(f"{'Iter':>5}{'Mejor':>16}{'Promedio':>16}{'Peor':>16}   Mejor individuo")
    for r in rows:
        coords = ", ".join(f"{v:.5f}" for v in r["mejor_individuo"])
        print(f"{r['iteracion']:>5}{r['mejor']:>16.8g}{r['promedio']:>16.8g}{r['peor']:>16.8g}   ({coords})")

    # 4. Mejor solución final
    final = rows[-1]
    print("\n=== Mejor solución ===")
    for label, value in zip(objective.labels, final["mejor_individuo"]):
        print(f"{label} = {value:.6f}")
    print(f"f = {final['mejor']:.10g}")
    print("Motivo de término: se alcanzó el número máximo de iteraciones.")

    # 5. Guardar historial
    out_dir = ROOT/"ejemplos"
    out_dir.mkdir(exist_ok=True)
    stem = f"de_{args.funcion}" + (f"_{objective.dimensions}d" if args.dimension else "")
    with open(out_dir/f"{stem}.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["iteracion", "mejor", "promedio", "peor", *objective.labels])
        for r in rows:
            writer.writerow([r["iteracion"], r["mejor"], r["promedio"], r["peor"], *r["mejor_individuo"]])
    summary = {
        "configuracion": {
            "funcion": objective.name, "clave": args.funcion, "formula": objective.expression,
            "variables": objective.dimensions, "dominio": objective.bounds[0],
            "maximizar": objective.maximize, "poblacion": len(population), "iteraciones": config.generations,
            "F": config.mutation_factor, "CR": config.crossover_rate,
            "estrategia": config.strategy, "semilla": config.seed,
        },
        "mejor_solucion": {"vector": final["mejor_individuo"], "valor": final["mejor"]},
        "motivo_termino": "Número máximo de iteraciones",
        "historial": rows,
    }
    (out_dir/f"{stem}.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nHistorial guardado en ejemplos/{stem}.csv y ejemplos/{stem}.json")


if __name__ == "__main__":
    main()
