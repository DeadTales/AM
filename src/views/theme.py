"""Paleta y componentes compartidos de la interfaz."""
import flet as ft

BACKGROUND = "#F4F5F7"
SURFACE = "#FFFFFF"
SOFT = "#F0F3F7"
TEXT = "#243247"
MUTED = "#58677C"
ACCENT = "#456A91"
BORDER = "#DDE3EB"
ERROR = "#A33737"


def field(label: str, value: str = "", **kwargs) -> ft.TextField:
    """Campo uniforme; kwargs permite pasar eventos, anchura y otras opciones de Flet."""
    return ft.TextField(label=label, value=value, text_size=14, filled=True, fill_color=SOFT, border=ft.OutlineInputBorder(border_radius=10, side=ft.BorderSide(color=BORDER)), **kwargs)


def card(title: str, subtitle: str, controls: list, col=12) -> ft.Container:
    """Superficie clara con encabezado; col determina el ancho en ResponsiveRow."""
    return ft.Container(content=ft.Column([ft.Text(title, size=19, weight=ft.FontWeight.W_600, color=TEXT), ft.Text(subtitle, size=13, color=MUTED), *controls], spacing=18), bgcolor=SURFACE, border=ft.Border.all(1, BORDER), padding=24, border_radius=16, col=col)
