"""Menú de algoritmos: cada panel conserva su propia configuración y resultados."""
import flet as ft
from models.genetic_engine import GeneticEngine
from models.pso_demo_engine import PSODemoEngine
from views.dashboard import Dashboard
from views.menu import Menu, MenuItem
from views.router import ViewRouter
from views.theme import ACCENT, TEXT


class OptimizationApp:
    """Aloja el evolutivo existente y una simulación PSO en vistas independientes."""

    def __init__(self, page: ft.Page):
        """Para conectar PSO real, sustituye únicamente PSODemoEngine() por PSOEngine()."""
        self.page = page
        self.panels = {
            "genetic": Dashboard(page, engine=GeneticEngine(), algorithm="genetic"),
            # PUNTO DE CONEXIÓN: from models.pso_engine import PSOEngine
            # Cambiar engine=PSODemoEngine() por engine=PSOEngine() tras implementarlo.
            "pso": Dashboard(page, engine=PSODemoEngine(), algorithm="pso"),
        }
        self.active = "genetic"
        self.router = ViewRouter({key: panel.build(show_header=False) for key, panel in self.panels.items()}, initial=self.active, on_change=self.change_algorithm)
        self.router.outlet.expand = True
        self.menu = Menu([MenuItem("genetic", "Evolutivo", ft.Icons.SCIENCE_OUTLINED), MenuItem("pso", "Partículas · PSO", ft.Icons.GRAIN)], on_navigate=self.router.go)
        self.menu.select(self.active)

    def change_algorithm(self, name: str):
        """Pausa el panel anterior y conserva sus campos al cambiar de algoritmo."""
        self.panels[self.active]._pause()
        self.active = name
        self.menu.select(name)
        self.page.update()

    def build(self) -> ft.Column:
        """Barra fija de algoritmos y panel seleccionado con cuerpo desplazable."""
        return ft.Column([ft.Row([ft.Icon(ft.Icons.SCIENCE_OUTLINED, color=ACCENT), ft.Text("Optimización Lab", color=TEXT, size=24)], spacing=12), self.menu, self.router.outlet], spacing=12, expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
