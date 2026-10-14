"""Punto de entrada de la aplicación de escritorio."""
import flet as ft
from views.dashboard import Dashboard
from models.genetic_engine import GeneticEngine
from views.theme import ACCENT, BACKGROUND


def main(page: ft.Page):
    """Configura la ventana `page` y monta el panel con el motor genético conectado."""
    page.title = "Evolución Lab · Algoritmos genéticos"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(color_scheme_seed=ACCENT)
    page.bgcolor = BACKGROUND
    page.padding = 24
    page.window.width = 1280
    page.window.height = 900
    page.window.min_width = 760
    page.window.min_height = 640
    page.add(Dashboard(page, engine=GeneticEngine()).build())


if __name__ == "__main__":
    ft.run(main)