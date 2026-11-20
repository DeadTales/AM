"""Formularios para editar instancias TSP y de asignación sin cambiar archivos."""
import math

import flet as ft

from models.categorical import AssignmentProblem, TSPProblem, get_problem
from views.theme import ERROR, MUTED, field


TSP_DEFINITION = (
    "Representación: permutación de índices de ciudades (0, 1, 2…). Cada índice identifica "
    "una ciudad de la tabla. Se visita cada ciudad una vez y se regresa al inicio. "
    "Objetivo: minimizar la suma de distancias euclidianas del recorrido cerrado."
)
ASSIGNMENT_DEFINITION = (
    "Representación: vector de índices de recursos (0, 1, 2…). La posición i corresponde "
    "a la tarea i y su valor indica el recurso asignado. Cada tarea usa un recurso y la "
    "suma de demandas por recurso debe respetar su capacidad. Objetivo: minimizar la "
    "suma de costos; el motor penaliza las soluciones que exceden capacidades."
)


class CategoricalEditor(ft.Column):
    """Mantiene los datos de ambos problemas al alternar el selector."""

    def __init__(self, on_change, on_refresh):
        super().__init__(spacing=12)
        self._on_change, self._on_refresh = on_change, on_refresh
        self.problem = ft.Dropdown(
            label="Problema a resolver", value="tsp",
            options=[ft.DropdownOption(key="tsp", text="Agente viajero (TSP)"),
                     ft.DropdownOption(key="assignment", text="Asignación de tareas")],
            on_select=self.change_problem,
        )
        self.definition = ft.Text(TSP_DEFINITION, color=MUTED)
        self.message = ft.Text(color=ERROR, visible=False)
        self.cities = []
        self.start = ft.Dropdown(label="Ciudad inicial", on_select=self._edited, width=240)
        self.city_rows = ft.Column(spacing=8)
        self.add_city_button = ft.TextButton("Agregar ciudad", icon=ft.Icons.ADD, on_click=self.add_city)
        self.tsp_section = ft.Column([
            ft.Row([self.start, self.add_city_button], wrap=True),
            ft.Text("Entre 3 y 60 ciudades. Los nombres y las coordenadas deben ser distintos.", size=12),
            self._table_view(self.city_rows, 280),
        ], spacing=12)

        self.task_count = field("Número de tareas", "1", width=180)
        self.resource_count = field("Número de recursos", "1", width=180)
        self.resources = []
        self.tasks = []
        self.resource_rows = ft.Column(spacing=8)
        self.cost_rows = ft.Column(spacing=8)
        self.assignment_section = ft.Column([
            ft.Row([self.task_count, self.resource_count,
                    ft.TextButton("Ajustar tabla", on_click=self.resize_assignment)], wrap=True),
            ft.Text("Recursos y capacidades", weight=ft.FontWeight.W_600),
            self._table_view(self.resource_rows, 150),
            ft.Text("Tareas, demandas y matriz de costos", weight=ft.FontWeight.W_600),
            ft.Text("Cada columna R0, R1… corresponde al recurso con ese índice. Costos y demandas deben ser positivos.", size=12),
            self._table_view(self.cost_rows, 280),
        ], spacing=12, visible=False)
        for key in ("tsp", "assignment"):
            try:
                self._set_example(get_problem(key))
            except (ValueError, OSError) as error:
                self.message.value, self.message.visible = str(error), True
        self.controls = [self.problem, self.definition,
                         ft.TextButton("Restaurar ejemplo del problema", on_click=self.load_example),
                         self.message, self.tsp_section, self.assignment_section]

    @staticmethod
    def _table_view(rows, height):
        return ft.Column([ft.Container(content=ft.Row([rows], scroll=ft.ScrollMode.AUTO), padding=8)],
                         height=height, scroll=ft.ScrollMode.AUTO)

    def _entry(self, label, value, width=100):
        return field(label, str(value), width=width, on_change=self._edited)

    def _edited(self, event=None):
        self.message.visible = False
        self._on_change()

    def _error(self, error):
        self.message.value, self.message.visible = str(error), True
        self._on_refresh()

    def change_problem(self, event=None):
        tsp = self.problem.value == "tsp"
        self.tsp_section.visible, self.assignment_section.visible = tsp, not tsp
        self.definition.value = TSP_DEFINITION if tsp else ASSIGNMENT_DEFINITION
        self._edited()

    def _set_example(self, problem):
        if isinstance(problem, TSPProblem):
            self.cities = [(self._entry("Ciudad", name, 140), self._entry("x", x), self._entry("y", y))
                           for name, (x, y) in zip(problem.labels, problem.coordinates)]
            self.start.value = str(problem.start)
            self._render_cities()
        else:
            self.resources = [(self._entry("Recurso", name, 140), self._entry("Capacidad", capacity, 120))
                              for name, capacity in zip(problem.resource_labels, problem.capacities)]
            self.tasks = [(self._entry("Tarea", name, 140), self._entry("Demanda", demand),
                           [self._entry(f"R{r}", cost) for r, cost in enumerate(costs)])
                          for name, demand, costs in zip(problem.labels, problem.demands, problem.costs)]
            self.task_count.value, self.resource_count.value = str(problem.size), str(problem.resources)
            self._render_assignment()

    def load_example(self, event=None):
        try:
            # Solo sustituye el formulario después de cargar y validar correctamente.
            problem = get_problem(self.problem.value)
            self._set_example(problem)
            self._edited()
        except (ValueError, OSError) as error:
            self._error(error)

    def _render_cities(self):
        self.city_rows.controls = [
            ft.Row([ft.Text(str(index), width=24), *entries,
                    ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, tooltip="Quitar ciudad",
                                  disabled=len(self.cities) <= 3,
                                  on_click=lambda event, i=index: self.remove_city(i))])
            for index, entries in enumerate(self.cities)
        ]
        self.start.options = [ft.DropdownOption(key=str(i), text=f"Ciudad {i}") for i in range(len(self.cities))]
        if self.start.value not in {str(i) for i in range(len(self.cities))}:
            self.start.value = "0" if self.cities else None
        self.add_city_button.disabled = len(self.cities) >= 60

    def add_city(self, event=None):
        if len(self.cities) >= 60:
            return
        index = len(self.cities)
        name = self._unused_name("C", [row[0].value for row in self.cities])
        self.cities.append((self._entry("Ciudad", name, 140),
                            self._entry("x", index * 10), self._entry("y", 0)))
        self._render_cities()
        self._edited()

    def remove_city(self, index):
        if len(self.cities) <= 3:
            return
        start = int(self.start.value or "0")
        self.cities.pop(index)
        self.start.value = str(0 if index == start else start - (index < start))
        self._render_cities()
        self._edited()

    def _render_assignment(self):
        self.resource_rows.controls = [
            ft.Row([ft.Text(f"R{index}", width=32), name, capacity])
            for index, (name, capacity) in enumerate(self.resources)
        ]
        self.cost_rows.controls = [
            ft.Row([ft.Text(str(index), width=24), name, demand, *costs])
            for index, (name, demand, costs) in enumerate(self.tasks)
        ]

    @staticmethod
    def _unused_name(prefix, names):
        used = {(name or "").strip() for name in names}
        index = 1
        while f"{prefix}{index}" in used:
            index += 1
        return f"{prefix}{index}"

    def resize_assignment(self, event=None):
        try:
            task_count, resource_count = int(self.task_count.value), int(self.resource_count.value)
            if not 1 <= task_count <= 60 or not 1 <= resource_count <= 20:
                raise ValueError("Usa entre 1 y 60 tareas y entre 1 y 20 recursos.")
        except (TypeError, ValueError) as error:
            self._error(ValueError("Los tamaños deben ser enteros: 1–60 tareas y 1–20 recursos.")
                        if not str(error).startswith("Usa") else error)
            return
        resources = list(self.resources[:resource_count])
        for r in range(len(resources), resource_count):
            name = self._unused_name("R", [row[0].value for row in resources])
            resources.append((self._entry("Recurso", name, 140), self._entry("Capacidad", 100, 120)))
        tasks = []
        for i in range(task_count):
            if i < len(self.tasks):
                name, demand, old_costs = self.tasks[i]
                costs = list(old_costs[:resource_count])
            else:
                label = self._unused_name("T", [row[0].value for row in tasks])
                name, demand, costs = self._entry("Tarea", label, 140), self._entry("Demanda", 1), []
            costs.extend(self._entry(f"R{r}", 1) for r in range(len(costs), resource_count))
            tasks.append((name, demand, costs))
        self.resources, self.tasks = resources, tasks
        self.task_count.value, self.resource_count.value = str(task_count), str(resource_count)
        self._render_assignment()
        self._edited()

    @staticmethod
    def _number(control, label):
        try:
            value = float(control.value)
        except (TypeError, ValueError):
            raise ValueError(f"{label} debe ser un número.") from None
        if not math.isfinite(value):
            raise ValueError(f"{label} debe ser un número finito.")
        return value

    @staticmethod
    def _names(controls, label):
        names = tuple((control.value or "").strip() for control in controls)
        if not all(names) or len(set(names)) != len(names):
            raise ValueError(f"Los nombres de {label} deben estar completos y no repetirse.")
        return names

    def build_problem(self):
        """Construye una instancia inmutable con los datos editados y sus restricciones."""
        if self.problem.value == "tsp":
            names = self._names([row[0] for row in self.cities], "ciudades")
            coordinates = tuple((self._number(x, f"x de ciudad {i}"), self._number(y, f"y de ciudad {i}"))
                                for i, (_, x, y) in enumerate(self.cities))
            try:
                start = int(self.start.value)
            except (TypeError, ValueError):
                raise ValueError("Selecciona una ciudad inicial.") from None
            problem = TSPProblem(coordinates=coordinates, names=names, start=start)
        elif self.problem.value == "assignment":
            if (self.task_count.value != str(len(self.tasks))
                    or self.resource_count.value != str(len(self.resources))):
                raise ValueError("Pulsa Ajustar tabla para aplicar el número de tareas y recursos.")
            names = self._names([row[0] for row in self.tasks], "tareas")
            resources = self._names([row[0] for row in self.resources], "recursos")
            problem = AssignmentProblem(
                costs=tuple(tuple(self._number(cost, f"Costo de tarea {i}, recurso {r}")
                                  for r, cost in enumerate(costs)) for i, (_, _, costs) in enumerate(self.tasks)),
                demands=tuple(self._number(demand, f"Demanda de tarea {i}")
                              for i, (_, demand, _) in enumerate(self.tasks)),
                capacities=tuple(self._number(capacity, f"Capacidad de recurso {r}")
                                 for r, (_, capacity) in enumerate(self.resources)),
                task_names=names, resource_names=resources,
            )
        else:
            raise ValueError("Selecciona TSP o asignación.")
        problem.validate()
        return problem


def instance_summary(problem):
    """Texto de la instancia realmente ejecutada, independiente de ediciones posteriores."""
    if isinstance(problem, TSPProblem):
        lines = [f"Ciudad inicial: {problem.start} ({problem.labels[problem.start]})"]
        lines.extend(f"{i}: {name} · x={x:g}, y={y:g}"
                     for i, (name, (x, y)) in enumerate(zip(problem.labels, problem.coordinates)))
    else:
        lines = [f"R{r}: {name} · capacidad={capacity:g}"
                 for r, (name, capacity) in enumerate(zip(problem.resource_labels, problem.capacities))]
        lines.extend(f"Tarea {i}: {name} · demanda={demand:g} · costos=" + ", ".join(f"{cost:g}" for cost in costs)
                     for i, (name, demand, costs) in enumerate(zip(problem.labels, problem.demands, problem.costs)))
    return "\n".join(lines)
