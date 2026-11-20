"""Configuración, ejecución y resultados de ACO para TSP y asignación."""
import asyncio
from threading import Event

import flet as ft

from models.aco_engine import ACOEngine, best_history, best_solution
from models.contracts import ACOConfig, ACO_PARAMETERS, validate_aco_generations
from models.results import make_record
from views.categorical_editor import CategoricalEditor, instance_summary
from views.charts import Chart, categorical_solution, plot
from views.theme import ERROR, MUTED, card, field
from views.run_support import ExportActions, HistoryBrowser, run_with_progress


class ACOPanel:
    """Conserva la configuración aplicada y ejecuta el motor sin bloquear Flet."""

    def __init__(self, page: ft.Page, engine: ACOEngine):
        self.page = page
        self.engine = engine
        self._running = False
        self._stop_event = Event()
        self.config: ACOConfig | None = None
        self.generations = []
        self.history = ()
        self.run_record = None
        self.build_ui()

    def _pause(self):
        """Solicita detener el motor al cambiar de algoritmo o pulsar Detener."""
        self.browser.pause()
        if self._running:
            self._stop_event.set()
            # Sigue ocupado hasta que el hilo termine: no se permite otro cálculo.
            self.btn_run.disabled = True
            self.btn_run.content = "Deteniendo…"
            self.lbl_status.value = "Deteniendo al completar la iteración actual…"

    def build_ui(self):
        self.problem_editor = CategoricalEditor(on_change=self._instance_changed, on_refresh=self.page.update)
        self.dd_problem = self.problem_editor.problem
        # Comparte etiquetas, ayuda y valores iniciales con la validación del motor.
        self.parameter_fields = {
            name: field(
                spec.label, str(spec.default), helper=spec.help, tooltip=spec.help, helper_max_lines=3,
                col={"xs": 12, "sm": 6},
            )
            for name, spec in ACO_PARAMETERS.items()
        }
        self.configuration = ft.ResponsiveRow([
            card("Datos del problema", "Edita la instancia antes de ejecutar. Los ejemplos originales se conservan.",
                 [self.problem_editor], 12),
            card("Parámetros de la colonia", "Variante Ant System con refuerzo elitista. La semilla permite repetir la búsqueda.",
                 [ft.ResponsiveRow(list(self.parameter_fields.values()), run_spacing=16)],
                 12),
        ], run_spacing=16)
        self.btn_run = ft.Button(
            "Iniciar optimización", icon=ft.Icons.PLAY_ARROW, on_click=self.run_aco,
        )
        self.btn_reset = ft.TextButton(
            "Reiniciar resultados", icon=ft.Icons.RESTART_ALT, on_click=self.reset,
        )
        self.lbl_status = ft.Text("Configura los parámetros e inicia.", color=MUTED)
        self.history_chart = Chart(height=300)
        self.solution_chart = Chart(height=340)
        self.browser = HistoryBrowser(self._show_iteration)
        self.timeline = self.browser.slider
        self.exporter = ExportActions(self.page.update)
        self.results_col = ft.Column(spacing=16, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        self.view = ft.Column([
            self.configuration,
            ft.Row([self.btn_run, self.btn_reset], wrap=True),
            self.lbl_status,
            self.exporter,
            self.results_col,
        ], spacing=16, expand=True, scroll=ft.ScrollMode.AUTO)

    def build(self, show_header=False) -> ft.Control:
        return self.view

    def _instance_changed(self):
        if hasattr(self, "lbl_status"):
            if self.config is not None and self.dd_problem.value != self.config.problem.kind:
                self.reset()
                return
            self.lbl_status.value, self.lbl_status.color = "Datos editados. Inicia una búsqueda para aplicarlos.", MUTED
            self.page.update()

    def _progressed(self, batch):
        self.generations.extend(batch)
        self.history = best_history(self.generations)
        self.browser.set_frames(self.generations, running=True)
        self._render_results(len(self.generations) - 1)
        self.lbl_status.value = f"Ejecutando ACO: iteración {self.generations[-1].index} de {self.config.generations}."
        self.page.update()

    def _show_iteration(self, index):
        self._render_results(index)
        self.page.update()

    def settings(self) -> ACOConfig:
        """Usa los datos del formulario y valida la instancia antes de ejecutar."""
        problem = self.problem_editor.build_problem()
        values = {}
        for name, spec in ACO_PARAMETERS.items():
            try:
                values[name] = spec.kind(self.parameter_fields[name].value)
            except (TypeError, ValueError):
                kind = "un entero" if spec.kind is int else "un número"
                raise ValueError(f"{spec.label} debe ser {kind}.") from None
        config = ACOConfig(problem=problem, **values)
        config.validate()
        return config

    async def run_aco(self, event=None):
        """Inicia una búsqueda o solicita detener la que aún está en curso."""
        if self._running:
            self._pause()
            self.page.update()
            return

        try:
            config = self.settings()
        except (ValueError, OSError) as error:
            self.lbl_status.value, self.lbl_status.color = str(error), ERROR
            self.page.update()
            return

        self._running = True
        self.browser.pause()
        self._stop_event.clear()
        self.run_record = None
        self.exporter.set_record(None)
        self.config, self.generations, self.history = config, [], ()
        self.configuration.disabled = self.btn_reset.disabled = True
        self.btn_run.content, self.btn_run.icon = "Detener", ft.Icons.STOP
        self.lbl_status.value = f"Explorando {config.problem.name}: hasta {config.generations} iteraciones…"
        self.lbl_status.color = MUTED
        self.results_col.controls.clear()
        self.page.update()

        try:
            generations = await run_with_progress(self.engine.run, config,
                                                  stop_event=self._stop_event, on_progress=self._progressed)
            if generations:
                validate_aco_generations(generations, config)
                self.generations = generations
                self.history = best_history(generations)
                self.run_record = make_record("aco", config, generations, self.engine.stop_reason)
                self.exporter.set_record(self.run_record)
            self.lbl_status.value = self.engine.stop_reason
        except asyncio.CancelledError:
            self._stop_event.set()
            raise
        except Exception as error:
            self.lbl_status.value = f"No se pudo ejecutar ACO: {error}"
            self.lbl_status.color = ERROR
        finally:
            self._running = False
            self.configuration.disabled = self.btn_reset.disabled = False
            self.btn_run.disabled = False
            self.btn_run.content, self.btn_run.icon = "Iniciar optimización", ft.Icons.PLAY_ARROW
            self.browser.set_frames(self.generations)
            if self.generations:
                self._render_results(len(self.generations) - 1)
            self.page.update()

    def reset(self, event=None):
        """Limpia el resultado y conserva los campos para una nueva ejecución."""
        if self._running:
            return
        self.config, self.generations, self.history = None, [], ()
        self.run_record = None
        self.browser.pause()
        self.browser.set_frames([])
        self.exporter.set_record(None)
        self.results_col.controls.clear()
        self.lbl_status.value, self.lbl_status.color = "Configura los parámetros e inicia.", MUTED
        self.page.update()

    def _render_results(self, index=None):
        """Dibuja el historial real y la mejor solución de las iteraciones completadas."""
        config = self.config
        problem = config.problem
        index = len(self.generations) - 1 if index is None else index
        solution, score, best_iteration = best_solution(self.generations[:index + 1])
        completed = self.generations[-1].index
        points = list(enumerate(self.history))
        self.history_chart.set_image(plot(points, [], xlabel="Iteración", best_dot=points[index]))
        self.solution_chart.set_image(categorical_solution(problem, solution))
        parameters = " · ".join(
            f"{spec.label}: {getattr(config, name)}" for name, spec in ACO_PARAMETERS.items()
        )
        self.results_col.controls = [
            self.browser,
            card("Mejor resultado", f"{problem.name} · Minimización · {completed} de {config.generations} iteraciones", [
                ft.Text(f"Costo mínimo encontrado: {score:.6g}", size=20),
                ft.Text(f"Viendo iteración {index}. Encontrado en la iteración {best_iteration}. " +
                        ("Búsqueda en curso…" if self._running else self.engine.stop_reason)),
                ft.Text(f"Vector: {solution}", selectable=True),
                ft.Text(problem.describe(solution), selectable=True),
                ft.Text("Solución factible." if problem.is_feasible(solution)
                        else "La solución excede capacidades y su costo incluye penalización."),
            ]),
            card("Configuración utilizada", problem.expression, [ft.Text(parameters, selectable=True),
                 ft.Text(instance_summary(problem), selectable=True)]),
            card("Convergencia", "Mejor costo acumulado desde la iteración 0.", [
                self.history_chart,
                ft.Text(", ".join(f"{value:.6g}" for value in self.history), size=12, selectable=True),
            ]),
            card("Solución", "Ruta cerrada para TSP o carga por recurso para asignación.", [self.solution_chart]),
        ]
