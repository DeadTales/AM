"""Pruebas reproducibles de simulación, comparaciones, exportación y menú de algoritmos."""
import asyncio
from dataclasses import replace
import json
from pathlib import Path
import random
import sys
import tempfile
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
from models.contracts import Objective, PSOConfig, validate_generations
from models.demo_engine import initial_population
from models.objectives import FUNCTIONS, get_objective
from models.pso_demo_engine import PSODemoEngine
from models.pso_engine import PSOEngine
from models.pso_experiments import best_history, comparable, compare_parameters, export_trials
from views.application import OptimizationApp
from views.menu import Menu
from views.submenu import Submenu


def check_simulation():
    """Verifica ecuación inicial, dominio, finitud, max/min y sensibilidad de coeficientes."""
    engine = PSODemoEngine()
    for key in FUNCTIONS:
        objective = get_objective(key)
        config = PSOConfig(tuple(initial_population(12, objective)), objective, 15)
        snapshots = engine.run(config)
        validate_generations(snapshots, config)
        assert snapshots == engine.run(config)
        assert all(g.scores == tuple(objective.evaluate(p) for p in g.population) for g in snapshots)
        history = best_history(snapshots, objective.maximize)
        assert all(b >= a if objective.maximize else b <= a for a, b in zip(history, history[1:]))
        for changed in (replace(config, inertia=0.2), replace(config, cognitive=3), replace(config, social=0.2)):
            assert engine.run(changed)[-1].population != snapshots[-1].population
    objective = Objective("Cuadrado", "x²", ("x",), ((-10,10),), lambda v:v[0]**2)
    config = PSOConfig(((4.,), (1.,)), objective, 1)
    rng = random.Random(config.seed)
    velocities = [rng.uniform(-1, 1) for _ in range(2)]
    expected = []
    for i, (x,) in enumerate(config.population):
        rng.random()  # r1: desplazamiento personal igual a cero al inicio.
        r2 = rng.random()
        velocity = config.inertia*velocities[i]+config.social*r2*(1-x)
        expected.append((x+max(-4, min(4, velocity)),))
    assert engine.run(config)[1].population == tuple(expected)
    for invalid in (replace(config, inertia=float("nan")), replace(config, cognitive=-1), replace(config, social=5), replace(config, generations=0), replace(config, seed=-1)):
        try:
            engine.run(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("Se aceptó una configuración inválida")
    try:
        PSOEngine().run(config)
    except NotImplementedError:
        pass
    else:
        raise AssertionError("El punto de integración no debe fingir un PSO definitivo")
    print("Simulación: cinco funciones, ecuación, semilla, max/min y coeficientes verificados.")


def check_experiments():
    """Garantiza comparación de un factor, posiciones idénticas y archivos reproducibles."""
    objective = get_objective("ackley")
    config = PSOConfig(tuple(initial_population(10, objective)), objective, 10)
    trials = compare_parameters(config, PSODemoEngine())
    assert len(trials) == 7
    for trial in trials:
        assert comparable(config, trial.config)
        assert all(0 <= spread <= 0.51 for spread in trial.spread)
        changed = sum(getattr(config, name) != getattr(trial.config, name) for name in ("inertia", "cognitive", "social"))
        assert changed == (0 if trial.name == "Base" else 1)
    assert not comparable(config, replace(config, seed=43))
    assert not comparable(config, replace(config, population=config.population[::-1]))
    trials[0].notes = "Observación de ejemplo, sin inferir superioridad general."
    with tempfile.TemporaryDirectory() as folder:
        csv_path, json_path = export_trials(trials, Path(folder))
        records = json.loads(json_path.read_text(encoding="utf-8"))
        assert len(records) == 7 and records[0]["notes"] == trials[0].notes
        assert records[0]["initial_population"] == [list(v) for v in config.population]
        assert len(csv_path.read_text(encoding="utf-8-sig").splitlines()) == 1+7*11
    print("Comparaciones: un coeficiente por variante, constantes y CSV/JSON verificados.")


async def check_interface():
    """Verifica independencia de paneles, registro, validación y vista de comparación."""
    app = OptimizationApp(SimpleNamespace(update=lambda:None))
    app.build()
    genetic, pso = app.panels["genetic"], app.panels["pso"]
    assert isinstance(app.menu, Menu) and not isinstance(app.menu, Submenu)
    assert set(app.menu.buttons) == {"genetic", "pso"}
    assert isinstance(genetic.submenu, Submenu) and isinstance(pso.submenu, Submenu)
    assert set(genetic.submenu.buttons) == {"config", "results"}
    assert set(pso.submenu.buttons) == {"config", "results", "comparison"}
    assert pso.submenu.buttons["results"].disabled
    assert genetic.genetic_controls.visible and not genetic.pso_controls.visible
    assert pso.pso_controls.visible and not pso.genetic_controls.visible
    pso.generations.value = "4"
    pso.inertia.value = "0.9"
    await pso.apply()
    assert len(pso.snapshots) == 5 and pso.config.inertia == 0.9
    assert pso.config.objective.maximize and pso.history[-1] >= pso.history[0]
    assert "simulación" in pso.message.value
    app.menu.buttons["pso"].on_click(None)
    pso.submenu.back_button.on_click(None)
    assert app.active == "pso" and pso.router.active == "config"
    assert pso.inertia.value == "0.9" and len(pso.snapshots) == 5
    pso.submenu.buttons["results"].on_click(None)
    assert app.active == "pso" and pso.router.active == "results"
    app.menu.buttons["genetic"].on_click(None)
    assert pso.inertia.value == "0.9" and genetic.snapshots == []
    await pso.compare_pso()
    assert pso.router.active == "comparison" and len(pso.comparison.trials) == 8
    pso.inertia.value = "nan"
    await pso.apply()
    assert "w debe" in pso.message.value
    assert len(pso.snapshots) == 5
    print("Interfaz: Menu/Submenu independientes, Volver local, estado, pruebas y errores verificados.")


if __name__ == "__main__":
    check_simulation()
    check_experiments()
    asyncio.run(check_interface())
