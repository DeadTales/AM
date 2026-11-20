"""Menú de algoritmos: cada panel conserva su propia configuración y resultados."""
import flet as ft
from models.ais_engine import AISEngine
from models.genetic_engine import GeneticEngine
from models.pso_engine import PSOEngine
from models.de_engine import DEEngine
from views.ais_panel import AISPanel
from views.dashboard import Dashboard
from views.menu import Menu, MenuItem
from views.router import ViewRouter
from views.theme import ACCENT, TEXT
from models.aco_engine import ACOEngine
from views.aco_panel import ACOPanel


class OptimizationApp:
    """Aloja Evolutivo, PSO, Evolución Diferencial y AIS en vistas independientes."""

    def __init__(self, page: ft.Page):
        """Conecta todos los motores en sus respectivos paneles."""
        self.page = page
        self.panels = {
            "genetic": Dashboard(page, engine=GeneticEngine(), algorithm="genetic"),
            "pso": Dashboard(page, engine=PSOEngine(), algorithm="pso"),
            "de": Dashboard(page, engine=DEEngine(), algorithm="de"),
            "ais": AISPanel(page, engine=AISEngine()),
            "aco": ACOPanel(page, engine=ACOEngine()),
        }
        self.active = "genetic"
        self.type_by_algorithm = {"genetic": "continuous", "pso": "continuous", "de": "continuous",
                                  "ais": "binary", "aco": "categorical"}
        self.last_by_type = {"continuous": "genetic", "binary": "ais", "categorical": "aco"}
        self.router = ViewRouter(
            {key: panel.build(show_header=False) for key, panel in self.panels.items()}, 
            initial=self.active, 
            on_change=self.change_algorithm
        )
        self.router.outlet.expand = True
        
        self.menu = Menu([
            MenuItem("genetic", "GA · Algoritmo genético", ft.Icons.SCIENCE_OUTLINED),
            MenuItem("pso", "Partículas · PSO", ft.Icons.GRAIN),
            MenuItem("de", "Evolución Diferencial", ft.Icons.TUNE),
            MenuItem("ais", "AIS · Selección clonal", ft.Icons.BIOTECH),
            MenuItem("aco", "Colonia de Hormigas", ft.Icons.BUG_REPORT)
        ], on_navigate=self.router.go)
        
        self.menu.select(self.active)
        self.problem_type = ft.Dropdown(
            label="Tipo de problema", value="continuous", width=360,
            options=[ft.DropdownOption(key="continuous", text="Continuo · vectores reales"),
                     ft.DropdownOption(key="binary", text="Binario · vectores 0/1"),
                     ft.DropdownOption(key="categorical", text="Categórico o discreto")],
            on_select=self.change_problem_type,
            tooltip="Se muestran los algoritmos compatibles con la representación elegida.",
        )
        self._filter_algorithms("continuous")

    def _filter_algorithms(self, kind):
        for name, button in self.menu.buttons.items():
            button.visible = self.type_by_algorithm[name] == kind

    def change_problem_type(self, event=None):
        kind = self.problem_type.value
        if kind not in self.last_by_type:
            raise ValueError("Selecciona un tipo de problema válido.")
        self.router.go(self.last_by_type[kind])
        self._filter_algorithms(kind)
        self.page.update()

    def change_algorithm(self, name: str):
        """Pausa el panel anterior y conserva sus campos al cambiar de algoritmo."""
        # Verificamos si el panel tiene el método _pause antes de llamarlo (AISPanel podría no tenerlo)
        if hasattr(self.panels[self.active], '_pause'):
            self.panels[self.active]._pause()
            
        self.active = name
        kind = self.type_by_algorithm[name]
        self.problem_type.value = kind
        self.last_by_type[kind] = name
        self._filter_algorithms(kind)
        self.menu.select(name)
        self.page.update()

    def build(self) -> ft.Column:
        """Barra fija de algoritmos y panel seleccionado con cuerpo desplazable."""
        return ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.SCIENCE_OUTLINED, color=ACCENT), 
                ft.Text("Optimización Lab", color=TEXT, size=24)
            ], spacing=12), 
            self.problem_type,
            self.menu, 
            self.router.outlet
        ], spacing=12, expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
