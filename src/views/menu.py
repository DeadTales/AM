"""Menú reutilizable con indicador de vista activa y acción de volver."""
from dataclasses import dataclass
from typing import Callable
import flet as ft
from views.theme import ACCENT, BORDER, MUTED, SOFT


@dataclass(frozen=True)
class MenuItem:
    """route identifica la vista; label e icon definen su representación."""
    route: str
    label: str
    icon: ft.IconData


class Menu(ft.Container):
    """Presenta opciones; delega navegación sin conocer datos del algoritmo."""

    def __init__(self, items: list[MenuItem], on_navigate: Callable[[str], object], on_back: Callable[[], object]):
        """items define opciones; callbacks reciben ruta elegida o solicitud de volver."""
        super().__init__(padding=12, bgcolor=SOFT, border=ft.Border.all(1, BORDER), border_radius=12)
        self.buttons = {}
        self.back_button = ft.IconButton(icon=ft.Icons.ARROW_BACK, tooltip="Volver a la vista anterior", disabled=True, on_click=lambda e: on_back())
        for item in items:
            if item.route in self.buttons:
                raise ValueError(f"Opción duplicada: {item.route}")
            self.buttons[item.route] = ft.Button(item.label, icon=item.icon, elevation=0, on_click=lambda e, route=item.route: on_navigate(route))
        self.content = ft.Row([self.back_button, *self.buttons.values()], spacing=10, wrap=True)

    def set_enabled(self, route: str, enabled: bool):
        """Habilita o bloquea una opción; el router también debe validar su acceso."""
        self.buttons[route].disabled = not enabled

    def select(self, route: str, can_go_back: bool = False):
        """Destaca route sin deshabilitarla; actualiza disponibilidad del botón Volver."""
        if route not in self.buttons:
            raise ValueError(f"Opción desconocida: {route}")
        for name, button in self.buttons.items():
            button.bgcolor = ACCENT if name == route else SOFT
            button.color = "#FFFFFF" if name == route else MUTED
        self.back_button.disabled = not can_go_back
