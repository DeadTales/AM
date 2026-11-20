"""Panel de interfaz para la Colonia de Hormigas (ACO)."""
import flet as ft
import json
from pathlib import Path

from models.aco_engine import ACOEngine, best_solution, best_history
from models.contracts import ACOConfig
from models.categorical import TSPProblem, AssignmentProblem

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

        self.btn_run = ft.FilledButton(
            "Iniciar Optimización",
            icon=ft.Icons.PLAY_ARROW,
            on_click=self.run_aco
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
                        ]),
                        padding=15
                    ),
                    expand=3
                )
            ]),
            ft.Row([self.btn_run, self.lbl_status], alignment=ft.MainAxisAlignment.START),
            ft.Divider(),
            self.results_col
        ], expand=True, scroll=ft.ScrollMode.ADAPTIVE)

    def build(self, show_header=False) -> ft.Control:
        return self.view

    def _load_problem(self):
        """Carga el problema elegido leyendo los JSON locales."""
        try:
            base_path = Path("data")
            is_tsp = self.dd_problem.value == "tsp"
            filename = "tsp.json" if is_tsp else "asignacion.json"
            
            with open(base_path / filename, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            return TSPProblem(**data) if is_tsp else AssignmentProblem(**data)
        except Exception as e:
            self.lbl_status.value = f"Error al cargar archivo JSON: {e}"
            return None

    def run_aco(self, e):
        """Dispara o detiene el motor ACO."""
        if self._running:
            # Si ya está corriendo, el botón actúa como "Detener"
            self._running = False
            self.btn_run.text = "Iniciar Optimización"
            self.btn_run.icon = ft.Icons.PLAY_ARROW
            self.lbl_status.value = "Deteniendo colonia..."
            self.page.update()
            return

        problem = self._load_problem()
        if not problem:
            self.page.update()
            return

        # Cambiar interfaz a modo "Ejecutando"
        self._running = True
        self.btn_run.text = "Detener"
        self.btn_run.icon = ft.Icons.STOP
        self.lbl_status.value = "Hormigas explorando rutas..."
        self.results_col.controls.clear()
        self.page.update()

        # Construir configuración
        config = ACOConfig(
            problem=problem,
            ants=int(self.txt_ants.value),
            generations=int(self.txt_gen.value),
            alpha=float(self.txt_alpha.value),
            beta=float(self.txt_beta.value),
            rho=float(self.txt_rho.value),
            q=float(self.txt_q.value),
            initial_pheromone=0.0,
            patience=15, 
            seed=None
        )

        # Ejecutar el motor. Le pasamos el callback para que pueda abortarse.
        generations = self.engine.run(config, should_stop=self._should_stop)
        
        # Restaurar estado al terminar
        self._running = False
        self.btn_run.text = "Iniciar Optimización"
        self.btn_run.icon = ft.Icons.PLAY_ARROW
        self.lbl_status.value = f"Finalizado: {self.engine.stop_reason}"

        # Renderizar resultados
        if generations:
            sol, score, gen_idx = best_solution(generations)
            hist = best_history(generations)
            
            self.results_col.controls.append(
                ft.Card(
                    color=ft.colors.SURFACE_VARIANT,
                    content=ft.Container(
                        padding=20,
                        content=ft.Column([
                            ft.Text("Mejor Resultado Global", size=20, weight="bold"),
                            ft.Text(f"Costo / Distancia Mínima: {score:.4f} (alcanzado en iteración {gen_idx})", size=16),
                            ft.Text(f"Solución (Ruta/Asignación):"),
                            ft.Text(f"{sol}", color=ft.colors.ON_SURFACE_VARIANT, selectable=True),
                            ft.Divider(),
                            ft.Text("Curva de convergencia (Mejor costo por iteración):"),
                            ft.Text(", ".join([f"{h:.2f}" for h in hist]), size=12, color=ft.colors.OUTLINE)
                        ])
                    )
                )
            )
        self.page.update()