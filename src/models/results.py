"""Resultados y exportaciones independientes de la interfaz y del directorio actual."""
import csv
from dataclasses import asdict, dataclass, fields
import json
from pathlib import Path
from uuid import uuid4

RESULTS_DIR = Path(__file__).resolve().parents[2] / "artifacts" / "results"


@dataclass(frozen=True)
class BestIndividual:
    solution: tuple
    fitness: float
    iteration: int
    index: int


def best_individual(generations, maximize=False):
    """Devuelve un candidato real de todo el historial recibido, con su procedencia."""
    best = None
    for generation in generations:
        for index, (vector, score) in enumerate(zip(generation.population, generation.scores)):
            if best is None or (score > best.fitness if maximize else score < best.fitness):
                best = BestIndividual(tuple(vector), score, generation.index, index)
    return best


def make_record(algorithm, config, generations, stop_reason, problem=None):
    """Captura los datos aplicados, nunca los campos editables de la pantalla."""
    if not generations:
        return None
    objective = getattr(config, "objective", None)
    problem = problem or getattr(config, "problem", None)
    maximize = objective.maximize if objective else algorithm == "ais"
    parameters = {field.name: getattr(config, field.name) for field in fields(config)
                  if field.name not in ("objective", "problem", "population")}
    if objective:
        parameters["population_size"] = len(config.population)
        if algorithm == "pso":
            parameters["velocity_limit_percent"] = config.velocity_limit * 100
        definition = {"name": objective.name, "expression": objective.expression,
                      "representation": "continuous", "labels": objective.labels,
                      "bounds": objective.bounds, "initial_population": config.population}
        parameters["variant"] = {
            "genetic": "GA con elitismo, BLX-alpha=0.25 y mutación gaussiana sigma=10% del intervalo",
            "pso": "PSO global-best; velocidad inicial uniforme en ±5% del intervalo",
            "de": f"DE {config.strategy}" if algorithm == "de" else "",
        }[algorithm]
    else:
        definition = {"name": getattr(problem, "name", type(problem).__name__),
                      "representation": "binary" if algorithm == "ais" else "categorical",
                      "data": asdict(problem)}
        parameters["variant"] = ("Selección clonal por afinidad e hipermutación adaptativa hasta 4 veces la tasa base"
                                 if algorithm == "ais" else "Ant System con refuerzo elitista")
        if algorithm == "ais":
            parameters["effective_mutation_rate"] = 1 / problem.length if config.mutation_rate is None else config.mutation_rate
    history, best = [], None
    for generation in generations:
        current = best_individual([generation], maximize)
        if best is None or (current.fitness > best.fitness if maximize else current.fitness < best.fitness):
            best = current
        history.append({"iteration": generation.index, "best_fitness": best.fitness,
                        "best_solution": best.solution, "best_in_iteration": current.fitness,
                        "population": generation.population, "fitness": generation.scores})
    return {"schema_version": 1, "algorithm": algorithm, "problem": definition,
            "objective": "maximize" if maximize else "minimize", "configuration": parameters,
            "iterations_requested": getattr(config, "generations", getattr(config, "iterations", 0)),
            "iterations_executed": generations[-1].index, "stop_reason": stop_reason,
            "best": asdict(best), "history": history}


def export_record(record, directory=RESULTS_DIR):
    """Guarda CSV por iteración y JSON completo con nombres únicos, sin sobrescribir."""
    if not record or not record["history"]:
        raise ValueError("Primero ejecuta el algoritmo para generar resultados.")
    encoded = json.dumps(record, ensure_ascii=False, indent=2, allow_nan=False)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    stem = f"{record['algorithm']}_{uuid4().hex[:12]}"
    csv_path, json_path = directory / f"{stem}.csv", directory / f"{stem}.json"
    configuration = json.dumps({"problem": record["problem"], "parameters": record["configuration"]}, ensure_ascii=False)
    with csv_path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.writer(stream)
        writer.writerow(["algorithm", "problem", "objective", "iteration", "best_fitness", "best_solution",
                         "best_in_iteration", "iterations_executed", "stop_reason", "configuration"])
        for row in record["history"]:
            writer.writerow([record["algorithm"], record["problem"]["name"], record["objective"], row["iteration"],
                             row["best_fitness"], json.dumps(row["best_solution"]), row["best_in_iteration"],
                             record["iterations_executed"], record["stop_reason"], configuration])
    json_path.write_text(encoded, encoding="utf-8")
    return csv_path, json_path
