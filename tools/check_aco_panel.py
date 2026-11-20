"""Pruebas del panel ACO con controles Flet reales y motores en un hilo.

Ejecutar desde la raíz: python tools/check_aco_panel.py
No abre ventanas ni requiere una sesión Flet conectada.
"""
import asyncio
import os
from pathlib import Path
import struct
import sys
import tempfile
from threading import Event
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from models.aco_engine import ACOEngine, best_history, best_solution
from models.categorical import AssignmentProblem, TSPProblem, load_tsp
from models.contracts import validate_aco_generations
from views.aco_panel import ACOPanel
from views.application import OptimizationApp
from views.charts import plot


class RecordingEngine(ACOEngine):
    def __init__(self, error=None):
        super().__init__()
        self.calls = []
        self.error = error

    def run(self, config, should_stop=None, on_generation=None):
        self.calls.append(config)
        if self.error:
            raise self.error
        return super().run(config, should_stop, on_generation)


class WaitingEngine(RecordingEngine):
    """Mantiene el hilo abierto para comprobar respuesta, detención y exclusión."""

    def __init__(self):
        super().__init__()
        self.started = Event()
        self.release = Event()

    def run(self, config, should_stop=None, on_generation=None):
        self.started.set()
        if not self.release.wait(5):
            raise TimeoutError("La prueba no liberó el motor.")
        return super().run(config, should_stop, on_generation)


class ACOPanelChecks(unittest.IsolatedAsyncioTestCase):
    def panel(self, engine=None):
        panel = ACOPanel(SimpleNamespace(update=lambda: None), engine or RecordingEngine())
        panel.parameter_fields["ants"].value = "5"
        panel.parameter_fields["generations"].value = "6"
        panel.parameter_fields["patience"].value = "0"
        return panel

    def assert_ready(self, panel):
        self.assertFalse(panel._running)
        self.assertFalse(panel.configuration.disabled)
        self.assertFalse(panel.btn_run.disabled)
        self.assertFalse(panel.btn_reset.disabled)
        self.assertEqual(panel.btn_run.content, "Iniciar optimización")

    def assert_chart(self, chart):
        png = chart.raster.src
        self.assertTrue(png.startswith(b"\x89PNG\r\n\x1a\n"))
        width, height = struct.unpack(">II", png[16:24])
        self.assertGreater(width, 100)
        self.assertGreater(height, 100)

    async def test_both_examples_load_outside_the_project_directory(self):
        panel = self.panel()
        original_directory = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            try:
                os.chdir(directory)
                for key, problem_type in (("tsp", TSPProblem), ("assignment", AssignmentProblem)):
                    panel.dd_problem.value = key
                    config = panel.settings()
                    self.assertIsInstance(config.problem, problem_type)
                    self.assertEqual(config.seed, 42)
                    await panel.run_aco()
                    self.assertTrue(panel.generations, panel.lbl_status.value)
            finally:
                os.chdir(original_directory)

    async def test_invalid_fields_never_start_the_engine(self):
        for name, value in (("ants", "texto"), ("ants", "1"), ("generations", "0"),
                            ("alpha", "nan"), ("rho", "1"), ("q", "inf"),
                            ("seed", ""), ("seed", "-1"), ("patience", "2.5")):
            with self.subTest(name=name, value=value):
                panel = self.panel()
                panel.parameter_fields[name].value = value
                await panel.run_aco()
                self.assertEqual(panel.engine.calls, [])
                self.assertIn(panel.parameter_fields[name].label, panel.lbl_status.value)
                self.assert_ready(panel)

    async def test_malformed_json_is_reported_without_locking_the_panel(self):
        panel = self.panel()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            path.write_text("{bad json", encoding="utf-8")
            with patch("views.categorical_editor.get_problem", side_effect=lambda key: load_tsp(path)):
                panel.problem_editor.load_example()
        self.assertIn("JSON inválido", panel.problem_editor.message.value)
        self.assertEqual(panel.engine.calls, [])
        self.assert_ready(panel)

    async def test_real_results_are_reproducible_and_render_both_problem_types(self):
        panel = self.panel()
        for key in ("tsp", "assignment"):
            with self.subTest(problem=key):
                panel.dd_problem.value = key
                with patch("views.aco_panel.plot", wraps=plot) as draw_history:
                    await panel.run_aco()
                self.assertTrue(panel.generations, panel.lbl_status.value)
                validate_aco_generations(panel.generations, panel.config)
                self.assertEqual(panel.history, best_history(panel.generations))
                self.assertEqual(draw_history.call_args.args[0], list(enumerate(panel.history)))
                self.assertEqual(panel.history[-1], best_solution(panel.generations)[1])
                self.assert_chart(panel.history_chart)
                self.assert_chart(panel.solution_chart)
                self.assert_ready(panel)
                first_run = panel.generations
                await panel.run_aco()
                self.assertEqual(panel.generations, first_run)

    async def test_engine_failure_restores_controls_and_allows_retry(self):
        engine = RecordingEngine(error=RuntimeError("fallo de prueba"))
        panel = self.panel(engine)
        await panel.run_aco()
        self.assertIn("fallo de prueba", panel.lbl_status.value)
        self.assert_ready(panel)
        engine.error = None
        await panel.run_aco()
        self.assertTrue(panel.generations, panel.lbl_status.value)

    async def test_stop_keeps_the_worker_exclusive_until_it_finishes(self):
        engine = WaitingEngine()
        panel = self.panel(engine)
        task = asyncio.create_task(panel.run_aco())
        try:
            self.assertTrue(await asyncio.to_thread(engine.started.wait, 2))
            # Este código puede ejecutarse mientras el motor está esperando en su hilo.
            self.assertTrue(panel._running)
            await panel.run_aco()
            self.assertTrue(panel._stop_event.is_set())
            self.assertTrue(panel._running)
            self.assertTrue(panel.btn_run.disabled)
            panel.reset()
            self.assertIsNotNone(panel.config)
        finally:
            engine.release.set()
            await asyncio.wait_for(task, 5)
        self.assertEqual(len(engine.calls), 1)
        self.assertIn("Detenido por el usuario", panel.lbl_status.value)
        self.assertEqual(panel.generations, [])
        self.assert_ready(panel)

    async def test_changing_algorithm_requests_stop(self):
        app = OptimizationApp(SimpleNamespace(update=lambda: None))
        panel = app.panels["aco"]
        panel.engine = engine = WaitingEngine()
        app.router.go("aco")
        task = asyncio.create_task(panel.run_aco())
        try:
            self.assertTrue(await asyncio.to_thread(engine.started.wait, 2))
            app.router.go("genetic")
            self.assertTrue(panel._stop_event.is_set())
        finally:
            engine.release.set()
            await asyncio.wait_for(task, 5)
        self.assert_ready(panel)

    async def test_reset_clears_results_and_preserves_parameters(self):
        panel = self.panel()
        await panel.run_aco()
        self.assertTrue(panel.results_col.controls, panel.lbl_status.value)
        panel.reset()
        self.assertEqual(panel.results_col.controls, [])
        self.assertEqual(panel.history, ())
        self.assertIsNone(panel.config)
        self.assertEqual(panel.parameter_fields["seed"].value, "42")
        self.assertEqual(panel.parameter_fields["generations"].value, "6")


if __name__ == "__main__":
    unittest.main(verbosity=2)
