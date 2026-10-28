"""Submenú de etapas: configuración, simulación/resultados y comparaciones del algoritmo."""
from dataclasses import dataclass
from typing import Callable
import flet as ft
from views.theme import ACCENT, BORDER, MUTED, SOFT, SURFACE


@dataclass(frozen=True)
class SubmenuItem:
    """route identifica una etapa del panel; label e icon describen su botón."""
    route: str
    label: str
    icon: ft.IconData


class Submenu(ft.Container):
    """Navega dentro de un algoritmo y permite volver a su etapa anterior."""

    def __init__(self, items: list[SubmenuItem], on_navigate: Callable[[str], object], on_back: Callable[[], object]):
        """items define etapas; on_navigate recibe ruta; on_back vuelve en el router del panel."""
        super().__init__(padding=8, bgcolor=SURFACE, border=ft.Border.only(bottom=ft.BorderSide(color=BORDER)), border_radius=8)
        self.buttons = {}
        self.back_button = ft.IconButton(icon=ft.Icons.ARROW_BACK, tooltip="Volver a la etapa anterior de este algoritmo", disabled=True, on_click=lambda e: on_back())
        for item in items:
            if item.route in self.buttons:
                raise ValueError(f"Etapa duplicada: {item.route}")
            self.buttons[item.route] = ft.Button(item.label, icon=item.icon, elevation=0, on_click=lambda e, route=item.route: on_navigate(route))
        self.content = ft.Row([self.back_button, *self.buttons.values()], spacing=8, wrap=True)

    def set_enabled(self, route: str, enabled: bool):
        """Activa una etapa cuando tiene datos; el router también verifica el acceso."""
        self.buttons[route].disabled = not enabled

    def select(self, route: str, can_go_back: bool = False):
        """Marca la etapa activa con acento suave y sincroniza la flecha Volver."""
        if route not in self.buttons:
            raise ValueError(f"Etapa desconocida: {route}")
        for name, button in self.buttons.items():
            button.bgcolor = SOFT if name == route else SURFACE
            button.color = ACCENT if name == route else MUTED
        self.back_button.disabled = not can_go_back
