"""Gráficas renderizadas a PNG: evitan comparar cientos de primitivas Canvas por actualización."""
from io import BytesIO
from base64 import b64decode
import flet as ft
import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.figure import Figure
from models.contracts import Objective
from views.theme import ACCENT, BORDER, MUTED


class Chart(ft.Container):
    """Visor persistente con dimensiones explícitas; cambiar src no reconstruye sus controles."""

    def __init__(self, height: int = 320):
        """height fija el alto del visor; el ancho se ajusta al espacio de la tarjeta."""
        super().__init__(height=height, width=float("inf"))
        placeholder = b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
        self.raster = ft.Image(src=placeholder, width=800, height=height, fit=ft.BoxFit.CONTAIN, gapless_playback=True, semantics_label="Gráfica de la evolución")
        self.viewer = ft.InteractiveViewer(content=self.raster, height=height, width=float("inf"), constrained=True, min_scale=1, max_scale=4, trackpad_scroll_causes_scale=True)
        self.content = self.viewer

    def set_image(self, png: bytes):
        """Sustituye la imagen sin recrear el visor ni perder el estado del zoom."""
        self.raster.src = png
        self.raster.visible = True


def _figure(height: int = 320):
    """Crea figura independiente de pyplot con estilo claro y margen para etiquetas."""
    figure = Figure(figsize=(8, height/100), dpi=100, layout="constrained", facecolor="white")
    axes = figure.add_subplot(111)
    axes.tick_params(colors=MUTED, labelsize=9)
    for name, spine in axes.spines.items():
        spine.set_color(BORDER)
        spine.set_visible(name not in ("top", "right"))
    return figure, axes


def _png(figure: Figure) -> bytes:
    """Renderiza con Agg sin ventanas auxiliares y devuelve bytes PNG para ft.Image."""
    stream = BytesIO()
    FigureCanvasAgg(figure).print_png(stream)
    result = stream.getvalue()
    figure.clear()
    return result


def plot(
    curve: list[tuple[float, float]],
    dots: list[tuple[float, float]],
    color: str = ACCENT,
    xlabel: str = "x",
    best_dot: tuple[float, float] | None = None,
) -> bytes:
    """Dibuja curva y puntos en un PNG; xlabel nombra el eje horizontal."""
    figure, axes = _figure()
    axes.plot(*zip(*curve), color=color, linewidth=1.8)
    if dots:
        axes.scatter(*zip(*dots), c="#243247", s=26, edgecolors="white", linewidths=0.7, zorder=3)
    if best_dot is not None:
        axes.scatter([best_dot[0]], [best_dot[1]], c="#9C5837", s=70, edgecolors="white", linewidths=1.2, zorder=4)
    axes.grid(color=BORDER, linewidth=0.6, alpha=0.7)
    axes.set_xlabel(xlabel, fontsize=10, color=MUTED)
    axes.set_ylabel("Evaluación", fontsize=10, color=MUTED)
    return _png(figure)


def heatmap(objective: Objective, population, best: int) -> bytes:
    """Muestra f(x,y) con color e individuos superpuestos, destacando best."""
    (xmin, xmax), (ymin, ymax) = objective.bounds
    resolution = 50
    xs = [xmin+(xmax-xmin)*(i+0.5)/resolution for i in range(resolution)]
    ys = [ymin+(ymax-ymin)*(j+0.5)/resolution for j in range(resolution)]
    values = [[objective.evaluate((x, y)) for x in xs] for y in ys]
    figure, axes = _figure(340)
    palette = LinearSegmentedColormap.from_list("evolution", ["#EDF2F7", "#53789B"])
    surface = axes.imshow(values, extent=(xmin, xmax, ymin, ymax), origin="lower", aspect="auto", cmap=palette)
    axes.scatter(*zip(*population), c="#243247", s=22, edgecolors="white", linewidths=0.7, zorder=3)
    axes.scatter(*population[best], c="#9C5837", s=65, edgecolors="white", linewidths=1.2, zorder=4)
    axes.set_xlabel(objective.labels[0], fontsize=10, color=MUTED)
    axes.set_ylabel(objective.labels[1], fontsize=10, color=MUTED)
    colorbar = figure.colorbar(surface, ax=axes, pad=0.025)
    colorbar.set_label("f(x, y)", fontsize=9, color=MUTED)
    colorbar.ax.tick_params(labelsize=8, colors=MUTED)
    return _png(figure)


def surface3d(objective: Objective, population, best: int, elevation: float = 30, azimuth: float = -55) -> bytes:
    """Dibuja z=f(x,y), individuos sobre la superficie y cámara en grados."""
    (xmin, xmax), (ymin, ymax) = objective.bounds
    x, y = np.meshgrid(np.linspace(xmin, xmax, 55), np.linspace(ymin, ymax, 55))
    z = np.array([[objective.evaluate((float(a), float(b))) for a, b in zip(row_x, row_y)] for row_x, row_y in zip(x, y)])
    figure = Figure(figsize=(8, 4.2), dpi=100, layout="constrained", facecolor="white")
    axes = figure.add_subplot(111, projection="3d", computed_zorder=False)
    palette = LinearSegmentedColormap.from_list("evolution3d", ["#EDF2F7", "#53789B"])
    axes.plot_surface(x, y, z, cmap=palette, alpha=0.8, linewidth=0, antialiased=True, rcount=55, ccount=55, zorder=1)
    px, py = zip(*population)
    scores = [objective.evaluate(individual) for individual in population]
    axes.scatter(px, py, scores, c="#243247", s=22, edgecolors="white", linewidths=0.5, depthshade=False, zorder=3)
    axes.scatter(*population[best], scores[best], c="#9C5837", s=75, edgecolors="white", linewidths=1, depthshade=False, zorder=4)
    axes.view_init(elev=elevation, azim=azimuth)
    axes.set_xlabel(objective.labels[0], color=MUTED, fontsize=9)
    axes.set_ylabel(objective.labels[1], color=MUTED, fontsize=9)
    axes.set_zlabel("f(x, y)", color=MUTED, fontsize=9)
    axes.tick_params(colors=MUTED, labelsize=8)
    axes.set_box_aspect((1, 1, 0.65))
    return _png(figure)