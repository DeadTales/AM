"""Editor reutilizable de individuos vectoriales con una lista de altura acotada."""
import math
from typing import Callable
import flet as ft
from views.theme import ACCENT, BORDER, ERROR, MUTED, SOFT, TEXT, field


class PopulationEditor(ft.Container):
    """Contenedor compuesto configurable por dimensiones, etiquetas y límites opcionales."""

    def __init__(self, dimensions: int = 2, labels=None, bounds=None, on_change: Callable | None = None, on_refresh: Callable | None = None, list_height: int = 290, max_individuals: int = 200):
        """dimensions: coordenadas; labels: nombres; bounds: dominios; callbacks: cambios/refresco.

        list_height limita la lista; max_individuals limita cantidad. on_change recibe
        una copia de los vectores tras modificar la lista; on_refresh solicita repintado.
        """
        super().__init__(padding=0)
        self._on_population_change = on_change
        self._refresh_callback = on_refresh
        self.max_individuals = max_individuals
        self._individuals = []
        self.editing_index = None
        self.fields = []
        self.inputs = ft.ResponsiveRow(spacing=14, run_spacing=10)
        self.counter = ft.Text(size=13, color=MUTED)
        self.error = ft.Text(color=ERROR, size=13, visible=False)
        self.mode = ft.Text("Nuevo individuo", size=14, weight=ft.FontWeight.W_600, color=TEXT)
        self.save_button = ft.Button("Agregar individuo", icon=ft.Icons.ADD, on_click=self.save)
        self.cancel_button = ft.TextButton("Cancelar edición", on_click=self.cancel_edit, visible=False)
        self.items = ft.ListView(height=list_height, spacing=8, build_controls_on_demand=True)
        self.content = ft.Column([self.mode, self.inputs, ft.Row([self.save_button, self.cancel_button], wrap=True), self.error, ft.Divider(color=BORDER), self.counter, self.items], spacing=12)
        self.set_schema(dimensions, labels, bounds, notify=False)

    @property
    def individuals(self) -> list[tuple[float, ...]]:
        """Devuelve una copia para impedir modificaciones externas del estado interno."""
        return list(self._individuals)

    def set_schema(self, dimensions: int, labels=None, bounds=None, notify: bool = True):
        """Configura coordenadas y vacía la lista para no reinterpretar datos existentes."""
        if not isinstance(dimensions, int) or dimensions < 1:
            raise ValueError("dimensions debe ser un entero positivo.")
        labels = tuple(labels) if labels is not None else tuple(f"x{i+1}" for i in range(dimensions))
        bounds = tuple(bounds) if bounds is not None else (None,)*dimensions
        if len(labels) != dimensions or len(bounds) != dimensions:
            raise ValueError("Debe existir una etiqueta y un límite por dimensión.")
        if any(not isinstance(label, str) or not label.strip() for label in labels):
            raise ValueError("Cada etiqueta debe ser un texto no vacío.")
        for bound in bounds:
            if bound is not None and (len(bound) != 2 or not all(math.isfinite(v) for v in bound) or bound[0] >= bound[1]):
                raise ValueError("Cada límite requiere dos valores finitos en orden ascendente.")
        self.dimensions, self.labels, self.bounds = dimensions, labels, bounds
        self.fields = [field("Valor", hint_text=f"{bound[0]:g} a {bound[1]:g}" if bound else "Número real", expand=True, on_submit=self.save) for bound in bounds]
        self.inputs.controls = [ft.Container(content=ft.Row([ft.Container(content=ft.Text(label, size=14, color=ACCENT, weight=ft.FontWeight.W_600), width=38), input_field], spacing=10), col={"xs":12, "md":6}) for label, input_field in zip(labels, self.fields)]
        self._individuals = []
        self._clear_form()
        self._render_list()
        if notify:
            self._emit_population_change()

    def _validate(self, values) -> tuple[float, ...]:
        """Valida dimensión, conversión, finitud y cotas sin alterar la lista."""
        if len(values) != self.dimensions:
            raise ValueError(f"Se requieren {self.dimensions} coordenadas.")
        result = []
        for label, raw, bound in zip(self.labels, values, self.bounds):
            try:
                value = float(raw)
            except (TypeError, ValueError):
                raise ValueError(f"Introduce un número para {label} (usa punto decimal).") from None
            if not math.isfinite(value):
                raise ValueError(f"{label} debe ser un número finito.")
            if bound is not None and not bound[0] <= value <= bound[1]:
                raise ValueError(f"{label} debe estar entre {bound[0]:g} y {bound[1]:g}.")
            result.append(value)
        return tuple(result)

    def set_individuals(self, individuals, notify: bool = True):
        """Sustituye la lista validada de forma atómica; permite lista vacía."""
        if len(individuals) > self.max_individuals:
            raise ValueError(f"Máximo {self.max_individuals} individuos.")
        values = [self._validate(individual) for individual in individuals]
        self._individuals = values
        self._clear_form()
        self._render_list()
        if notify:
            self._emit_population_change()

    def save(self, e=None):
        """Añade o sustituye el individuo editado y muestra errores junto al formulario."""
        try:
            individual = self._validate([input_field.value for input_field in self.fields])
            if self.editing_index is None:
                if len(self._individuals) >= self.max_individuals:
                    raise ValueError(f"Máximo {self.max_individuals} individuos.")
                self._individuals.append(individual)
            else:
                self._individuals[self.editing_index] = individual
        except ValueError as error:
            self.error.value, self.error.visible = str(error), True
            self._refresh()
            return
        self._clear_form()
        self._render_list()
        self._emit_population_change()

    def edit(self, index: int):
        """Carga el individuo index en los campos y activa modo edición."""
        self.editing_index = index
        for input_field, value in zip(self.fields, self._individuals[index]):
            input_field.value = repr(value)
        self.mode.value = f"Editar individuo {index+1:02d}"
        self.save_button.content = "Guardar cambios"
        self.cancel_button.visible = True
        self.error.visible = False
        self._render_list()
        self._refresh()

    def delete(self, index: int):
        """Elimina index y reajusta la edición si se elimina una fila anterior."""
        self._individuals.pop(index)
        if self.editing_index == index:
            self._clear_form()
        elif self.editing_index is not None and index < self.editing_index:
            self.editing_index -= 1
            self.mode.value = f"Editar individuo {self.editing_index+1:02d}"
        self._render_list()
        self._emit_population_change()

    def cancel_edit(self, e=None):
        """Descarta los campos pendientes sin cambiar los individuos guardados."""
        self._clear_form()
        self._render_list()
        self._refresh()

    def _clear_form(self):
        """Restablece campos, mensajes y botones para agregar un individuo nuevo."""
        self.editing_index = None
        for input_field in self.fields:
            input_field.value = ""
        self.mode.value = "Nuevo individuo"
        self.save_button.content = "Agregar individuo"
        self.cancel_button.visible = False
        self.error.visible = False

    def _render_list(self):
        """Construye filas con callbacks que capturan el índice individual."""
        self.counter.value = f"{len(self._individuals)} individuos · {self.dimensions} {'variable' if self.dimensions == 1 else 'variables'}"
        self.items.controls = []
        if not self._individuals:
            self.items.controls = [ft.Container(content=ft.Text("Aún no hay individuos. Agrega uno o genera una población.", color=MUTED), padding=18, bgcolor=SOFT, border_radius=10)]
        for index, individual in enumerate(self._individuals):
            coordinates = "    ·    ".join(f"{label} = {value:.5g}" for label, value in zip(self.labels, individual))
            self.items.controls.append(ft.Container(content=ft.Row([
                ft.Text(f"{index+1:02d}", size=12, color=MUTED, width=28),
                ft.Text(coordinates, size=14, color=TEXT, expand=True),
                ft.IconButton(icon=ft.Icons.EDIT_OUTLINED, tooltip=f"Editar individuo {index+1}", icon_color=ACCENT, on_click=lambda e, i=index: self.edit(i)),
                ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, tooltip=f"Eliminar individuo {index+1}", icon_color=MUTED, on_click=lambda e, i=index: self.delete(i)),
            ], spacing=8), padding=8, bgcolor="#E9EFF6" if index == self.editing_index else SOFT, border_radius=10))

    def _emit_population_change(self):
        """Entrega una copia de los vectores al consumidor y solicita repintado."""
        if self._on_population_change:
            self._on_population_change(self.individuals)
        self._refresh()

    def _refresh(self):
        """Actualiza por callback o por la página si el control ya está montado."""
        if self._refresh_callback:
            self._refresh_callback()
        else:
            try:
                self.page
            except RuntimeError:
                # Antes de montar el componente sólo cambia el estado en memoria.
                return
            self.update()
