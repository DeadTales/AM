"""Regresiones de nombres, parámetros efectivos, mejor primero, progreso y exportación."""
import asyncio
import csv
from dataclasses import replace
import json
from pathlib import Path
import sys
import tempfile
from threading import Event
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from models.ais_engine import AISConfig, AISEngine
from models.ais_problems import OneMax
from models.aco_engine import ACOEngine
from models.categorical import default_tsp
from models.contracts import ACOConfig, AlgorithmConfig, PSOConfig
from models.de_engine import DEConfig, DEEngine
from models.demo_engine import initial_population
from models.genetic_engine import GeneticEngine
from models.objectives import get_objective
from models.pso_engine import PSOEngine
from models.results import best_individual
from views.application import OptimizationApp
from views.dashboard import Dashboard


def page():
    return SimpleNamespace(update=lambda: None)


class GateEngine:
    """Publica la inicialización y mantiene el hilo abierto hasta que la prueba lo libere."""
    def __init__(self, base):
        self.base, self.started, self.release = base, Event(), Event()
        self.calls = 0

    @property
    def stop_reason(self):
        return self.base.stop_reason

    def run(self, *args, should_stop=None, on_generation=None):
        self.calls += 1

        def publish(generation):
            on_generation(generation)
            if generation.index == 0:
                self.started.set()
                if not self.release.wait(5):
                    raise TimeoutError("No se liberó el motor de prueba.")
        return self.base.run(*args, should_stop=should_stop, on_generation=publish)


