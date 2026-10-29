"""Registro reproducible y comparación de parámetros de la simulación o motor PSO conectado."""
import csv
from dataclasses import dataclass, replace
import json
import math
from pathlib import Path
from uuid import uuid4
from models.contracts import Generation, PSOConfig, validate_generations


@dataclass
class PSOTrial:
    """Conserva configuración, mejor valor acumulado, dispersión por paso y notas editables."""
    name: str
    config: PSOConfig
    history: tuple[float, ...]
    spread: tuple[float, ...]
    simulated: bool
    notes: str = ""


def best_history(snapshots: list[Generation], maximize: bool) -> tuple[float, ...]:
    """Mejor evaluación encontrada hasta cada paso, aunque luego las partículas se alejen."""
    choose = max if maximize else min
    history = []
    for snapshot in snapshots:
        best = choose(snapshot.scores)
        history.append(choose(history[-1], best) if history else best)
    return tuple(history)


def make_trial(name: str, config: PSOConfig, snapshots: list[Generation], simulated: bool) -> PSOTrial:
    """Valida resultados y registra dispersión RMS normalizada por amplitud de cada dominio."""
    validate_generations(snapshots, config)
    spread = []
    for snapshot in snapshots:
        population = snapshot.population
        center = [sum(vector[d] for vector in population)/len(population) for d in range(config.objective.dimensions)]
        variance = sum(((vector[d]-center[d])/(hi-lo))**2 for vector in population for d, (lo, hi) in enumerate(config.objective.bounds))
        spread.append(math.sqrt(variance/(len(population)*config.objective.dimensions)))
    return PSOTrial(name, config, best_history(snapshots, config.objective.maximize), tuple(spread), simulated)


def comparable(a: PSOConfig, b: PSOConfig) -> bool:
    """Sólo compara misma función, dominio, posiciones iniciales, pasos y semilla."""
    return (a.objective.name, a.objective.expression, a.objective.labels, a.objective.bounds, a.objective.maximize, a.population, a.generations, a.seed) == (b.objective.name, b.objective.expression, b.objective.labels, b.objective.bounds, b.objective.maximize, b.population, b.generations, b.seed)


def compare_parameters(config: PSOConfig, engine) -> list[PSOTrial]:
    """Genera hasta siete pruebas cambiando un solo coeficiente respecto a la base."""
    config.validate()
    variants = [("Base", config)]
    for field, label, delta, maximum in (("inertia", "w", 0.3, 2), ("cognitive", "c1", 0.75, 4), ("social", "c2", 0.75, 4)):
        value = getattr(config, field)
        for suffix, candidate in (("bajo", max(0, value-delta)), ("alto", min(maximum, value+delta))):
            if candidate != value:
                variants.append((f"{label} {suffix}", replace(config, **{field:candidate})))
    return [make_trial(name, variant, engine.run(variant), getattr(engine, "is_demo", False)) for name, variant in variants]


def export_trials(trials: list[PSOTrial], directory: Path) -> tuple[Path, Path]:
    """Guarda CSV por iteración y JSON con posiciones iniciales, dominio, notas y parámetros."""
    directory.mkdir(parents=True, exist_ok=True)
    stem = "pso_"+uuid4().hex[:10]
    csv_path, json_path = directory/(stem+".csv"), directory/(stem+".json")
    records = []
    with csv_path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.writer(stream)
        writer.writerow(["prueba", "simulacion", "funcion", "maximizar", "particulas", "iteraciones", "semilla", "w", "c1", "c2", "iteracion", "mejor_acumulado", "dispersion", "notas"])
        for trial in trials:
            c = trial.config
            for index, (score, spread) in enumerate(zip(trial.history, trial.spread)):
                writer.writerow([trial.name, trial.simulated, c.objective.name, c.objective.maximize, len(c.population), c.generations, c.seed, c.inertia, c.cognitive, c.social, index, score, spread, trial.notes])
            records.append({"name":trial.name, "simulation":trial.simulated, "function":c.objective.name, "expression":c.objective.expression, "maximize":c.objective.maximize, "bounds":c.objective.bounds, "initial_population":c.population, "iterations":c.generations, "seed":c.seed, "w":c.inertia, "c1":c.cognitive, "c2":c.social, "history":trial.history, "spread":trial.spread, "notes":trial.notes})
    json_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    return csv_path, json_path
