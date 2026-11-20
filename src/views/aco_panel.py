"""Panel de interfaz para la Colonia de Hormigas (ACO)."""
import flet as ft
from models.aco_engine import ACOEngine, best_solution, best_history
from models.contracts import ACOConfig
from models.categorical import load_tsp, load_assignment


class ACOPanel:
    """Vista para configurar y visualizar la optimización por Colonia de Hormigas."""

    def __init__(self, page: ft.Page, engine: ACOEngine):
        self.page = page
        self.engine = engine
        self._running = False
        self.build_ui()

    def _pause(self):
        """Detiene la ejecución si el usuario cambia a otra pestaña."""
        self._running = False

    def _should_stop(self) -> bool:
        """Callback que el motor revisa en cada iteración para saber si debe abortar."""
        return not self._running

    def build_ui(self):
        # 1. Controles de configuración
        self.dd_problem = ft.Dropdown(
            label="Problema a resolver",
            options=[
                ft.dropdown.Option("tsp", "Agente Viajero (TSP)"),
                ft.dropdown.Option("asignacion", "Asignación de Tareas")
            ],
            value="tsp"
        )

        self.txt_ants = ft.TextField(label="Hormigas", value="20", expand=True)
        self.txt_gen = ft.TextField(label="Iteraciones", value="50", expand=True)
        self.txt_alpha = ft.TextField(label="Importancia Feromona (α)", value="1.0", expand=True)
        self.txt_beta = ft.TextField(label="Importancia Heurística (β)", value="2.0", expand=True)
        self.txt_rho = ft.TextField(label="Tasa Evaporación (ρ)", value="0.1", expand=True)
        self.txt_q = ft.TextField(label="Factor de Depósito (Q)", value="100.0", expand=True)
        self.txt_seed = ft.TextField(label="Semilla (opcional)", value="", expand=True)

        self.btn_run = ft.FilledButton(
            "Iniciar Optimización",
            icon=ft.Icons.PLAY_ARROW,
            on_click=self.run_aco
        )
        self.btn_reset = ft.OutlinedButton(
            "Reiniciar",
            icon=ft.Icons.REFRESH,
            on_click=self.reset_panel
        )

        self.lbl_status = ft.Text("Configura los parámetros e inicia.", italic=True)
        self.results_col = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, expand=True)

        # 2. Ensamblar la vista principal
        self.view = ft.Column([
            ft.Row([
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Text("Instancia", size=18, weight="bold"),
                            self.dd_problem,
                            ft.Text("Objetivo: Minimización", size=13, italic=True),
                        ]),
                        padding=15
                    ),
                    expand=1
                ),
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Text("Parámetros de la Colonia", size=18, weight="bold"),
                            ft.Row([self.txt_ants, self.txt_gen]),
                            ft.Row([self.txt_alpha, self.txt_beta]),
                            ft.Row([self.txt_rho, self.txt_q]),
                            ft.Row([self.txt_seed]),
                        ]),
                        padding=15
                    ),
                    expand=3
                )
            ]),
            ft.Row([self.btn_run, self.btn_reset, self.lbl_status], alignment=ft.MainAxisAlignment.START),
            ft.Divider(),
            self.results_col
        ], expand=True, scroll=ft.ScrollMode.ADAPTIVE)

    def build(self, show_header=False) -> ft.Control:
        return self.view

    def reset_panel(self, e):
        """Restaura valores predeterminados y limpia resultados."""
        self._running = False
        self.dd_problem.value = "tsp"
        self.txt_ants.value = "20"
        self.txt_gen.value = "50"
        self.txt_alpha.value = "1.0"
        self.txt_beta.value = "2.0"
        self.txt_rho.value = "0.1"
        self.txt_q.value = "100.0"
        self.txt_seed.value = ""
        self.btn_run.text = "Iniciar Optimización"
        self.btn_run.icon = ft.Icons.PLAY_ARROW
        self.lbl_status.value = "Panel reiniciado. Configura los parámetros e inicia."
        self.results_col.controls.clear()
        self.page.update()

    def _build_convergence_chart(self, history: tuple[float, ...]) -> ft.Control:
        """Construye una gráfica visual de convergencia usando controles nativos universales de Flet."""
        min_y = min(history)
        max_y = max(history)
        span = (max_y - min_y) if max_y > min_y else 1.0
        max_height = 140

        bars = []
        for idx, val in enumerate(history):
            ratio = (val - min_y) / span if max_y > min_y else 0.5
            bar_h = 18 + int(ratio * (max_height - 18))
            bars.append(
                ft.Column(
                    [
                        ft.Container(
                            width=max(4, min(14, 520 // max(1, len(history)))),
                            height=bar_h,
                            bgcolor=ft.Colors.BLUE_400,
                            border_radius=3,
                            tooltip=f"Iteración {idx}: {val:.4f}",
                        )
                    ],
                    alignment=ft.MainAxisAlignment.END,
                    height=max_height,
                )
            )

        return ft.Card(
            content=ft.Container(
                padding=12,
                content=ft.Column([
                    ft.Row(
                        [
                            ft.Text(f"Máx: {max_y:.2f}", size=11, color=ft.Colors.OUTLINE),
                            ft.Text(f"Mín (Óptimo): {min_y:.2f}", size=11, weight="bold", color=ft.Colors.BLUE_400),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Row(
                        bars,
                        spacing=2,
                        alignment=ft.MainAxisAlignment.CENTER,
                        scroll=ft.ScrollMode.ADAPTIVE,
                    ),
                    ft.Row(
                        [
                            ft.Text("Iteración 0", size=11, color=ft.Colors.OUTLINE),
                            ft.Text(f"Iteración {len(history) - 1}", size=11, color=ft.Colors.OUTLINE),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                ]),
            )
        )
    
    def run_aco(self, e):
        """Valida entradas y ejecuta o detiene el motor ACO."""
        if self._running:
            self._running = False
            self.btn_run.text = "Iniciar Optimización"
            self.btn_run.icon = ft.Icons.PLAY_ARROW
            self.lbl_status.value = "Deteniendo colonia..."
            self.page.update()
            return

        # 1. Cargar problema y validar parámetros
        try:
            is_tsp = self.dd_problem.value == "tsp"
            problem = load_tsp() if is_tsp else load_assignment()

            ants = int(self.txt_ants.value)
            generations_count = int(self.txt_gen.value)
            alpha = float(self.txt_alpha.value)
            beta = float(self.txt_beta.value)
            rho = float(self.txt_rho.value)
            q = float(self.txt_q.value)
            seed = int(self.txt_seed.value) if self.txt_seed.value.strip() else None

            config = ACOConfig(
                problem=problem,
                ants=ants,
                generations=generations_count,
                alpha=alpha,
                beta=beta,
                rho=rho,
                q=q,
                initial_pheromone=0.0,
                patience=15,
                seed=seed
            )
            config.validate()
        except ValueError as err:
            self.lbl_status.value = f"Error de validación: {err}"
            self.page.update()
            return

        # 2. Cambiar interfaz a modo "Ejecutando"
        self._running = True
        self.btn_run.text = "Detener"
        self.btn_run.icon = ft.Icons.STOP
        self.lbl_status.value = "Hormigas explorando rutas..."
        self.results_col.controls.clear()
        self.page.update()

        # 3. Ejecutar el motor
        generations = self.engine.run(config, should_stop=self._should_stop)

        # 4. Restaurar botones y renderizar resultados
        self._running = False
        self.btn_run.text = "Iniciar Optimización"
        self.btn_run.icon = ft.Icons.PLAY_ARROW
        self.lbl_status.value = f"Finalizado: {self.engine.stop_reason}"

        if generations:
            sol, score, gen_idx = best_solution(generations)
            hist = best_history(generations)
            total_gens = len(generations) - 1

            # Hitos requeridos: Inicio (0), 1/3, 2/3 y Final
            milestones = [
                ("Inicio", 0),
                ("1/3", total_gens // 3),
                ("2/3", (2 * total_gens) // 3),
                ("Final", total_gens),
            ]
            milestone_rows = []
            for label, idx in milestones:
                gen = generations[idx]
                best_i = min(range(len(gen.scores)), key=lambda k: gen.scores[k])
                milestone_rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(f"{label} (Iter. {gen.index})")),
                        ft.DataCell(ft.Text(f"{gen.scores[best_i]:.4f}")),
                        ft.DataCell(ft.Text(problem.describe(gen.population[best_i]))),
                    ])
                )

            config_summary = (
                f"Problema: {problem.name} | Hormigas: {ants} | Iteraciones ejecutadas: {total_gens}/{generations_count} | "
                f"α={alpha}, β={beta}, ρ={rho}, Q={q} | Semilla: {seed if seed is not None else 'Aleatoria'}"
            )

            self.results_col.controls.append(
                ft.Card(
                    content=ft.Container(
                        padding=20,
                        content=ft.Column([
                            ft.Text("Resumen y Mejor Resultado Global", size=20, weight="bold"),
                            ft.Text(config_summary, size=13, italic=True),
                            ft.Text(f"Motivo de término: {self.engine.stop_reason}", size=13),
                            ft.Divider(),
                            ft.Text(f"Costo / Distancia Mínima: {score:.4f} (encontrado en iteración {gen_idx})", size=16, weight="bold"),
                            ft.Text("Mejor solución encontrada:"),
                            ft.Text(problem.describe(sol), selectable=True),
                            ft.Divider(),
                            ft.Text("Curva de Convergencia", size=16, weight="bold"),
                            self._build_convergence_chart(hist),
                            ft.Divider(),
                            ft.Text("Historial de Ejecución (Inicio, 1/3, 2/3 y Final)", size=16, weight="bold"),
                            ft.DataTable(
                                columns=[
                                    ft.DataColumn(ft.Text("Etapa")),
                                    ft.DataColumn(ft.Text("Mejor Costo")),
                                    ft.DataColumn(ft.Text("Solución")),
                                ],
                                rows=milestone_rows,
                            ),
                        ], spacing=10)
                    )
                )
            )
        self.page.update()