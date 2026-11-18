"""Configuración y resultados del motor de selección clonal."""
import asyncio

import flet as ft

from models.ais_engine import AISConfig, AISEngine, AISResult
from models.ais_problems import DEFAULT_ONEMAX_LENGTH, Knapsack, OneMax, load_knapsack_example
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
        self.length = field("Longitud del vector", str(DEFAULT_ONEMAX_LENGTH))
        self.weights = field("Pesos", multiline=True, min_lines=1, max_lines=4)
        self.values = field("Valores", multiline=True, min_lines=1, max_lines=4)
        self.capacity = field("Capacidad")
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
        self.population_size = field("Tamaño de población", str(defaults.population_size))
        self.iterations = field("Iteraciones", str(defaults.iterations))
        self.max_clones = field("Máximo de clones por candidato", str(defaults.max_clones))
        self.seed = field("Semilla (opcional)", str(defaults.seed))

        self.message = ft.Text(color=ERROR, visible=False)
        self.summary = ft.Text(weight=ft.FontWeight.W_600)
        self.vector_text = ft.Text(selectable=True)
        self.history_text = ft.Text(selectable=True)
        self.history_chart = Chart(height=300)
        settings_cards = ft.ResponsiveRow([
            card("Problema", "Elige y edita la instancia que quieres optimizar.",
                 [self.problem, self.length, self.knapsack_fields], {"xs": 12, "md": 7}),
            card("Parámetros", "Una semilla fija permite repetir la ejecución.",
                 [self.population_size, self.iterations, self.max_clones, self.seed], {"xs": 12, "md": 5}),
        ], spacing=16, run_spacing=16)
        self.configuration_view = ft.Column([settings_cards], scroll=ft.ScrollMode.AUTO, expand=True)
        results_view = ft.Column([
            card("Mejor solución", "Vector binario encontrado por selección clonal.", [self.summary, self.vector_text]),
            card("Historial", "Mejor valor acumulado desde la población inicial (iteración 0).",
                 [self.history_chart, self.history_text]),
        ], spacing=16, scroll=ft.ScrollMode.AUTO, expand=True,
           horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

        self.router = ViewRouter(
            {"config": self.configuration_view, "results": results_view},
            initial="config",
            guards={"results": lambda: self.result is not None},
            on_change=self.change_stage,
        )
        self.router.outlet.expand = True
        self.submenu = Submenu([
            SubmenuItem("config", "Configuración", ft.Icons.TUNE),
            SubmenuItem("results", "Simulación / Resultados", ft.Icons.INSIGHTS),
        ], on_navigate=self.router.go, on_back=self.router.back)
        self.submenu.select("config")
        self.submenu.set_enabled("results", False)
        self.apply_button = ft.Button("Ver resultados", icon=ft.Icons.ARROW_FORWARD, on_click=self.apply)
        self.edit_button = ft.TextButton("Editar configuración", on_click=lambda e: self.router.go("config"), visible=False)
        self.body = ft.Column([self.message, self.router.outlet], spacing=16, expand=True,
                              horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    def build(self, show_header: bool = True) -> ft.Column:
        header = [ft.Text("AIS · Selección clonal", size=20, color=ACCENT)] if show_header else []
        actions = ft.Container(content=ft.Row([self.apply_button, self.edit_button]), padding=12,
                               bgcolor=SOFT, border_radius=12)
        return ft.Column([*header, self.submenu, self.body, actions], expand=True, spacing=12,
                         horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    def change_problem(self, event=None) -> None:
        knapsack = self.problem.value == "knapsack"
        self.length.visible = not knapsack
        self.knapsack_fields.visible = knapsack
        self._show_message(self.example_error if knapsack else "")
        self.page.update()

    def change_stage(self, name: str) -> None:
        self._pause()
        self.submenu.select(name, self.router.can_go_back)
        self.apply_button.visible = name == "config"
        self.edit_button.visible = name == "results"
        self._show_message("")
        self.page.update()

    def _pause(self) -> None:
        """Invalida la ejecución pendiente si el usuario cambia de panel o de etapa."""
        self.revision += 1

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
        else:
            problem = OneMax(_integer(self.length.value, "La longitud"))
        seed = (self.seed.value or "").strip()
        config = AISConfig(
            population_size=_integer(self.population_size.value, "El tamaño de población"),
            iterations=_integer(self.iterations.value, "El número de iteraciones"),
            max_clones=_integer(self.max_clones.value, "El máximo de clones"),
            seed=_integer(seed, "La semilla") if seed else None,
        )
        return problem, config

    async def apply(self, event=None) -> None:
        """Ejecuta AIS fuera del bucle de Flet y abre Resultados para esta ejecución."""
        if self.busy:
            return
        try:
            problem, config = self.settings()
        except ValueError as error:
            self._show_message(str(error))
            self.page.update()
            return

        token = self.revision
        self.busy = self.apply_button.disabled = self.configuration_view.disabled = True
        self.apply_button.content = "Calculando…"
        self._show_message("Ejecutando selección clonal…", MUTED)
        self.page.update()
        try:
            result = await asyncio.to_thread(self.engine.run, problem, config)
            if token != self.revision:
                self._show_message("")
                return
            self._render_result(problem, result)
            self.result = result
            self.submenu.set_enabled("results", True)
            self.router.go("results")
        except Exception as error:
            if token == self.revision:
                self._show_message(f"No se pudieron preparar los resultados. {error}")
        finally:
            self.busy = self.apply_button.disabled = self.configuration_view.disabled = False
            self.apply_button.content = "Ver resultados"
            self.page.update()

    def _render_result(self, problem: OneMax | Knapsack, result: AISResult) -> None:
        points = list(enumerate(result.history))
        self.history_chart.set_image(plot(points, [], xlabel="Iteración", best_dot=points[-1]))
        if isinstance(problem, Knapsack):
            self.summary.value = f"Mochila 0/1 · Valor {result.value} · Peso {result.weight} de {problem.capacity}"
        else:
            self.summary.value = f"OneMax · {result.value} unos de {problem.length} bits"
        self.vector_text.value = str(list(result.vector))
        self.history_text.value = str(list(result.history))
