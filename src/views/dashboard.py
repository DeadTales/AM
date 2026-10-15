"""Vistas de configuración y resultados, independientes del motor de evolución."""
import asyncio
import flet as ft
from models.contracts import AlgorithmConfig, validate_generations, validate_population
from models.genetic_engine import GeneticEngine
from models.demo_engine import DemoEngine, initial_population
from models.objectives import FIXED_DIMENSIONS, FUNCTIONS, get_objective
from views.charts import Chart, heatmap, plot, surface3d
from views.population_editor import PopulationEditor
from views.menu import Menu, MenuItem
from views.router import ViewRouter
from views.theme import ACCENT, BORDER, ERROR, MUTED, SOFT, TEXT, card, field


class Dashboard:
    """Coordina configuración, ejecución del motor y navegación por resultados."""

    def __init__(self, page: ft.Page, engine: GeneticEngine | DemoEngine | None = None):
        """page aloja controles; engine ejecuta run(config), por defecto GeneticEngine."""
        self.page = page
        self.engine = engine if engine is not None else GeneticEngine()
        self.index, self.total = 0, 40
        self.playing, self.busy, self.revision = False, False, 0
        self.snapshots = []
        self.history = []
        self.config = None
        self.is_demo = isinstance(self.engine, DemoEngine)
        self.function = ft.Dropdown(label="Función objetivo", value="sine_1d", options=[ft.DropdownOption(key=k, text=name) for k, name in FUNCTIONS.items()], on_select=self.change_objective)
        self.dimensions = ft.Dropdown(label="Variables por individuo", value="1", disabled=True, options=[ft.DropdownOption(key="1", text="Una variable · x"), ft.DropdownOption(key="2", text="Dos variables · x, y")], on_select=self.change_objective)
        self.size = field("Cantidad para generar", "20")
        self.generations = field("Generaciones", "40", on_change=self.invalidate)
        self.selection = ft.Dropdown(label="Selección", value="torneo", options=[ft.DropdownOption(key=k, text=k.capitalize()) for k in ("torneo", "ruleta", "elitista")], on_select=self.invalidate)
        self.crossover_label = ft.Text("Cruza · 80 %", color=TEXT, size=14)
        self.crossover = ft.Slider(min=0, max=100, divisions=100, value=80, label="{value}%", active_color=ACCENT, on_change=self.change_crossover)
        self.mutation_label = ft.Text("Mutación · 5 %", color=TEXT, size=14)
        self.mutation = ft.Slider(min=0, max=100, divisions=100, value=5, label="{value}%", active_color=ACCENT, on_change=self.change_mutation)
        self.message = ft.Text("Ajusta los parámetros y la población; después pulsa Ver resultados.", size=13, color=MUTED)
        self.formula = ft.Text(color=MUTED, size=12)
        initial_obj = get_objective("sine_1d", 1)
        self.editor = PopulationEditor(dimensions=initial_obj.dimensions, labels=initial_obj.labels, bounds=initial_obj.bounds, on_change=self.population_changed, on_refresh=self.page.update)
        self.metrics = ft.ResponsiveRow(spacing=14, run_spacing=12)
        self.function_chart = Chart(height=420)
        self.chart_mode = ft.Dropdown(label="Visualización", value="heatmap", options=[ft.DropdownOption(key="surface", text="Superficie 3D"), ft.DropdownOption(key="heatmap", text="Mapa de calor")], on_select=self.change_chart)
        self.azimuth = ft.Slider(min=-180, max=180, divisions=72, value=-55, label="Giro: {value}°", active_color=ACCENT, on_change_end=self.change_chart)
        self.elevation = ft.Slider(min=5, max=85, divisions=16, value=30, label="Inclinación: {value}°", active_color=ACCENT, on_change_end=self.change_chart)
        self.camera_controls = ft.ResponsiveRow([ft.Column([ft.Text("Giro horizontal", size=12, color=MUTED), self.azimuth], col={"xs":12,"sm":6}, spacing=0), ft.Column([ft.Text("Inclinación", size=12, color=MUTED), self.elevation], col={"xs":12,"sm":6}, spacing=0)], visible=False)
        self.chart_controls = ft.Column([self.chart_mode, self.camera_controls], visible=False)
        self.history_chart = Chart(height=300)
        self.table = ft.ListView(height=330, spacing=8)
        self.timeline = ft.Slider(min=0, max=40, divisions=40, value=0, label="Generación {value}", active_color=ACCENT, on_change=self.seek)
        self.play_button = ft.Button("Reproducir", icon=ft.Icons.PLAY_ARROW, on_click=self.toggle_play)
        self.progress = ft.ProgressBar(value=0, color=ACCENT, bgcolor=SOFT)
        self.apply_button = ft.Button("Ver resultados", icon=ft.Icons.ARROW_FORWARD, on_click=self.apply)
        self.edit_button = ft.Button("Editar configuración", icon=ft.Icons.TUNE, on_click=lambda e: self.show_view("config"), visible=False)
        self.action_hint = ft.Text("Se usarán los individuos guardados en la lista.", size=12, color=MUTED, expand=True)
        self.actions = ft.Container(content=ft.Row([self.action_hint, self.apply_button, self.edit_button], spacing=12), padding=12, bgcolor=SOFT, border_radius=12)
        self.result_summary = ft.Text(size=13, color=MUTED)
        self.configuration_view = ft.Column()
        self.results_view = ft.Column(visible=False)
        self.router = ViewRouter({"config": self.configuration_view, "results": self.results_view}, initial="config", guards={"results": lambda: bool(self.snapshots)}, on_change=self._on_route_change)
        self.menu = Menu([MenuItem("config", "Configuración", ft.Icons.TUNE), MenuItem("results", "Resultados", ft.Icons.INSIGHTS)], on_navigate=self.show_view, on_back=self.router.back)
        self.menu.set_enabled("results", False)
        self.menu.select("config")
        self._prepare_population()

    def _sync_dimension_control(self):
        """Ajusta y bloquea/desbloquea el selector de variables según la función elegida."""
        fixed = FIXED_DIMENSIONS.get(self.function.value)
        if fixed is not None:
            self.dimensions.value = str(fixed)
            self.dimensions.disabled = True
        else:
            self.dimensions.disabled = False

    def _best_index(self, scores: tuple[float, ...], maximize: bool) -> int:
        """Devuelve el índice del mejor individuo según si se maximiza o minimiza."""
        return max(range(len(scores)), key=lambda i: scores[i]) if maximize else min(range(len(scores)), key=lambda i: scores[i])

    def _prepare_population(self):
        """Carga población inicial de ejemplo y fórmula sin ejecutar el motor."""
        self._sync_dimension_control()
        objective = get_objective(self.function.value, int(self.dimensions.value))
        self.editor.set_schema(objective.dimensions, objective.labels, objective.bounds, notify=False)
        self.editor.set_individuals(initial_population(int(self.size.value), objective), notify=False)
        self.formula.value = objective.expression+"\n"+" · ".join(f"{label} ∈ [{low:g}, {high:g}]" for label, (low, high) in zip(objective.labels, objective.bounds))

    def build(self) -> ft.Column:
        """Construye dos vistas para separar preparación y análisis visual."""
        self.configuration_view.controls = [ft.ResponsiveRow([
            card("Parámetros", "Define cómo se evaluará tu población.", [self.function, self.dimensions, self.formula, ft.Divider(color=BORDER), self.generations, self.selection, ft.Column([self.crossover_label, self.crossover], spacing=0), ft.Column([self.mutation_label, self.mutation], spacing=0)], {"xs":12, "lg":4}),
            card("Población inicial", "Cada fila es un individuo. Puedes agregarlo, editarlo o eliminarlo.", [ft.Row([self.size, ft.TextButton("Generar población", icon=ft.Icons.REFRESH, on_click=self.configure)], wrap=True), self.editor], {"xs":12, "lg":8}),
        ], spacing=20, run_spacing=20)]
        self.results_view.controls = [self.result_summary, self.metrics, ft.ResponsiveRow([
            card("Función y población", "Curva 1D, Superficie 3D o Mapa de calor 2D · Zoom y arrastre", [self.chart_controls, self.function_chart], {"xs":12, "lg":8}),
            card("Individuos", "Valores de la generación actual; el mejor aparece destacado.", [self.table], {"xs":12, "lg":4}),
        ], spacing=20, run_spacing=20), card("Evolución del fitness (Convergencia)", "Eje horizontal: generación · Eje vertical: mejor evaluación de la generación", [ft.Row([ft.IconButton(icon=ft.Icons.SKIP_PREVIOUS, tooltip="Volver a generación 0", on_click=self.reset), ft.IconButton(icon=ft.Icons.CHEVRON_LEFT, tooltip="Generación anterior", on_click=lambda e: self.step(-1)), self.play_button, ft.IconButton(icon=ft.Icons.CHEVRON_RIGHT, tooltip="Siguiente generación", on_click=lambda e: self.step(1))], wrap=True), self.timeline, self.progress, self.history_chart])]
        self.body = ft.Column([self.message, self.router.outlet], spacing=16, scroll=ft.ScrollMode.AUTO, expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        return ft.Column([ft.Row([ft.Icon(ft.Icons.SCIENCE_OUTLINED, color=ACCENT, size=26), ft.Text("Evolución Lab", size=24, weight=ft.FontWeight.W_600, color=TEXT), ft.Text("Demostración" if self.is_demo else "Motor Genético Conectado", color=ACCENT, size=12)], spacing=12), self.menu, self.body, self.actions], spacing=12, expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    def show_view(self, name: str):
        """Solicita navegación al router conservando edición y resultados existentes."""
        return self.router.go(name)

    def _on_route_change(self, name: str):
        """Pausa reproducción y sincroniza el menú cuando el router cambia de vista."""
        self._pause()
        self.menu.select(name, self.router.can_go_back)
        self.apply_button.visible = name == "config"
        self.edit_button.visible = name == "results"
        self.action_hint.value = "Se usarán los individuos guardados en la lista." if name == "config" else "Puedes volver a editar sin perder los resultados."
        self.page.update()
        if hasattr(self.page, "run_task"):
            self.page.run_task(self._scroll_to_start)

    async def _scroll_to_start(self):
        """Vuelve al inicio del cuerpo al navegar, para no abrir resultados a mitad del contenido."""
        await asyncio.sleep(0)
        await self.body.scroll_to(offset=0, duration=0)

    def _pause(self):
        """Cancela tareas de reproducción o resultados anteriores mediante revision."""
        self.playing = False
        self.revision += 1
        self.play_button.content = "Reproducir"

    def invalidate(self, e=None):
        """Marca cambios pendientes conservando resultados de la última configuración aplicada."""
        self._pause()
        self.message.color = MUTED
        self.message.value = "Cambios pendientes. Pulsa Ver resultados para aplicar la configuración."
        self.page.update()

    def population_changed(self, individuals):
        """Recibe el evento del editor; el tamaño aplicado proviene de su lista guardada."""
        self.invalidate()

    def change_crossover(self, e=None):
        """Actualiza porcentaje de cruza visible; el motor recibirá este valor dividido entre 100."""
        self.crossover_label.value = f"Cruza · {self.crossover.value:.0f} %"
        self.invalidate()

    def change_mutation(self, e=None):
        """Actualiza porcentaje visible; el motor recibirá este valor dividido entre 100."""
        self.mutation_label.value = f"Mutación · {self.mutation.value:.0f} %"
        self.invalidate()

    def change_objective(self, e=None):
        """Adapta dimensiones y límites del editor; genera automáticamente población para el nuevo dominio."""
        self._sync_dimension_control()
        objective = get_objective(self.function.value, int(self.dimensions.value))
        self.editor.set_schema(objective.dimensions, objective.labels, objective.bounds, notify=False)
        try:
            count = max(2, min(200, int(self.size.value)))
        except (ValueError, TypeError):
            count = 20
        self.editor.set_individuals(initial_population(count, objective), notify=False)
        self.formula.value = objective.expression+"\n"+" · ".join(f"{label} ∈ [{low:g}, {high:g}]" for label, (low, high) in zip(objective.labels, objective.bounds))
        self.invalidate()
        self.message.value = "Función cambiada: se generó una población inicial en el nuevo dominio. Pulsa Ver resultados."
        self.page.update()

    def configure(self, e=None):
        """Reemplaza la población por una muestra del dominio; no ejecuta el algoritmo."""
        try:
            count = int(self.size.value)
            objective = get_objective(self.function.value, int(self.dimensions.value))
            self.editor.set_individuals(initial_population(count, objective))
        except (ValueError, TypeError) as error:
            self.message.value = str(error) if isinstance(error, ValueError) and str(error).startswith("La cantidad") else "La cantidad para generar debe ser un entero entre 2 y 200."
            self.message.color = ERROR
        self.page.update()

    def settings(self) -> AlgorithmConfig:
        """Construye la entrada tipada del motor a partir de parámetros e individuos guardados."""
        try:
            total = int(self.generations.value)
        except (ValueError, TypeError):
            raise ValueError("Las generaciones deben ser un número entero.") from None
        if not 1 <= total <= 500:
            raise ValueError("Las generaciones deben estar entre 1 y 500.")
        if self.editor.editing_index is not None or any(input_field.value.strip() for input_field in self.editor.fields):
            raise ValueError("Guarda el individuo pendiente o cancela sus campos antes de ver resultados.")
        objective = get_objective(self.function.value, int(self.dimensions.value))
        population = validate_population(self.editor.individuals, objective)
        return AlgorithmConfig(
            population=population,
            objective=objective,
            mutation_rate=self.mutation.value / 100,
            selection=self.selection.value,
            generations=total,
            crossover_rate=self.crossover.value / 100,
        )

    async def apply(self, e=None):
        """Ejecuta el motor fuera del hilo de interfaz, valida la salida y abre resultados."""
        if self.busy:
            return
        try:
            config = self.settings()
        except ValueError as error:
            self.message.value, self.message.color = str(error), ERROR
            self.page.update()
            return
        self._pause()
        token = self.revision
        self.busy, self.apply_button.disabled = True, True
        self.apply_button.content = "Preparando resultados…"
        self.message.value, self.message.color = "Procesando la configuración…", MUTED
        self.page.update()
        try:
            snapshots = await asyncio.to_thread(self.engine.run, config)
            validate_generations(snapshots, config)
            if token != self.revision:
                self.message.value = "La configuración cambió durante el cálculo. Vuelve a aplicar."
                return
            self.config, self.snapshots = config, snapshots
            self.total, self.index = config.generations, 0
            maximize = config.objective.maximize
            self.history = [
                (max(generation.scores) if maximize else min(generation.scores))
                for generation in snapshots
            ]
            self.timeline.max, self.timeline.divisions = self.total, self.total
            self.message.value = "Vista de demostración: selección y mutación no modifican el recorrido." if self.is_demo else "Resultados del algoritmo genético."
            mode_str = "Maximización" if maximize else "Minimización"
            self.result_summary.value = (
                f"{config.objective.name} ({mode_str}) · {config.objective.dimensions}D · "
                f"{len(config.population)} individuos · Selección: {config.selection.capitalize()} · "
                f"Cruza: {config.crossover_rate:.0%} · Mutación: {config.mutation_rate:.0%}"
            )
            self.render()
            self.menu.set_enabled("results", True)
            self.show_view("results")
        except Exception as error:
            self.message.value, self.message.color = f"No se pudieron preparar los resultados: {error}", ERROR
        finally:
            self.busy, self.apply_button.disabled = False, False
            self.apply_button.content = "Ver resultados"
            self.page.update()

    def render(self):
        """Dibuja una generación recibida del motor; no calcula operadores genéticos."""
        if not self.snapshots:
            return
        generation = self.snapshots[self.index]
        objective = self.config.objective
        values, scores = generation.population, generation.scores
        best = self._best_index(scores, objective.maximize)
        opt_label = "Mejor evaluación (Máx)" if objective.maximize else "Mejor evaluación (Mín)"
        metrics = [("Generación", f"{self.index} / {self.total}"), (opt_label, f"{scores[best]:.5g}"), ("Promedio", f"{sum(scores)/len(scores):.5g}")]
        self.metrics.controls = [ft.Container(content=ft.Column([ft.Text(label, size=12, color=MUTED), ft.Text(value, size=24, weight=ft.FontWeight.W_600, color=TEXT)], spacing=6), bgcolor="#FFFFFF", padding=20, border_radius=12, border=ft.Border.all(1, BORDER), col={"xs":12, "sm":4}) for label, value in metrics]
        self._render_function(generation, best)
        self.history_chart.set_image(plot(list(enumerate(self.history)), [(self.index, self.history[self.index])], xlabel="Generación", best_dot=(self.index, self.history[self.index])))
        self.table.controls = [ft.Container(content=ft.Column([ft.Row([ft.Text(f"Individuo {i+1:02d}", size=13, color=TEXT), ft.Text("Mejor" if i == best else "", size=12, color=ACCENT)]), ft.Text(" · ".join(f"{label} = {v:.5g}" for label, v in zip(objective.labels, individual)), size=12, color=MUTED), ft.Text(f"f = {scores[i]:.5g}", size=13, color=TEXT)], spacing=5), padding=12, bgcolor="#E8EEF5" if i == best else SOFT, border_radius=10) for i, individual in enumerate(values)]
        self.timeline.value, self.progress.value = self.index, self.index/self.total
        self.page.update()

    def _render_function(self, generation, best: int):
        """Actualiza sólo la gráfica de función, según dimensión y cámara seleccionadas."""
        objective = self.config.objective
        values, scores = generation.population, generation.scores
        self.chart_controls.visible = objective.dimensions == 2
        self.camera_controls.visible = objective.dimensions == 2 and self.chart_mode.value == "surface"
        if objective.dimensions == 1:
            lower, upper = objective.bounds[0]
            curve = [(lower+(upper-lower)*i/300, 0) for i in range(301)]
            dots = [(v[0], score) for v, score in zip(values, scores)]
            best_dot = (values[best][0], scores[best])
            chart = plot([(x, objective.evaluate((x,))) for x, _ in curve], dots, best_dot=best_dot)
        elif self.chart_mode.value == "surface":
            chart = surface3d(objective, values, best, self.elevation.value, self.azimuth.value)
        else:
            chart = heatmap(objective, values, best)
        self.function_chart.set_image(chart)

    def change_chart(self, e=None):
        """Redibuja al elegir modo o soltar el slider de cámara; conserva generación y parámetros."""
        if not self.snapshots:
            return
        generation = self.snapshots[self.index]
        best = self._best_index(generation.scores, self.config.objective.maximize)
        self._render_function(generation, best)
        self.page.update()

    def seek(self, e=None):
        """Pausa y salta a la generación indicada por el slider."""
        self._pause()
        self.index = round(self.timeline.value)
        self.render()

    def step(self, delta: int):
        """Pausa y avanza delta generaciones, acotando el índice al recorrido."""
        self._pause()
        self.index = max(0, min(self.total, self.index+delta))
        self.render()

    def reset(self, e=None):
        """Vuelve a la generación inicial manteniendo resultados aplicados."""
        self.step(-self.index)

    async def toggle_play(self, e=None):
        """Recorre snapshots con esperas asíncronas; revision cancela una tarea anterior."""
        if not self.snapshots:
            return
        if self.playing:
            self.step(0)
            return
        if self.index == self.total:
            self.index = 0
        self.playing = True
        self.revision += 1
        token = self.revision
        self.play_button.content = "Pausar"
        self.render()
        while self.playing and token == self.revision and self.index < self.total:
            await asyncio.sleep(0.35)
            if not self.playing or token != self.revision:
                return
            self.index += 1
            self.render()
        if token == self.revision:
            self.playing = False
            self.play_button.content = "Reproducir"
            self.page.update()
