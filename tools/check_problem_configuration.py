"""Regresiones de la configuración de las tres representaciones con Flet real.

Uso: python tools/check_problem_configuration.py (sin abrir ventanas).
"""
import math
from pathlib import Path
import struct
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from models.aco_engine import best_solution
from models.contracts import validate_generations
from models.genetic_engine import GeneticEngine
from models.objectives import get_objective
from views.aco_panel import ACOPanel
from views.ais_panel import AISPanel
from models.aco_engine import ACOEngine
from models.ais_engine import AISEngine
from views.categorical_editor import instance_summary
from views.dashboard import Dashboard


def page():
    return SimpleNamespace(update=lambda: None)


class ConfigurationChecks(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Matplotlib puede tardar más de 100 ms sin que sea un fallo asíncrono.
        import asyncio
        asyncio.get_running_loop().slow_callback_duration = 1.0

    def continuous(self, algorithm, function="sphere", dimensions=3):
        kwargs = {"engine": GeneticEngine(seed=7)} if algorithm == "genetic" else {}
        panel = Dashboard(page(), algorithm=algorithm, **kwargs)
        panel.build()
        panel.function.value, panel.dimensions.value = function, str(dimensions)
        panel.change_objective()
        panel.size.value, panel.generations.value = "8", "8"
        return panel

    def aco(self):
        panel = ACOPanel(page(), ACOEngine())
        for name, value in (("ants", "8"), ("generations", "8"), ("patience", "0")):
            panel.parameter_fields[name].value = value
        return panel

    def assert_png(self, chart):
        png = chart.raster.src
        self.assertTrue(png.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertTrue(all(size > 100 for size in struct.unpack(">II", png[16:24])))

    def test_objective_keeps_the_formula_and_validates_domains(self):
        bounds = ((1.0, 2.0), (-3.0, -1.0), (5.0, 6.0))
        minimum = get_objective("sphere", 3, bounds=bounds, maximize=False)
        maximum = get_objective("sphere", 3, bounds=bounds, maximize=True)
        self.assertEqual(minimum.evaluate((1, 2, 3)), 14)
        self.assertEqual(maximum.evaluate((1, 2, 3)), 14)
        self.assertFalse(minimum.maximize)
        self.assertTrue(maximum.maximize)
        self.assertIn("Maximización", maximum.expression)
        self.assertNotIn("Minimización", maximum.expression)
        for bad in (((0, 1),), ((1, 1),) * 3, ((2, 1),) * 3,
                    ((0, math.nan),) * 3, ((-1e308, 1e308),) * 3):
            with self.subTest(bounds=bad), self.assertRaises(ValueError):
                get_objective("sphere", 3, bounds=bad)

    async def test_all_continuous_engines_use_dimension_bounds_and_direction(self):
        bounds = ((1.0, 2.0), (-3.0, -1.0), (5.0, 6.0))
        for algorithm in ("genetic", "pso", "de"):
            for direction in ("min", "max"):
                with self.subTest(algorithm=algorithm, direction=direction):
                    panel = self.continuous(algorithm)
                    panel.optimization.value = direction
                    panel.change_direction()
                    for controls, pair in zip(panel.bound_fields, bounds):
                        controls[0].value, controls[1].value = map(str, pair)
                    panel.configure()
                    await panel.apply()
                    self.assertTrue(panel.snapshots, panel.message.value)
                    objective = panel.config.objective
                    self.assertEqual(objective.dimensions, 3)
                    self.assertEqual(objective.bounds, bounds)
                    self.assertEqual(objective.maximize, direction == "max")
                    validate_generations(panel.snapshots, panel.config)
                    for snapshot in panel.snapshots:
                        self.assertEqual(snapshot.scores, tuple(objective.evaluate(v) for v in snapshot.population))
                    self.assertIn("Maximización" if direction == "max" else "Minimización", panel.result_summary.value)
                    self.assertIn("[5, 6]", panel.result_summary.value)
                    self.assert_png(panel.function_chart)
                    self.assert_png(panel.history_chart)
                    self.assertTrue(all(b >= a if direction == "max" else b <= a
                                        for a, b in zip(panel.history, panel.history[1:])))

    async def test_minimize_and_maximize_produce_different_searches(self):
        for algorithm in ("genetic", "pso", "de"):
            results = {}
            for direction in ("min", "max"):
                panel = self.continuous(algorithm, "linear_1d", 1)
                panel.optimization.value, panel.generations.value = direction, "40"
                panel.mutation.value = 100
                panel.configure()
                await panel.apply()
                self.assertTrue(panel.snapshots, panel.message.value)
                results[direction] = panel.history[-1]
            self.assertGreater(results["max"], 4.8, algorithm)
            self.assertLess(results["min"], -0.8, algorithm)

    async def test_ten_dimensions_and_fixed_variants_render_correctly(self):
        panel = self.continuous("de", dimensions=10)
        self.assertEqual(len(panel.dimensions.options), 10)
        self.assertEqual(len(panel.bound_fields), 10)
        panel.configure()
        await panel.apply()
        self.assertTrue(panel.snapshots, panel.message.value)
        self.assert_png(panel.function_chart)
        self.assertFalse(panel.chart_controls.visible)
        panel.function.value = "rastrigin"
        panel.change_objective()
        self.assertTrue(panel.dimensions.disabled)
        self.assertEqual(panel.dimensions.value, "2")
        self.assertEqual(len(panel.bound_fields), 2)

    async def test_invalid_domains_preserve_population_and_previous_results(self):
        panel = self.continuous("pso")
        panel.configure()
        await panel.apply()
        previous = panel.config
        population = panel.editor.individuals
        panel.bound_fields[0][0].value, panel.bound_fields[0][1].value = "3", "2"
        panel.configure()
        self.assertEqual(panel.editor.individuals, population)
        await panel.apply()
        self.assertIs(panel.config, previous)
        self.assertIn("mínimo menor", panel.message.value)
        self.assertFalse(panel.busy)

    async def test_bounds_excluding_population_are_reported_before_running(self):
        panel = self.continuous("de", dimensions=1)
        panel.bound_fields[0][0].value, panel.bound_fields[0][1].value = "100", "101"
        await panel.apply()
        self.assertEqual(panel.snapshots, [])
        self.assertIn("regenerar", panel.message.value)
        panel.configure()
        await panel.apply()
        self.assertTrue(panel.snapshots, panel.message.value)
        self.assertEqual(panel.config.objective.bounds, ((100, 101),))

    async def test_tsp_edits_reach_the_engine_and_are_preserved_in_the_result(self):
        panel = self.aco()
        editor = panel.problem_editor
        editor.cities[0][0].value = "Inicio ficticio"
        editor.cities[0][1].value, editor.cities[0][2].value = "-10", "7"
        editor.add_city()
        editor.start.value = "2"
        await panel.run_aco()
        self.assertTrue(panel.generations, panel.lbl_status.value)
        problem = panel.config.problem
        self.assertEqual(problem.coordinates[0], (-10, 7))
        self.assertEqual(problem.size, 11)
        self.assertEqual(problem.start, 2)
        solution, score, _ = best_solution(panel.generations)
        self.assertTrue(problem.is_feasible(solution))
        self.assertEqual(score, problem.evaluate(solution))
        snapshot = instance_summary(problem)
        editor.cities[0][1].value = "-20"
        self.assertEqual(instance_summary(problem), snapshot)
        self.assertNotEqual(editor.build_problem().coordinates, problem.coordinates)
        self.assert_png(panel.solution_chart)

    async def test_assignment_matrix_demands_and_capacities_reach_the_engine(self):
        panel = self.aco()
        editor = panel.problem_editor
        editor.problem.value = "assignment"
        editor.change_problem()
        editor.task_count.value, editor.resource_count.value = "3", "2"
        editor.resize_assignment()
        for (name, capacity), label, limit in zip(editor.resources, ("Equipo A", "Equipo B"), (3, 5)):
            name.value, capacity.value = label, str(limit)
        costs = ((1, 10), (2, 5), (7, 1))
        for (_, demand, fields), row in zip(editor.tasks, costs):
            demand.value = "2"
            for control, cost in zip(fields, row):
                control.value = str(cost)
        await panel.run_aco()
        self.assertTrue(panel.generations, panel.lbl_status.value)
        problem = panel.config.problem
        self.assertEqual(problem.costs, costs)
        self.assertEqual(problem.demands, (2, 2, 2))
        self.assertEqual(problem.capacities, (3, 5))
        solution, score, _ = best_solution(panel.generations)
        self.assertTrue(problem.is_feasible(solution))
        self.assertEqual(score, problem.evaluate(solution))
        self.assertIn("Equipo A", instance_summary(problem))
        self.assert_png(panel.solution_chart)

    def test_categorical_data_validation_and_resize_preserve_values(self):
        editor = self.aco().problem_editor
        editor.cities[1][0].value = editor.cities[0][0].value
        with self.assertRaisesRegex(ValueError, "no repetirse"):
            editor.build_problem()
        editor.problem.value = "assignment"
        editor.tasks[0][2][0].value = "7.5"
        editor.task_count.value, editor.resource_count.value = "3", "2"
        editor.resize_assignment()
        self.assertEqual(editor.tasks[0][2][0].value, "7.5")
        self.assertEqual(len(editor.tasks), 3)
        self.assertEqual(len(editor.tasks[0][2]), 2)
        editor.tasks[0][2][0].value = "nan"
        with self.assertRaisesRegex(ValueError, "finito"):
            editor.build_problem()
        editor.tasks[0][2][0].value = "-1"
        with self.assertRaisesRegex(ValueError, "positivos"):
            editor.build_problem()
        editor.task_count.value = "4"
        with self.assertRaisesRegex(ValueError, "Ajustar tabla"):
            editor.build_problem()

    def test_growing_and_shrinking_instances_keeps_names_and_start_consistent(self):
        editor = self.aco().problem_editor
        editor.cities[0][0].value = "C1"
        editor.add_city()
        self.assertNotEqual(editor.cities[-1][0].value, "C1")
        editor.start.value = "2"
        editor.remove_city(1)
        self.assertEqual(editor.start.value, "1")
        editor.remove_city(1)
        self.assertEqual(editor.start.value, "0")
        editor.build_problem().validate()
        editor.problem.value = "assignment"
        editor.task_count.value, editor.resource_count.value = "21", "6"
        editor.resize_assignment()
        problem = editor.build_problem()
        self.assertEqual((problem.size, problem.resources), (21, 6))
        self.assertEqual(len(set(problem.labels)), 21)
        self.assertEqual(len(set(problem.resource_labels)), 6)

    async def test_binary_problem_data_and_bits(self):
        panel = AISPanel(page(), AISEngine())
        panel.iterations.value, panel.population_size.value = "8", "12"
        panel.length.value = "7"
        await panel.apply()
        self.assertIsNotNone(panel.result, panel.message.value)
        self.assertEqual(len(panel.result.vector), 7)
        self.assertLessEqual(set(panel.result.vector), {0, 1})
        self.assertEqual(panel.result.value, sum(panel.result.vector))
        panel.problem.value = "knapsack"
        panel.change_problem()
        panel.weights.value, panel.values.value, panel.capacity.value = "2, 3, 4", "3, 4, 5", "5"
        await panel.apply()
        self.assertEqual(panel.last_problem.weights, (2, 3, 4))
        self.assertLessEqual(panel.result.weight, 5)
        self.assertEqual(panel.result.value, panel.last_problem.evaluate(panel.result.vector))
        self.assertIn("(2, 3, 4)", panel.configuration_text.value)
        panel.weights.value = "100, 200, 300"
        self.assertEqual(panel.last_problem.weights, (2, 3, 4))

    async def test_invalid_knapsack_data_is_rejected(self):
        panel = AISPanel(page(), AISEngine())
        panel.problem.value = "knapsack"
        panel.weights.value, panel.values.value = "1, 2, 3", "4, 5"
        await panel.apply()
        self.assertIsNone(panel.result)
        self.assertIn("un valor por cada peso", panel.message.value)
        self.assertFalse(panel.busy)


if __name__ == "__main__":
    unittest.main(verbosity=2)