class RunWorkflowChecks(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        asyncio.get_running_loop().slow_callback_duration = 1.0

    def continuous(self, kind="pso", maximize=False):
        panel = Dashboard(page(), algorithm=kind)
        panel.build()
        panel.function.value, panel.dimensions.value = "sphere", "2"
        panel.change_objective()
        panel.optimization.value = "max" if maximize else "min"
        panel.size.value, panel.generations.value = "12", "8"
        panel.configure()
        return panel

    def test_parameter_labels_and_type_filter(self):
        app = OptimizationApp(page())
        ga, pso, de, ais, aco = (app.panels[key] for key in ("genetic", "pso", "de", "ais", "aco"))
        self.assertEqual(ga.size.label, "Tamaño de población")
        self.assertEqual(ga.selection.label, "Método de selección")
        self.assertTrue(ga.crossover_label.value.startswith("Tasa de cruza"))
        self.assertTrue(ga.mutation_label.value.startswith("Tasa de mutación"))
        self.assertEqual(ga.generations.label, "Número de generaciones")
        self.assertEqual(pso.size.label, "Número de partículas")
        self.assertIn("Límites de velocidad", pso.velocity_limit.label)
        self.assertEqual(pso.generations.label, "Número de iteraciones")
        self.assertEqual(de.generations.label, "Número de generaciones")
        self.assertIn("Estrategia de selección", de.de_strategy.label)
        self.assertEqual(ais.population_size.label, "Número de anticuerpos")
        self.assertEqual(ais.cloning_rate.label, "Tasa de clonación")
        self.assertEqual(ais.mutation_rate.label, "Tasa de mutación")
        self.assertEqual(ais.selection_fraction.label, "Selección clonal")
        self.assertTrue(all(control.helper for control in aco.parameter_fields.values()))
        for kind, visible in (("binary", {"ais"}), ("categorical", {"aco"}),
                              ("continuous", {"genetic", "pso", "de"})):
            app.problem_type.value = kind
            app.change_problem_type()
            self.assertEqual({key for key, button in app.menu.buttons.items() if button.visible}, visible)

    def test_pso_velocity_limit_changes_actual_movement(self):
        objective = get_objective("sphere", 1)
        base = PSOConfig(((-0.5,), (0.5,)), objective, 1, inertia=1, cognitive=0, social=0, seed=42)
        low = PSOEngine().run(replace(base, velocity_limit=0.001))
        high = PSOEngine().run(base)
        self.assertTrue(all(abs(new[0] - old[0]) <= 0.01000001 for old, new in zip(base.population, low[-1].population)))
        self.assertNotEqual(low[-1].population, high[-1].population)
        with self.assertRaises(ValueError):
            PSOEngine().run(replace(base, velocity_limit=0))

    def test_ais_cloning_mutation_and_selection_parameters_are_effective(self):
        original = OneMax.evaluate

        def evaluations(config):
            seen = []

            def evaluate(problem, vector):
                seen.append(vector)
                return original(problem, vector)
            with patch.object(OneMax, "evaluate", evaluate):
                AISEngine().run(OneMax(8), config)
            return seen
        base = AISConfig(population_size=12, iterations=1, max_clones=4, seed=7,
                         mutation_rate=0, diversity_fraction=0)
        without = evaluations(replace(base, cloning_rate=0))
        with_clones = evaluations(base)
        mutated = evaluations(replace(base, mutation_rate=1))
        more_selected = evaluations(replace(base, selection_fraction=1))
        self.assertEqual(len(without), 12)
        self.assertGreater(len(with_clones), 12)
        self.assertGreater(len(more_selected), len(with_clones))
        self.assertEqual(mutated[:12], with_clones[:12])
        self.assertEqual(mutated[12:], [tuple(1-bit for bit in vector) for vector in with_clones[12:]])

    async def test_best_is_first_for_min_and_max_without_reordering_engine_data(self):
        for kind in ("genetic", "pso", "de"):
            for maximize in (False, True):
                with self.subTest(kind=kind, maximize=maximize):
                    panel = self.continuous(kind, maximize)
                    await panel.apply()
                    self.assertTrue(panel.snapshots, panel.message.value)
                    expected = best_individual(panel.snapshots, maximize)
                    self.assertEqual(panel.displayed_best, expected)
                    self.assertEqual(panel.table.controls[0].content.controls[0].value, "Mejor encontrado")
                    self.assertIn(f"{expected.fitness:.8g}", panel.table.controls[0].content.controls[1].value)
                    self.assertEqual(panel.snapshots[0].population, panel.config.population)
                    self.assertEqual(panel.index, len(panel.snapshots)-1)
                    panel.step(-panel.index)
                    self.assertEqual(panel.displayed_best, best_individual(panel.snapshots[:1], maximize))

    async def test_pso_historical_record_is_not_replaced_by_a_worse_final_particle(self):
        panel = self.continuous("pso")
        panel.seed.value = "0"
        await panel.apply()
        expected = best_individual(panel.snapshots)
        self.assertLess(expected.fitness, min(panel.snapshots[-1].scores))
        self.assertEqual(panel.displayed_best, expected)
        self.assertEqual(panel.run_record["best"]["solution"], expected.solution)
        self.assertEqual(expected.iteration, 7)

    async def test_population_size_is_applied_explicitly_and_manual_edits_update_it(self):
        panel = self.continuous("genetic")
        panel.size.value = "8"
        await panel.apply()
        self.assertEqual(panel.snapshots, [])
        self.assertIn("Generar población", panel.message.value)
        panel.configure()
        await panel.apply()
        self.assertEqual(len(panel.config.population), 8)
        panel.reset()
        panel.editor.delete(0)
        self.assertEqual(panel.size.value, "7")

    async def test_export_csv_and_json_for_all_five_algorithms(self):
        app = OptimizationApp(page())
        with tempfile.TemporaryDirectory() as directory:
            for kind, panel in app.panels.items():
                with self.subTest(kind=kind):
                    if kind in ("genetic", "pso", "de"):
                        panel.generations.value = "4"
                        await panel.apply()
                    elif kind == "ais":
                        panel.problem.value = "knapsack"
                        panel.weights.value, panel.values.value, panel.capacity.value = "2,3", "4,5", "5"
                        panel.iterations.value = "4"
                        await panel.apply()
                    else:
                        for name, value in (("ants", "5"), ("generations", "4"), ("patience", "0")):
                            panel.parameter_fields[name].value = value
                        await panel.run_aco()
                    self.assertIsNotNone(panel.run_record)
                    self.assertFalse(panel.exporter.button.disabled)
                    target = Path(directory) / kind
                    panel.exporter.directory = target
                    # Editar el formulario no debe cambiar la ejecución exportada.
                    if kind == "ais":
                        panel.weights.value = "999,999"
                    panel.exporter.save()
                    record = json.loads(next(target.glob("*.json")).read_text(encoding="utf-8"))
                    with next(target.glob("*.csv")).open(encoding="utf-8-sig", newline="") as stream:
                        rows = list(csv.DictReader(stream))
                    self.assertEqual(record["algorithm"], kind)
                    self.assertEqual(len(rows), len(record["history"]))
                    self.assertEqual(record["history"][0]["iteration"], 0)
                    self.assertTrue(record["stop_reason"])
                    self.assertEqual(float(rows[-1]["best_fitness"]), record["best"]["fitness"])
                    self.assertEqual(json.loads(rows[-1]["best_solution"]), record["best"]["solution"])
                    if kind == "ais":
                        self.assertEqual(record["problem"]["data"]["weights"], [2, 3])
                    panel.exporter.save()
                    self.assertEqual(len(list(target.glob("*.json"))), 2)

    async def test_export_error_is_reported_and_can_be_retried(self):
        panel = self.continuous("de")
        await panel.apply()
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "file"
            file.write_text("dato ficticio", encoding="utf-8")
            panel.exporter.directory = file
            panel.exporter.save()
            self.assertIn("No se pudo exportar", panel.exporter.status.value)
            panel.exporter.directory = Path(directory) / "results"
            panel.exporter.save()
            self.assertIn("Guardado", panel.exporter.status.value)

    def test_all_engines_publish_initial_and_intermediate_states_and_stop(self):
        objective = get_objective("sphere", 2)
        population = tuple(initial_population(8, objective))
        runs = [(GeneticEngine(7), (AlgorithmConfig(population, objective, 0.1, "torneo", 20),)),
                (PSOEngine(), (PSOConfig(population, objective, 20),)),
                (DEEngine(), (DEConfig(population, objective, 20),)),
                (AISEngine(), (OneMax(8), AISConfig(iterations=20))),
                (ACOEngine(), (ACOConfig(default_tsp(), ants=4, generations=20),))]
        for engine, args in runs:
            states = []
            result = engine.run(*args, should_stop=lambda: len(states) >= 3, on_generation=states.append)
            generations = list(result.generations) if hasattr(result, "generations") else result
            self.assertEqual([g.index for g in states], [0, 1, 2])
            self.assertEqual(states, generations)
            self.assertIn("Detenido", engine.stop_reason)

    async def test_progress_and_stop_remain_responsive_in_every_panel(self):
        app = OptimizationApp(page())
        for kind, panel in app.panels.items():
            with self.subTest(kind=kind):
                engine = GateEngine(panel.engine)
                panel.engine = engine
                task = asyncio.create_task(panel.run_aco() if kind == "aco" else panel.apply())
                try:
                    self.assertTrue(await asyncio.to_thread(engine.started.wait, 2))
                    for _ in range(100):
                        frames = panel.generations if kind in ("aco", "ais") else panel.snapshots
                        if frames:
                            break
                        await asyncio.sleep(0.02)
                    self.assertTrue(frames)
                    self.assertTrue(panel._running if kind == "aco" else panel.busy)
                    self.assertTrue(panel.exporter.button.disabled)
                    panel._pause() if kind == "aco" else panel.request_stop()
                    panel.reset()
                    self.assertIsNotNone(panel.config if kind != "ais" else panel.last_config)
                finally:
                    engine.release.set()
                    await asyncio.wait_for(task, 5)
                self.assertEqual(engine.calls, 1)
                self.assertIn("Detenido", panel.run_record["stop_reason"])
                self.assertEqual(panel.run_record["iterations_executed"], 0)

    async def test_history_and_reset_for_every_panel(self):
        app = OptimizationApp(page())
        for kind, panel in app.panels.items():
            if kind in ("genetic", "pso", "de"):
                panel.generations.value = "6"
                await panel.apply()
                states = panel.snapshots
                for index in (0, 2, 4, 6):
                    panel.step(index-panel.index)
                    self.assertEqual(panel.index, index)
                kept = panel.generations.value
            elif kind == "ais":
                panel.iterations.value = "6"
                await panel.apply()
                states = panel.generations
                for index in (0, 2, 4, 6):
                    panel.browser.select(index)
                    self.assertEqual(panel.browser.index, index)
                    self.assertEqual(panel.displayed_best.fitness, panel.history[index])
                kept = panel.iterations.value
            else:
                panel.parameter_fields["generations"].value = "6"
                panel.parameter_fields["patience"].value = "0"
                await panel.run_aco()
                states = panel.generations
                for index in (0, 2, 4, 6):
                    panel.browser.select(index)
                    self.assertEqual(panel.browser.index, index)
                kept = panel.parameter_fields["generations"].value
            self.assertEqual(len(states), 7)
            panel.reset()
            self.assertIsNone(panel.run_record)
            self.assertTrue(panel.exporter.button.disabled)
            if kind in ("genetic", "pso", "de"):
                self.assertEqual(panel.snapshots, [])
                self.assertEqual(panel.generations.value, kept)
            else:
                self.assertEqual(panel.generations, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
