"""Configuración y resultados del motor de selección clonal."""
import asyncio
from threading import Event

import flet as ft

from models.ais_engine import AISConfig, AISEngine, AISResult
from models.ais_problems import DEFAULT_ONEMAX_LENGTH, Knapsack, OneMax, load_knapsack_example
from models.results import best_individual, make_record
from views.run_support import ExportActions, HistoryBrowser, run_with_progress
from views.charts import Chart, plot
from views.router import ViewRouter
from views.submenu import Submenu, SubmenuItem
from views.theme import ACCENT, ERROR, MUTED, SOFT, card, field


def _integer(text: str | None, name: str) -> int:
    try:
        return int(text)
    except (ValueError, TypeError) as error:
        raise ValueError(f"{name} debe ser un entero.") from error


def _integer_list(text: str | None, name: str) -> tuple[int, ...]:
    try:
        return tuple(int(item) for item in (text or "").split(","))
    except ValueError as error:
        raise ValueError(f"Escribe números enteros separados por comas en {name}.") from error


class AISPanel:
    """Mantiene un motor, su formulario y el último resultado mientras se navega."""

    def __init__(self, page: ft.Page, engine: AISEngine):
        self.page = page
        self.engine = engine
        self.result: AISResult | None = None
        self.last_problem = self.last_config = None
        self.generations, self.history, self.run_record = [], [], None
        self._stop_event = Event()
        self.busy = False
        self.revision = 0
        self.example_error = ""
        defaults = AISConfig()

        self.problem = ft.Dropdown(
            label="Problema", value="onemax",
            options=[ft.DropdownOption(key="onemax", text="OneMax"),
                     ft.DropdownOption(key="knapsack", text="Mochila 0/1")],
            on_select=self.change_problem,
        )
        self.length = field("Longitud del vector", str(DEFAULT_ONEMAX_LENGTH), helper="Número entero positivo de bits (0 o 1).")
        self.weights = field("Pesos", helper="Enteros positivos, separados por comas.", multiline=True, min_lines=1, max_lines=4)
        self.values = field("Valores", helper="Un entero no negativo por cada peso.", multiline=True, min_lines=1, max_lines=4)
        self.capacity = field("Capacidad", helper="Peso máximo permitido; entero no negativo.")
        self.definition = ft.Text(
            "Representación: vector de bits (0 o 1). OneMax maximiza la cantidad de unos: f(x)=Σ xᵢ. Todos los vectores de la longitud elegida son válidos.",
            color=MUTED,
        )
        try:
            example = load_knapsack_example()
            self.weights.value = ", ".join(map(str, example.weights))
            self.values.value = ", ".join(map(str, example.values))
            self.capacity.value = str(example.capacity)
        except (OSError, ValueError):
            self.example_error = "No se pudo cargar el ejemplo de mochila. Puedes ingresar los datos manualmente."

        self.knapsack_fields = ft.Column([
            ft.Text("Separa los números por comas. Cada peso y su valor van en la misma posición.", color=MUTED),
            self.weights, self.values, self.capacity,
        ], visible=False)
        self.population_size = field("Número de anticuerpos", str(defaults.population_size), helper="Cantidad de soluciones; entero mayor o igual a 2.")
        self.iterations = field("Número de iteraciones", str(defaults.iterations), helper="Número máximo de ciclos de selección clonal; entero positivo.")
        self.max_clones = field("Máximo de clones por anticuerpo", str(defaults.max_clones), helper="Base de clones del mejor anticuerpo; disminuye según su rango.")
        self.cloning_rate = field("Tasa de clonación", "1", helper="0–1. Fracción de los clones base; 0 desactiva la clonación.")
        self.mutation_rate = field("Tasa de mutación", "", hint_text="Automática: 1 / longitud",
                                   helper="0–1; vacío usa 1/longitud. La hipermutación aumenta hasta 4× según afinidad.", helper_max_lines=3)
        self.selection_fraction = field("Selección clonal", "0.25", helper="Fracción de mejores anticuerpos que se clonan; mayor que 0 y hasta 1.")
        self.diversity_fraction = field("Fracción de renovación", "0.1", helper="0–menor que 1. Reemplaza esa fracción por anticuerpos aleatorios.")
        self.seed = field("Semilla (opcional)", str(defaults.seed), helper="Entero para repetir la ejecución; vacío genera otra secuencia.")

        self.message = ft.Text(color=ERROR, visible=False)
        self.summary = ft.Text(weight=ft.FontWeight.W_600)
        self.vector_text = ft.Text(selectable=True)
        self.history_text = ft.Text(selectable=True)
        self.configuration_text = ft.Text(selectable=True)
        self.history_chart = Chart(height=300)
        self.browser = HistoryBrowser(self._render_generation)
        self.timeline = self.browser.slider
        self.exporter = ExportActions(self.page.update)
        settings_cards = ft.ResponsiveRow([
            card("Problema", "Elige y edita la instancia que quieres optimizar.",
                 [self.problem, self.definition, self.length, self.knapsack_fields], {"xs": 12, "md": 7}),
            card("Parámetros", "Una semilla fija permite repetir la ejecución.",
                 [self.population_size, self.cloning_rate, self.mutation_rate, self.selection_fraction,
                  self.max_clones, self.diversity_fraction, self.iterations, self.seed], {"xs": 12, "md": 5}),
        ], spacing=16, run_spacing=16)
        self.configuration_view = ft.Column([settings_cards], scroll=ft.ScrollMode.AUTO, expand=True)
        results_view = ft.Column([
            self.browser, self.exporter,
            card("Mejor solución", "Vector binario encontrado por selección clonal.", [self.summary, self.vector_text]),
            card("Configuración utilizada", "Datos del problema y parámetros de la ejecución mostrada.", [self.configuration_text]),
            card("Historial", "Mejor valor acumulado desde la población inicial (iteración 0).",
                 [self.history_chart, self.history_text]),
        ], spacing=16, scroll=ft.ScrollMode.AUTO, expand=True,
           horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

        self.router = ViewRouter(
            {"config": self.configuration_view, "results": results_view},
            initial="config",
            guards={"results": lambda: self.result is not None or self.busy},
            on_change=self.change_stage,
        )
        self.router.outlet.expand = True
        self.submenu = Submenu([
            SubmenuItem("config", "Configuración", ft.Icons.TUNE),
            SubmenuItem("results", "Simulación / Resultados", ft.Icons.INSIGHTS),
        ], on_navigate=self.router.go, on_back=self.router.back)
        self.submenu.select("config")
        self.submenu.set_enabled("results", False)
        self.apply_button = ft.Button("Ejecutar", icon=ft.Icons.PLAY_ARROW, on_click=self.apply)
        self.stop_button = ft.TextButton("Detener", icon=ft.Icons.STOP, on_click=self.request_stop, visible=False)
        self.reset_button = ft.TextButton("Reiniciar", icon=ft.Icons.RESTART_ALT, on_click=self.reset)
        self.edit_button = ft.TextButton("Editar configuración", on_click=lambda e: self.router.go("config"), visible=False)
        self.body = ft.Column([self.message, self.router.outlet], spacing=16, expand=True,
                              horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    def build(self, show_header: bool = True) -> ft.Column:
        header = [ft.Text("AIS · Selección clonal", size=20, color=ACCENT)] if show_header else []
        actions = ft.Container(content=ft.Row([self.apply_button, self.stop_button, self.reset_button, self.edit_button], wrap=True), padding=12,
                               bgcolor=SOFT, border_radius=12)
        return ft.Column([*header, self.submenu, self.body, actions], expand=True, spacing=12,
                         horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    def change_problem(self, event=None) -> None:
        knapsack = self.problem.value == "knapsack"
        self.length.visible = not knapsack
        self.knapsack_fields.visible = knapsack
        self.definition.value = (
            "Representación: un bit por objeto; 1 significa incluirlo y 0 excluirlo. Se maximiza Σ valorᵢ·xᵢ, sujeto a Σ pesoᵢ·xᵢ ≤ capacidad."
            if knapsack else
            "Representación: vector de bits (0 o 1). OneMax maximiza la cantidad de unos: f(x)=Σ xᵢ. Todos los vectores de la longitud elegida son válidos."
        )
        self._show_message(self.example_error if knapsack else "")
        self.page.update()

    def change_stage(self, name: str) -> None:
        self.browser.pause()
        if name == "config" and self.busy:
            self.request_stop()
        self.submenu.select(name, self.router.can_go_back)
        self.apply_button.visible = name == "config"
        self.edit_button.visible = name == "results"
        self._show_message("")
        self.page.update()

    def _pause(self) -> None:
        """Invalida la ejecución pendiente si el usuario cambia de panel o de etapa."""
        self.revision += 1
        self.browser.pause()
        if self.busy:
            self.request_stop()

    def request_stop(self, event=None):
        if self.busy:
            self._stop_event.set()
            self.stop_button.disabled = True
            self._show_message("Deteniendo al completar el ciclo actual…", MUTED)
            self.page.update()

    def _show_message(self, text: str, color: str = ERROR) -> None:
        self.message.value = text
        self.message.color = color
        self.message.visible = bool(text)

    def settings(self) -> tuple[OneMax | Knapsack, AISConfig]:
        """Lee los valores actuales. Los modelos validan longitudes y restricciones."""
        if self.problem.value == "knapsack":
            problem = Knapsack(
                _integer_list(self.weights.value, "Pesos"),
                _integer_list(self.values.value, "Valores"),
                _integer(self.capacity.value, "La capacidad"),
            )
        elif self.problem.value == "onemax":
            problem = OneMax(_integer(self.length.value, "La longitud"))
        else:
            raise ValueError("Selecciona OneMax o Mochila 0/1.")
        seed = (self.seed.value or "").strip()
        config = AISConfig(
            population_size=_integer(self.population_size.value, "El número de anticuerpos"),
            iterations=_integer(self.iterations.value, "El número de iteraciones"),
            max_clones=_integer(self.max_clones.value, "El máximo de clones"),
            seed=_integer(seed, "La semilla") if seed else None,
            cloning_rate=self._rate(self.cloning_rate.value, "Tasa de clonación"),
            mutation_rate=self._rate(self.mutation_rate.value, "Tasa de mutación", optional=True),
            selection_fraction=self._rate(self.selection_fraction.value, "Selección clonal"),
            diversity_fraction=self._rate(self.diversity_fraction.value, "Fracción de renovación"),
        )
        return problem, config

    @staticmethod
    def _rate(text, label, optional=False):
        if optional and not (text or "").strip():
            return None
        try:
            return float(text)
        except (TypeError, ValueError):
            raise ValueError(f"{label} debe ser un número entre 0 y 1.") from None

    def _progressed(self, batch):
        self.generations.extend(batch)
        self.history = [max(g.scores) for g in self.generations]
        self.browser.set_frames(self.generations, running=True)
        self._render_generation(len(self.generations) - 1)
        self._show_message(f"Ejecutando AIS: iteración {self.generations[-1].index} de {self.last_config.iterations}.", MUTED)
        self.page.update()

    async def apply(self, event=None) -> None:
        if self.busy:
            return
        try:
            problem, config = self.settings()
        except ValueError as error:
            self._show_message(str(error))
            self.page.update()
            return
        self.browser.pause()
        self._stop_event.clear()
        self.last_problem, self.last_config = problem, config
        self.result, self.generations, self.history, self.run_record = None, [], [], None
        self.summary.value = self.vector_text.value = self.history_text.value = self.configuration_text.value = ""
        self.history_chart.clear()
        self.exporter.set_record(None)
        self.busy = self.apply_button.disabled = self.configuration_view.disabled = True
        self.reset_button.disabled = self.edit_button.disabled = True
        self.stop_button.visible, self.stop_button.disabled = True, False
        self._show_message("Inicializando AIS…", MUTED)
        self.submenu.set_enabled("results", True)
        try:
            self.router.go("results")
            self.page.update()
            result = await run_with_progress(self.engine.run, problem, config,
                                             stop_event=self._stop_event, on_progress=self._progressed)
            self.result = result
            self._render_result(problem, result, config)
            self.run_record = make_record("ais", config, self.generations, result.stop_reason, problem)
            self.exporter.set_record(self.run_record)
            self._show_message(result.stop_reason, MUTED)
        except Exception as error:
            self._show_message(f"No se pudieron preparar los resultados. {error}")
        finally:
            self.busy = self.apply_button.disabled = self.configuration_view.disabled = False
            self.reset_button.disabled = self.edit_button.disabled = False
            self.stop_button.visible, self.stop_button.disabled = False, False
            self.browser.set_frames(self.generations, self.browser.index, running=False)
            self.page.update()

    def _render_result(self, problem, result, config):
        self.last_problem, self.last_config = problem, config
        self.generations = list(result.generations)
        self.history = list(result.history)
        self.browser.set_frames(self.generations)
        self._render_generation(len(self.generations) - 1)

    def _render_generation(self, index):
        if not self.generations:
            return
        problem, config = self.last_problem, self.last_config
        best = best_individual(self.generations[:index + 1], True)
        self.displayed_best = best
        points = list(enumerate(self.history))
        self.history_chart.set_image(plot(points, [], xlabel="Iteración", best_dot=points[index]))
        details = (f"Mochila 0/1 · Valor {best.fitness} · Peso {problem.weight(best.solution)} de {problem.capacity}"
                   if isinstance(problem, Knapsack) else f"OneMax · {best.fitness} unos de {problem.length} bits")
        self.summary.value = f"Iteración {index} / {config.iterations} · {details}"
        self.vector_text.value = str(list(best.solution))
        self.history_text.value = str(list(self.history))
        data = (f"Pesos: {problem.weights}\nValores: {problem.values}\nCapacidad: {problem.capacity}"
                if isinstance(problem, Knapsack) else f"Longitud: {problem.length}")
        mutation = 1 / problem.length if config.mutation_rate is None else config.mutation_rate
        self.configuration_text.value = (
            f"Maximización · {config.iterations} iteraciones · {config.population_size} anticuerpos · Semilla: {config.seed}\n"
            f"Tasa de clonación: {config.cloning_rate:g} · Tasa base de mutación: {mutation:g} · "
            f"Selección clonal: {config.selection_fraction:g} · Máximo de clones: {config.max_clones} · "
            f"Renovación: {config.diversity_fraction:g}\n{data}"
        )
        self.page.update()

    def reset(self, event=None):
        if self.busy:
            return
        self.browser.pause()
        self.result, self.last_problem, self.last_config = None, None, None
        self.generations, self.history, self.run_record = [], [], None
        self.browser.set_frames([])
        self.exporter.set_record(None)
        self.summary.value = self.vector_text.value = self.history_text.value = self.configuration_text.value = ""
        self.router.go("config")
        self.submenu.set_enabled("results", False)
        self._show_message("Listo para una nueva ejecución.", MUTED)
        self.page.update()
