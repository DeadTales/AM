"""Menú principal dedicado a seleccionar el algoritmo de optimización."""
from dataclasses import dataclass
from typing import Callable
import flet as ft
from views.theme import ACCENT, BORDER, MUTED, SOFT


@dataclass(frozen=True)
class MenuItem:
    """route identifica un algoritmo; label e icon definen su representación."""
    route: str
    label: str
    icon: ft.IconData


class Menu(ft.Container):
    """Selecciona algoritmos; la navegación interna pertenece al componente Submenu."""

    def __init__(self, items: list[MenuItem], on_navigate: Callable[[str], object]):
        """items define algoritmos; on_navigate recibe la clave del algoritmo elegido."""
        super().__init__(padding=12, bgcolor=SOFT, border=ft.Border.all(1, BORDER), border_radius=12)
        self.buttons = {}
        for item in items:
            if item.route in self.buttons:
                raise ValueError(f"Opción duplicada: {item.route}")
            self.buttons[item.route] = ft.Button(item.label, icon=item.icon, elevation=0, on_click=lambda e, route=item.route: on_navigate(route))
        self.content = ft.Row([ft.Text("Algoritmo", size=13, color=MUTED), *self.buttons.values()], spacing=12, wrap=True)

    def select(self, route: str):
        """Destaca el algoritmo activo sin modificar sus parámetros ni su submenú."""
        if route not in self.buttons:
            raise ValueError(f"Opción desconocida: {route}")
        for name, button in self.buttons.items():
            button.bgcolor = ACCENT if name == route else SOFT
            button.color = "#FFFFFF" if name == route else MUTED
