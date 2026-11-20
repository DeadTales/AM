"""Vistas de configuración y resultados, independientes del motor de evolución."""
import asyncio
from threading import Event
import flet as ft
from models.contracts import AlgorithmConfig, PSOConfig, validate_generations, validate_population
from models.de_engine import DEConfig, DEEngine
from models.pso_demo_engine import PSODemoEngine
from models.pso_engine import PSOEngine
from models.pso_experiments import best_history, comparable, compare_parameters, make_trial
from models.genetic_engine import GeneticEngine
from models.demo_engine import DemoEngine, initial_population
from models.objectives import FIXED_DIMENSIONS, FUNCTIONS, VARIABLE_DIMENSIONS, get_objective
from models.results import best_individual, make_record
from views.run_support import ExportActions, run_with_progress
from views.charts import Chart, heatmap, plot, surface3d, vector_plot
from views.population_editor import PopulationEditor
from views.submenu import Submenu, SubmenuItem
from views.router import ViewRouter
from views.pso_comparison import PSOComparison
from views.theme import ACCENT, BORDER, ERROR, MUTED, SOFT, TEXT, card, field


class Dashboard:
    """Coordina configuración, ejecución del motor y navegación por resultados."""

    def __init__(self, page: ft.Page, engine=None, algorithm: str = "genetic"):
        """page aloja controles; engine ejecuta run(config)."""
        self.page = page
        if algorithm not in ("genetic", "pso", "de"):
            raise ValueError("Algoritmo desconocido")
        self.algorithm = algorithm
        self.is_pso = algorithm == "pso"
        self.is_de = algorithm == "de"
        self.is_genetic = algorithm == "genetic"
        self.step_label = "Iteración" if self.is_pso else "Generación"
        
        if engine is not None:
            self.engine = engine
        elif self.is_pso:
            self.engine = PSOEngine()
        elif self.is_de:
            self.engine = DEEngine()
        else:
            self.engine = GeneticEngine()
            
        self.trials = []
        self.comparison_batch = 0
        self.index, self.total = 0, 40
        self.playing, self.busy, self.revision = False, False, 0
        self.snapshots = []
        self.history = []
        self.config = None
        self.run_record = None
        self._stop_event = Event()
        self.is_demo = isinstance(self.engine, DemoEngine) or getattr(self.engine, "is_demo", False)
        self.function = ft.Dropdown(label="Función objetivo", value="sine_1d", options=[ft.DropdownOption(key=k, text=name) for k, name in FUNCTIONS.items()], on_select=self.change_objective)
        self.dimensions = ft.Dropdown(label="Variables por individuo", value="1", disabled=True, options=[ft.DropdownOption(key="1", text="Una variable · x"), ft.DropdownOption(key="2", text="Dos variables · x, y")], on_select=self.change_objective)
        self.optimization = ft.Dropdown(
            label="Sentido de optimización", value="max",
            options=[ft.DropdownOption(key="min", text="Minimizar"),
                     ft.DropdownOption(key="max", text="Maximizar")],
            on_select=self.change_direction,
            tooltip="Minimizar busca valores menores; maximizar busca valores mayores de la misma función.",
        )
        self.bound_fields = []
        self.bounds_controls = ft.ResponsiveRow(run_spacing=12)
        self.apply_bounds_button = ft.TextButton(
            "Aplicar límites y regenerar población", on_click=self.configure,
        )
        self.size = field("Número de partículas" if self.is_pso else "Tamaño de población", "20",
                          helper="Cantidad al generar. La lista guardada determina el tamaño de la búsqueda.", helper_max_lines=3)
        self.generations = field("Número de iteraciones" if self.is_pso else "Número de generaciones", "40",
                                 helper="Máximo de pasos de búsqueda; entero entre 1 y 500.", on_change=self.invalidate)
        
        # Controles Genéticos
        self.selection = ft.Dropdown(label="Método de selección", value="torneo", options=[ft.DropdownOption(key=k, text=k.capitalize()) for k in ("torneo", "ruleta", "elitista")], on_select=self.invalidate,
                                     tooltip="Torneo: competencia; ruleta: probabilidad por fitness; elitista: mejores padres.")
        self.crossover_label = ft.Text("Tasa de cruza · 80 %", color=TEXT, size=14)
        self.crossover = ft.Slider(min=0, max=100, divisions=100, value=80, label="{value}%", active_color=ACCENT, on_change=self.change_crossover)
        self.mutation_label = ft.Text("Tasa de mutación · 5 %", color=TEXT, size=14)
        self.mutation = ft.Slider(min=0, max=100, divisions=100, value=5, label="{value}%", active_color=ACCENT, on_change=self.change_mutation)
        
        # Controles PSO
        self.genetic_seed = field("Semilla", "42", helper="Entero 0–4294967295 para repetir la misma búsqueda.", on_change=self.invalidate)
        self.inertia = field("Inercia (w)", "0.7", helper="0–2. Conserva una parte de la velocidad anterior.", on_change=self.invalidate)
        self.cognitive = field("Coeficiente cognitivo (c1)", "1.5", helper="0–4. Atracción hacia la mejor posición personal.", on_change=self.invalidate)
        self.social = field("Coeficiente social (c2)", "1.5", helper="0–4. Atracción hacia el mejor punto del enjambre.", on_change=self.invalidate)
        self.velocity_limit = field("Límites de velocidad (%)", "20",
                                    helper="±porcentaje del intervalo por coordenada. Mayor que 0 y hasta 100.", on_change=self.invalidate)
        self.seed = field("Semilla", "42", helper="Entero 0–4294967295 para repetir la búsqueda.", on_change=self.invalidate)

        # Controles DE
        self.de_f = field("Factor de mutación (F)", "0.8", helper="0–2. Escala la diferencia entre individuos.", on_change=self.invalidate)
        self.de_cr = field("Tasa de cruza (CR)", "0.9", helper="0–1. Probabilidad de tomar cada coordenada del mutante.", on_change=self.invalidate)
        self.de_strategy = ft.Dropdown(label="Estrategia de selección / variante", value="rand/1/bin", options=[ft.DropdownOption(key=k, text=k) for k in ("rand/1/bin", "best/1/bin")], on_select=self.invalidate,
                                      tooltip="rand: base aleatoria; best: mejor base. Cruza binomial y reemplazo voraz.")
        self.de_seed = field("Semilla", "42", helper="Entero 0–4294967295 para repetir la búsqueda.", on_change=self.invalidate)
        
        self.genetic_controls = ft.Column([self.selection, ft.Text("Torneo: competencia; ruleta: probabilidad por fitness; elitista: mejores padres.", size=12), ft.Column([self.crossover_label, self.crossover, ft.Text("Probabilidad de cruzar los padres (0–100 %).", size=12)], spacing=0), ft.Column([self.mutation_label, self.mutation, ft.Text("Probabilidad de mutar cada coordenada (0–100 %).", size=12)], spacing=0), self.genetic_seed, ft.Text("Variante: elitismo, cruza BLX-α=0.25 y mutación gaussiana con σ=10 % del intervalo.", size=12)], visible=self.is_genetic)
        self.pso_controls = ft.Column([self.inertia, self.cognitive, self.social, self.velocity_limit, self.seed, ft.Text("Variante global-best. Velocidades iniciales uniformes en ±5 % del intervalo.", size=12, color=MUTED)], visible=self.is_pso)
        self.de_controls = ft.Column([self.de_f, self.de_cr, self.de_strategy, self.de_seed, ft.Text("Variante DE: rand/1/bin usa base aleatoria; best/1/bin usa el mejor individuo. Ambas aplican cruza binomial y selección voraz.", size=12, color=MUTED)], visible=self.is_de)
        
        self.generations.label = "Número de iteraciones" if self.is_pso else "Número de generaciones"
        self.mode_status = ft.Text("Evolución Diferencial" if self.is_de else ("PSO · Simulación didáctica" if self.is_pso and self.is_demo else ("PSO conectado" if self.is_pso else "GA · Algoritmo genético")), color=ACCENT, size=12)
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
        self.timeline = ft.Slider(min=0, max=40, divisions=40, value=0, label=self.step_label+" {value}", active_color=ACCENT, on_change=self.seek)
        self.play_button = ft.Button("Reproducir", icon=ft.Icons.PLAY_ARROW, on_click=self.toggle_play)
        self.progress = ft.ProgressBar(value=0, color=ACCENT, bgcolor=SOFT)
        self.apply_button = ft.Button("Ejecutar", icon=ft.Icons.PLAY_ARROW, on_click=self.apply)
        self.stop_button = ft.TextButton("Detener", icon=ft.Icons.STOP, on_click=self.request_stop, visible=False)
        self.reset_button = ft.TextButton("Reiniciar", icon=ft.Icons.RESTART_ALT, on_click=self.reset)
        self.exporter = ExportActions(self.page.update)
        self.edit_button = ft.Button("Editar configuración", icon=ft.Icons.TUNE, on_click=lambda e: self.show_view("config"), visible=False)
        self.action_hint = ft.Text("Se usarán los individuos guardados en la lista.", size=12, color=MUTED, width=240)
        self.actions = ft.Container(content=ft.Row([self.action_hint, self.apply_button, self.stop_button, self.reset_button, self.edit_button], spacing=12, wrap=True), padding=12, bgcolor=SOFT, border_radius=12)
        self.result_summary = ft.Text(size=13, color=MUTED)
        self.configuration_view = ft.Column()
        self.results_view = ft.Column(visible=False)
        self.comparison = PSOComparison(self.compare_pso, self.page.update)
        routes = {"config": self.configuration_view, "results": self.results_view}
        items = [SubmenuItem("config", "Configuración", ft.Icons.TUNE), SubmenuItem("results", "Simulación / Resultados", ft.Icons.INSIGHTS)]
        if self.is_pso:
            routes["comparison"] = self.comparison
            items.append(SubmenuItem("comparison", "Comparar pruebas", ft.Icons.COMPARE_ARROWS))
        self.router = ViewRouter(routes, initial="config", guards={"results": lambda: bool(self.snapshots) or self.busy}, on_change=self._on_route_change)
        self.submenu = Submenu(items, on_navigate=self.show_view, on_back=self.router.back)
        self.submenu.set_enabled("results", False)
        self.submenu.select("config")
        self._prepare_population()

    def _sync_dimension_control(self):
        """Ajusta y bloquea/desbloquea el selector de variables según la función elegida."""
        fixed = FIXED_DIMENSIONS.get(self.function.value)
        if fixed is not None:
            self.dimensions.options = [ft.DropdownOption(key=str(fixed), text=str(fixed))]
            self.dimensions.value = str(fixed)
            self.dimensions.disabled = True
        else:
            lower, upper = VARIABLE_DIMENSIONS[self.function.value]
            self.dimensions.options = [ft.DropdownOption(key=str(n), text=str(n)) for n in range(lower, upper + 1)]
            if self.dimensions.value not in {str(n) for n in range(lower, upper + 1)}:
                self.dimensions.value = str(max(lower, 2))
            self.dimensions.disabled = False

    def _set_bound_fields(self, objective):
        """Muestra un intervalo editable por coordenada de la función elegida."""
        self.bound_fields = [
            (field("Mínimo", f"{lower:g}", expand=True, on_change=self.invalidate, tooltip="Cota inferior finita; debe ser menor que la superior."),
             field("Máximo", f"{upper:g}", expand=True, on_change=self.invalidate, tooltip="Cota superior finita; debe ser mayor que la inferior."))
            for lower, upper in objective.bounds
        ]
        self.bounds_controls.controls = [
            ft.Column([ft.Text(label, color=ACCENT), ft.Row([lower, upper])],
                      col=12, spacing=4)
            for label, (lower, upper) in zip(objective.labels, self.bound_fields)
        ]

    def _current_objective(self):
        """Lee dimensión, intervalos y sentido sin alterar la función matemática."""
        try:
            dimensions = int(self.dimensions.value)
        except (TypeError, ValueError):
            raise ValueError("La dimensión debe ser un entero válido.") from None
        if self.optimization.value not in ("min", "max"):
            raise ValueError("Selecciona Minimizar o Maximizar.")
        bounds = []
        for index, (lower, upper) in enumerate(self.bound_fields, start=1):
            try:
                bounds.append((float(lower.value), float(upper.value)))
            except (TypeError, ValueError):
                raise ValueError(f"Escribe dos números para los límites de la variable {index}.") from None
        return get_objective(self.function.value, dimensions, bounds=tuple(bounds),
                             maximize=self.optimization.value == "max")

    def _describe_objective(self, objective):
        self.formula.value = objective.expression + "\n" + " · ".join(
            f"{label} ∈ [{lower:g}, {upper:g}]"
            for label, (lower, upper) in zip(objective.labels, objective.bounds)
        )

    def change_direction(self, event=None):
        try:
            self._describe_objective(self._current_objective())
            self.invalidate()
        except ValueError as error:
            self._pause()
            self.message.value, self.message.color = str(error), ERROR
            self.page.update()

    def _best_index(self, scores: tuple[float, ...], maximize: bool) -> int:
        """Devuelve el índice del mejor individuo según si se maximiza o minimiza."""
        return max(range(len(scores)), key=lambda i: scores[i]) if maximize else min(range(len(scores)), key=lambda i: scores[i])

    def _prepare_population(self):
        """Carga población inicial de ejemplo y fórmula sin ejecutar el motor."""
        self._sync_dimension_control()
        objective = get_objective(self.function.value, int(self.dimensions.value))
        self._selected_function = self.function.value
        self.optimization.value = "max" if objective.maximize else "min"
        self._set_bound_fields(objective)
        self.editor.set_schema(objective.dimensions, objective.labels, objective.bounds, notify=False)
        self.editor.set_individuals(initial_population(int(self.size.value), objective), notify=False)
        self._describe_objective(objective)

    def build(self, show_header: bool = True) -> ft.Column:
        """Construye dos vistas para separar preparación y análisis visual."""
        self.configuration_view.controls = [ft.ResponsiveRow([
            card("Problema y parámetros", "Solución: vector de números reales. Cada coordenada debe respetar su intervalo. El valor objetivo es f(x).", [self.function, self.dimensions, self.optimization, self.bounds_controls, self.apply_bounds_button, self.formula, ft.Divider(color=BORDER), self.generations, self.genetic_controls, self.pso_controls, self.de_controls], {"xs":12, "lg":4}),
            card("Población inicial", "Cada fila es un individuo. Puedes agregarlo, editarlo o eliminarlo.", [ft.Row([self.size, ft.TextButton("Generar población", icon=ft.Icons.REFRESH, on_click=self.configure)], wrap=True), self.editor], {"xs":12, "lg":8}),
        ], spacing=20, run_spacing=20)]
        self.results_view.controls = [self.result_summary, self.exporter, self.metrics, ft.ResponsiveRow([
            card("Función y población", "Curva para 1 variable; superficie o mapa para 2; vectores por coordenada para más dimensiones.", [self.chart_controls, self.function_chart], {"xs":12, "lg":8}),
            card("Partículas" if self.is_pso else "Individuos", "Primero, el mejor encontrado hasta el paso elegido; después, la población de ese paso.", [self.table], {"xs":12, "lg":4}),
        ], spacing=20, run_spacing=20), card("Convergencia", "Mejor valor encontrado desde la inicialización (iteración 0).", [ft.Row([ft.IconButton(icon=ft.Icons.SKIP_PREVIOUS, tooltip="Volver al inicio del historial", on_click=lambda e: self.step(-self.index)), ft.IconButton(icon=ft.Icons.CHEVRON_LEFT, tooltip="Paso anterior", on_click=lambda e: self.step(-1)), self.play_button, ft.IconButton(icon=ft.Icons.CHEVRON_RIGHT, tooltip="Paso siguiente", on_click=lambda e: self.step(1))], wrap=True), self.timeline, self.progress, self.history_chart])]
        self.body = ft.Column([self.message, self.router.outlet], spacing=16, scroll=ft.ScrollMode.AUTO, expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        header = ft.Row([ft.Icon(ft.Icons.SCIENCE_OUTLINED, color=ACCENT, size=26), ft.Text("Evolución Lab", size=24, weight=ft.FontWeight.W_600, color=TEXT), self.mode_status], spacing=12)
        return ft.Column(([header] if show_header else [self.mode_status])+[self.submenu, self.body, self.actions], spacing=12, expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    def show_view(self, name: str):
        """Solicita navegación al router conservando edición y resultados existentes."""
        return self.router.go(name)

    def _on_route_change(self, name: str):
        """Pausa reproducción y sincroniza el submenú cuando el router cambia de etapa."""
        self._pause_playback()
        self.submenu.select(name, self.router.can_go_back)
        if name == "config" and self.busy:
            self.request_stop()
        self.apply_button.visible = name == "config"
        self.edit_button.visible = name != "config"
        self.action_hint.value = "Se usarán los individuos guardados en la lista." if name == "config" else "Puedes volver a editar sin perder los resultados."
        self.page.update()
        if hasattr(self.page, "run_task"):
            self.page.run_task(self._scroll_to_start)

    async def _scroll_to_start(self):
        """Vuelve al inicio del cuerpo al navegar, para no abrir resultados a mitad del contenido."""
        await asyncio.sleep(0)
        await self.body.scroll_to(offset=0, duration=0)

    def _pause(self):
        self._pause_playback()
        if self.busy:
            self.request_stop()

    def _pause_playback(self):
        """Cancela tareas de reproducción o resultados anteriores mediante revision."""
        self.playing = False
        self.revision += 1
        self.play_button.content = "Reproducir"

    def request_stop(self, event=None):
        if self.busy:
            self._stop_event.set()
            self.stop_button.disabled = True
            self.message.value = "Deteniendo al completar el paso actual…"
            self.page.update()

    def invalidate(self, e=None):
        """Marca cambios pendientes conservando resultados de la última configuración aplicada."""
        self._pause()
        self.message.color = MUTED
        self.message.value = "Cambios pendientes. Pulsa Ver resultados para aplicar la configuración."
        self.page.update()

    def population_changed(self, individuals):
        """Recibe el evento del editor; el tamaño aplicado proviene de su lista guardada."""
        self.size.value = str(len(individuals))
        self.invalidate()

    def change_crossover(self, e=None):
        """Actualiza porcentaje de cruza visible; el motor recibirá este valor dividido entre 100."""
        self.crossover_label.value = f"Tasa de cruza · {self.crossover.value:.0f} %"
        self.invalidate()

    def change_mutation(self, e=None):
        """Actualiza porcentaje visible; el motor recibirá este valor dividido entre 100."""
        self.mutation_label.value = f"Tasa de mutación · {self.mutation.value:.0f} %"
        self.invalidate()

    def change_objective(self, e=None):
        """Adapta dimensiones y límites del editor; genera automáticamente población para el nuevo dominio."""
        self._sync_dimension_control()
        objective = get_objective(self.function.value, int(self.dimensions.value))
        if self.function.value != self._selected_function:
            self.optimization.value = "max" if objective.maximize else "min"
        self._selected_function = self.function.value
        self._set_bound_fields(objective)
        objective = self._current_objective()
        self.editor.set_schema(objective.dimensions, objective.labels, objective.bounds, notify=False)
        try:
            count = max(2, min(200, int(self.size.value)))
        except (ValueError, TypeError):
            count = 20
        self.editor.set_individuals(initial_population(count, objective), notify=False)
        self._describe_objective(objective)
        self.invalidate()
        self.message.value = "Función o dimensión cambiada: se restauraron sus límites y se generó la población. Puedes editar los intervalos antes de ejecutar."
        self.page.update()

    def configure(self, e=None):
        """Reemplaza la población por una muestra del dominio; no ejecuta el algoritmo."""
        try:
            try:
                count = int(self.size.value)
            except (TypeError, ValueError):
                raise ValueError("La cantidad para generar debe ser un entero entre 2 y 200.") from None
            objective = self._current_objective()
            population = initial_population(count, objective)
            self.editor.set_schema(objective.dimensions, objective.labels, objective.bounds, notify=False)
            self.editor.set_individuals(population)
            self._describe_objective(objective)
        except (ValueError, TypeError) as error:
            self.message.value = str(error) if isinstance(error, ValueError) else "La cantidad para generar debe ser un entero entre 2 y 200."
            self.message.color = ERROR
        self.page.update()

    def settings(self) -> AlgorithmConfig | PSOConfig | DEConfig:
        """Construye la entrada tipada del motor a partir de parámetros e individuos guardados."""
        try:
            total = int(self.generations.value)
        except (ValueError, TypeError):
            raise ValueError(f"{self.generations.label} debe ser un número entero.") from None
        if not 1 <= total <= 500:
            raise ValueError(f"{self.generations.label} debe estar entre 1 y 500.")
        if self.editor.editing_index is not None or any(input_field.value.strip() for input_field in self.editor.fields):
            raise ValueError("Guarda el individuo pendiente o cancela sus campos antes de ver resultados.")
        
        objective = self._current_objective()
        try:
            population = validate_population(self.editor.individuals, objective)
        except ValueError as error:
            raise ValueError(f"{error} Puedes aplicar los límites y regenerar la población.") from None
        try:
            desired_size = int(self.size.value)
        except (TypeError, ValueError):
            raise ValueError(f"{self.size.label} debe ser un entero entre 2 y 200.") from None
        if not 2 <= desired_size <= 200:
            raise ValueError(f"{self.size.label} debe estar entre 2 y 200.")
        if desired_size != len(population):
            raise ValueError("Pulsa Generar población para aplicar el tamaño seleccionado, o conserva el tamaño de la lista guardada.")
        if self.editor.bounds != objective.bounds:
            self.editor.set_schema(objective.dimensions, objective.labels, objective.bounds, notify=False)
            self.editor.set_individuals(population, notify=False)
        
        if self.is_pso:
            try:
                config = PSOConfig(population, objective, total, float(self.inertia.value), float(self.cognitive.value), float(self.social.value), int(self.seed.value), float(self.velocity_limit.value) / 100)
            except (ValueError, TypeError):
                raise ValueError("La inercia, los coeficientes y los límites de velocidad deben ser numéricos; la semilla debe ser entera.") from None
            config.validate()
            return config
        elif self.is_de:
            try:
                config = DEConfig(
                    population=population,
                    objective=objective,
                    generations=total,
                    mutation_factor=float(self.de_f.value),
                    crossover_rate=float(self.de_cr.value),
                    strategy=self.de_strategy.value,
                    seed=int(self.de_seed.value)
                )
            except (ValueError, TypeError):
                raise ValueError("F y CR deben ser números; la semilla debe ser entera.") from None
            config.validate()
            return config
            
        try:
            genetic_seed = int(self.genetic_seed.value)
        except (TypeError, ValueError):
            raise ValueError("La semilla debe ser un entero entre 0 y 4294967295.") from None
        config = AlgorithmConfig(
            population=population,
            objective=objective,
            mutation_rate=self.mutation.value / 100,
            selection=self.selection.value,
            generations=total,
            crossover_rate=self.crossover.value / 100,
            seed=genetic_seed,
        )
        config.validate()
        return config

    def _describe_config(self, config):
        name = {"genetic": "GA", "pso": "PSO", "de": "DE"}[self.algorithm]
        direction = "Maximización" if config.objective.maximize else "Minimización"
        if self.is_pso:
            parameters = f"w={config.inertia:g}, c1={config.cognitive:g}, c2={config.social:g}, límite de velocidad=±{config.velocity_limit:.0%}"
        elif self.is_de:
            parameters = f"F={config.mutation_factor:g}, CR={config.crossover_rate:g}, {config.strategy}"
        else:
            parameters = f"Selección: {config.selection} · Cruza: {config.crossover_rate:.0%} · Mutación: {config.mutation_rate:.0%}"
        domain = " · ".join(f"{label} ∈ [{low:g}, {high:g}]" for label, (low, high) in zip(config.objective.labels, config.objective.bounds))
        return (f"{name} · {config.objective.name} · {direction} · {len(config.population)} "
                f"{'partículas' if self.is_pso else 'individuos'} · {config.generations} {'iteraciones' if self.is_pso else 'generaciones'} · "
                f"{parameters} · Semilla {config.seed}\n{domain}")

    def _progressed(self, batch):
        self.snapshots.extend(batch)
        self.history = list(best_history(self.snapshots, self.config.objective.maximize))
        self.index = len(self.snapshots) - 1
        self.timeline.max = self.timeline.divisions = max(1, self.index)
        self.message.value = f"Ejecutando: {self.step_label.lower()} {self.index} de {self.config.generations}."
        self.render()

    async def apply(self, e=None):
        """Ejecuta con progreso real y conserva cada estado para revisarlo después."""
        if self.busy:
            return
        try:
            config = self.settings()
        except ValueError as error:
            self.message.value, self.message.color = str(error), ERROR
            self.page.update()
            return
        self._pause_playback()
        self._stop_event.clear()
        self.config, self.snapshots, self.history, self.index = config, [], [], 0
        self.metrics.controls, self.table.controls = [], []
        self.history_chart.clear()
        self.function_chart.clear()
        self.run_record = None
        self.exporter.set_record(None)
        self.total = config.generations
        self.busy = self.apply_button.disabled = self.configuration_view.disabled = True
        self.reset_button.disabled = self.edit_button.disabled = True
        self.timeline.disabled = self.play_button.disabled = True
        self.stop_button.visible, self.stop_button.disabled = True, False
        self.result_summary.value = self._describe_config(config)
        self.message.value, self.message.color = "Inicializando la búsqueda…", MUTED
        self.submenu.set_enabled("results", True)
        try:
            self.show_view("results")
            self.page.update()
            snapshots = await run_with_progress(self.engine.run, config,
                                                stop_event=self._stop_event, on_progress=self._progressed)
            validate_generations(snapshots, config, allow_partial=True)
            self.snapshots = snapshots
            self.history = list(best_history(snapshots, config.objective.maximize))
            self.index = self.total = len(snapshots) - 1
            self.timeline.max = self.timeline.divisions = max(1, self.total)
            reason = self.engine.stop_reason
            self.run_record = make_record(self.algorithm, config, snapshots, reason)
            self.exporter.set_record(self.run_record)
            self.message.value = f"{'PSO' if self.is_pso else 'DE' if self.is_de else 'GA'}: {reason}"
            if self.is_pso and len(snapshots) == config.generations + 1:
                self.trials.append(make_trial(f"Prueba {len(self.trials)+1}", config, snapshots, self.is_demo))
                self._sync_trials(config)
            self.render()
        except Exception as error:
            self.message.value, self.message.color = f"No se pudieron preparar los resultados: {error}", ERROR
        finally:
            self.busy = self.apply_button.disabled = self.configuration_view.disabled = False
            self.reset_button.disabled = self.edit_button.disabled = False
            self.timeline.disabled = self.play_button.disabled = len(self.snapshots) < 2
            self.stop_button.visible, self.stop_button.disabled = False, False
            self.apply_button.content = "Ejecutar"
            self.page.update()

    def render(self):
        """Presenta primero el récord real, sin alterar el orden de la población del motor."""
        if not self.snapshots:
            return
        generation = self.snapshots[self.index]
        objective = self.config.objective
        values, scores = generation.population, generation.scores
        best = self._best_index(scores, objective.maximize)
        record = best_individual(self.snapshots[:self.index + 1], objective.maximize)
        self.displayed_best = record
        self.ordered_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=objective.maximize)
        metrics = [(self.step_label, f"{self.index} / {self.total}"),
                   ("Mejor evaluación (Máx)" if objective.maximize else "Mejor evaluación (Mín)", f"{record.fitness:.7g}"),
                   ("Promedio actual", f"{sum(scores)/len(scores):.5g}")]
        self.metrics.controls = [ft.Container(content=ft.Column([ft.Text(label, size=12, color=MUTED),
                                     ft.Text(value, size=24, weight=ft.FontWeight.W_600, color=TEXT)], spacing=6),
                                 bgcolor="#FFFFFF", padding=20, border_radius=12, border=ft.Border.all(1, BORDER),
                                 col={"xs":12, "sm":4}) for label, value in metrics]
        self._render_function(generation, best)
        self.history_chart.set_image(plot(list(enumerate(self.history)), [(self.index, self.history[self.index])],
                                          xlabel=self.step_label, best_dot=(self.index, self.history[self.index])))
        vector_text = " · ".join(f"{label} = {value:.7g}" for label, value in zip(objective.labels, record.solution))
        self.table.controls = [ft.Container(content=ft.Column([
            ft.Text("Mejor encontrado", color=ACCENT, weight=ft.FontWeight.W_600),
            ft.Text(f"Evaluación: {record.fitness:.8g}", size=20, color=TEXT, selectable=True),
            ft.Text(vector_text, size=13, selectable=True),
            ft.Text(f"Encontrado en {self.step_label.lower()} {record.iteration}.", size=12, color=MUTED),
        ], spacing=6), padding=16, bgcolor="#E8EEF5", border_radius=10)]
        matching = next((i for i in self.ordered_indices if values[i] == record.solution and scores[i] == record.fitness), None)
        label = "Partícula" if self.is_pso else "Individuo"
        for i in self.ordered_indices:
            if i == matching:
                continue
            self.table.controls.append(ft.Container(content=ft.Column([
                ft.Text(f"{label} {i+1:02d} · {self.step_label.lower()} {self.index}", size=13, color=TEXT),
                ft.Text(" · ".join(f"{key} = {value:.5g}" for key, value in zip(objective.labels, values[i])), size=12, color=MUTED),
                ft.Text(f"Evaluación: {scores[i]:.7g}", size=14, color=TEXT),
            ], spacing=5), padding=12, bgcolor=SOFT, border_radius=10))
        self.timeline.value, self.progress.value = self.index, self.index/max(1, self.total)
        self.page.update()

    def _sync_trials(self, config: PSOConfig):
        """Presenta sólo ensayos equivalentes a la configuración actual, conservando otros grupos."""
        self.trials = self.trials[-40:]
        group = [trial for trial in self.trials if comparable(trial.config, config) and trial.simulated == self.is_demo]
        self.comparison.set_trials(group)

    async def compare_pso(self, e=None):
        """Ejecuta serie controlada con un coeficiente diferente por prueba y abre comparación."""
        if not self.is_pso or self.busy:
            return
        try:
            config = self.settings()
        except ValueError as error:
            self.comparison.status.value, self.comparison.status.color = str(error), ERROR
            self.page.update()
            return
        self._pause()
        token = self.revision
        self._stop_event.clear()
        self.busy = True
        self.stop_button.visible, self.stop_button.disabled = True, False
        self.reset_button.disabled = self.configuration_view.disabled = True
        self.apply_button.disabled = self.comparison.compare_button.disabled = True
        self.comparison.status.value = "Calculando variantes con la misma población, semilla y función…"
        self.page.update()
        try:
            trials = await asyncio.to_thread(compare_parameters, config, self.engine, self._stop_event.is_set)
            if token != self.revision:
                self.comparison.status.value = "La configuración cambió durante la comparación. Vuelve a ejecutar."
                return
            self.comparison_batch += 1
            for trial in trials:
                trial.name = f"Serie {self.comparison_batch} · {trial.name}"
            self.trials.extend(trials)
            self._sync_trials(config)
            if self._stop_event.is_set():
                self.comparison.status.value = "Comparación detenida. Se conservan las pruebas completadas."
            self.show_view("comparison")
        except Exception as error:
            self.comparison.status.value, self.comparison.status.color = str(error), ERROR
        finally:
            self.busy = False
            self.stop_button.visible, self.stop_button.disabled = False, False
            self.reset_button.disabled = self.configuration_view.disabled = False
            self.apply_button.disabled = self.comparison.compare_button.disabled = False
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
        elif objective.dimensions > 2:
            chart = vector_plot(objective, values, best)
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
        if self.busy:
            return
        self._pause_playback()
        self.index = round(self.timeline.value)
        self.render()

    def step(self, delta: int):
        """Pausa y avanza delta generaciones, acotando el índice al recorrido."""
        if self.busy:
            return
        self._pause_playback()
        self.index = max(0, min(len(self.snapshots)-1, self.index+delta))
        self.render()

    def reset(self, e=None):
        """Prepara una nueva ejecución sin borrar el problema ni sus parámetros."""
        if self.busy:
            return
        self._pause_playback()
        self.snapshots, self.history, self.config, self.run_record = [], [], None, None
        self.index, self.total = 0, 0
        self.exporter.set_record(None)
        self.table.controls = []
        self.result_summary.value = ""
        self.router.go("config")
        self.submenu.set_enabled("results", False)
        self.message.value, self.message.color = "Listo para una nueva ejecución con los parámetros del formulario.", MUTED
        self.page.update()

    async def toggle_play(self, e=None):
        """Recorre snapshots con esperas asíncronas; revision cancela una tarea anterior."""
        if not self.snapshots or self.busy:
            return
        if self.playing:
            self.step(0)
            return
        if self.index == len(self.snapshots) - 1:
            self.index = 0
        self.playing = True
        self.revision += 1
        token = self.revision
        self.play_button.content = "Pausar"
        self.render()
        while self.playing and token == self.revision and self.index < len(self.snapshots) - 1:
            await asyncio.sleep(0.35)
            if not self.playing or token != self.revision:
                return
            self.index += 1
            self.render()
        if token == self.revision:
            self.playing = False
            self.play_button.content = "Reproducir"
            self.page.update()
