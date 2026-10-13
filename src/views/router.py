"""Navegación local entre vistas persistentes, con historial y condiciones de acceso."""
from typing import Callable
import flet as ft


class ViewRouter:
    """Mantiene las instancias de las vistas para conservar formularios y resultados."""

    def __init__(self, routes: dict[str, ft.Control], initial: str, guards: dict[str, Callable[[], bool]] | None = None, on_change: Callable[[str], None] | None = None):
        """routes asocia nombres y controles; guards limita acceso; on_change notifica navegación."""
        if initial not in routes:
            raise ValueError(f"Ruta inicial desconocida: {initial}")
        self.routes = dict(routes)
        self.guards = guards or {}
        self.on_change = on_change
        self.active = initial
        self.history = []
        self.outlet = ft.Column(list(self.routes.values()), spacing=0)
        self._sync_visibility()

    @property
    def can_go_back(self) -> bool:
        """Indica si existe una vista anterior a la que esté permitido volver."""
        return any(self._allowed(route) for route in self.history)

    def _allowed(self, route: str) -> bool:
        """Comprueba que la ruta exista y cumpla su condición de acceso opcional."""
        if route not in self.routes:
            raise ValueError(f"Ruta desconocida: {route}")
        return route not in self.guards or bool(self.guards[route]())

    def go(self, route: str) -> bool:
        """Abre route y registra la vista anterior; devuelve False si se bloqueó el acceso."""
        if not self._allowed(route):
            return False
        if route == self.active:
            return True
        self.history.append(self.active)
        self.active = route
        self._sync_visibility()
        self._emit_change()
        return True

    def back(self) -> bool:
        """Vuelve a la última ruta permitida, sin añadir una entrada nueva al historial."""
        while self.history:
            route = self.history.pop()
            if self._allowed(route):
                self.active = route
                self._sync_visibility()
                self._emit_change()
                return True
        return False

    def _sync_visibility(self):
        """Muestra sólo la vista activa sin recrear sus controles ni valores."""
        for name, view in self.routes.items():
            view.visible = name == self.active

    def _emit_change(self):
        """Notifica al consumidor para sincronizar menú, reproducción y página."""
        if self.on_change:
            self.on_change(self.active)
