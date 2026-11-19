"""Problemas categóricos predeterminados para Colonia de Hormigas (ACO).

Ambos problemas usan la misma representación: una solución es una tupla de enteros.

* TSP (viajante): permutación de ciudades. ``route[k]`` es la ciudad visitada en el paso k;
  la ruta empieza en ``start`` y al final regresa a ella (el último tramo es implícito).
* Asignación de tareas: ``assignment[i]`` es el recurso asignado a la tarea i.

Los datos de prueba están en data/tsp.json y data/asignacion.json y se leen con
``load_tsp()`` y ``load_assignment()``. Son editables: se modifica el JSON o se construye una
instancia nueva y se llama ``validate()`` antes de ejecutar el algoritmo.
Este módulo no depende de Flet ni de los contratos continuos.
"""
from dataclasses import dataclass
import json
import math
from pathlib import Path

CategoricalSolution = tuple[int, ...]
DATA_DIR = Path(__file__).resolve().parents[2] / "data"  # carpeta data/ en la raíz del proyecto

PROBLEMS = {
    "tsp": "Viajante (TSP)",
    "assignment": "Asignación de tareas a recursos",
}


def _finite(value) -> bool:
    """True si el valor es numérico y finito (rechaza bool, NaN e infinito)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


# ---------------------------------------------------------------------------
# Viajante (TSP)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class TSPProblem:
    """Ciudades con coordenadas (x, y); se minimiza la distancia euclidiana del recorrido cerrado."""
    coordinates: tuple[tuple[float, float], ...]
    names: tuple[str, ...] = ()
    start: int = 0
    kind: str = "tsp"
    name: str = PROBLEMS["tsp"]
    expression: str = "L(π) = Σ d(π_k, π_k+1) + d(π_n, π_1)   [Minimización]"
    maximize: bool = False

    @property
    def size(self) -> int:
        """Número de posiciones de la solución (= número de ciudades)."""
        return len(self.coordinates)

    @property
    def labels(self) -> tuple[str, ...]:
        """Nombre de cada ciudad; si no se dieron nombres se usan C1, C2, ..."""
        return self.names or tuple(f"C{i+1}" for i in range(self.size))

    def validate(self) -> None:
        """Exige 3–60 ciudades con coordenadas finitas, nombres coherentes e inicio válido."""
        if not 3 <= self.size <= 60:
            raise ValueError("El TSP requiere entre 3 y 60 ciudades.")
        for index, point in enumerate(self.coordinates):
            if len(point) != 2 or not all(_finite(v) for v in point):
                raise ValueError(f"La ciudad {index+1} debe tener coordenadas (x, y) numéricas y finitas.")
        if len(set(map(tuple, self.coordinates))) != self.size:
            raise ValueError("Hay ciudades repetidas con las mismas coordenadas.")
        if self.names and len(self.names) != self.size:
            raise ValueError("Debe haber un nombre por ciudad.")
        if not isinstance(self.start, int) or not 0 <= self.start < self.size:
            raise ValueError("La ciudad inicial no existe.")

    def distance(self, a: int, b: int) -> float:
        """Distancia euclidiana entre las ciudades a y b."""
        (x1, y1), (x2, y2) = self.coordinates[a], self.coordinates[b]
        return math.hypot(x1 - x2, y1 - y2)

    def distance_matrix(self) -> tuple[tuple[float, ...], ...]:
        """Matriz simétrica d[i][j] usada por la heurística η = 1/d."""
        return tuple(tuple(self.distance(i, j) for j in range(self.size)) for i in range(self.size))

    def check_route(self, route: CategoricalSolution) -> None:
        """Verifica que la ruta visite cada ciudad exactamente una vez y empiece en el inicio."""
        if len(route) != self.size or sorted(route) != list(range(self.size)):
            raise ValueError("La ruta debe visitar cada ciudad exactamente una vez.")
        if route[0] != self.start:
            raise ValueError("La ruta debe comenzar en la ciudad inicial.")

    def closed_route(self, route: CategoricalSolution) -> CategoricalSolution:
        """Ruta explícita que regresa al inicio, p. ej. (0, 3, 1, 2) → (0, 3, 1, 2, 0)."""
        return tuple(route) + (route[0],)

    def evaluate(self, route: CategoricalSolution) -> float:
        """Distancia total del recorrido cerrado (incluye el regreso a la ciudad inicial)."""
        self.check_route(route)
        closed = self.closed_route(route)
        return sum(self.distance(a, b) for a, b in zip(closed, closed[1:]))

    def is_feasible(self, route: CategoricalSolution) -> bool:
        """Toda permutación válida es factible en TSP."""
        try:
            self.check_route(route)
        except ValueError:
            return False
        return True

    def describe(self, route: CategoricalSolution) -> str:
        """Texto legible de la ruta cerrada: C1 → C4 → ... → C1."""
        return " → ".join(self.labels[c] for c in self.closed_route(route))


def load_tsp(path: str | Path = DATA_DIR / "tsp.json") -> TSPProblem:
    """Lee ciudades y coordenadas desde JSON: {"inicio": "A", "ciudades": [{"nombre", "x", "y"}, ...]}."""
    data = _read_json(path)
    try:
        cities = data["ciudades"]
        names = tuple(str(city["nombre"]) for city in cities)
        coordinates = tuple((float(city["x"]), float(city["y"])) for city in cities)
        start = names.index(str(data.get("inicio", names[0])))
    except (KeyError, TypeError, ValueError, IndexError) as error:
        raise ValueError(f"Formato inválido en {path}: se esperan 'ciudades' con nombre, x, y e 'inicio' existente.") from error
    problem = TSPProblem(coordinates=coordinates, names=names, start=start)
    problem.validate()
    return problem


def default_tsp() -> TSPProblem:
    """Ejemplo precargado de 10 ciudades leído de data/tsp.json (coordenadas editables)."""
    return load_tsp()


# ---------------------------------------------------------------------------
# Asignación de tareas a recursos (asignación generalizada)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class AssignmentProblem:
    """costs[i][r]: costo de que el recurso r haga la tarea i.

    demands[i] es la carga de la tarea i y capacities[r] la carga máxima del recurso r.
    Restricción: para cada recurso r, Σ demands[i] (tareas con assignment[i] == r) ≤ capacities[r].
    Objetivo: minimizar Σ costs[i][assignment[i]].
    """
    costs: tuple[tuple[float, ...], ...]
    demands: tuple[float, ...]
    capacities: tuple[float, ...]
    task_names: tuple[str, ...] = ()
    resource_names: tuple[str, ...] = ()
    kind: str = "assignment"
    name: str = PROBLEMS["assignment"]
    expression: str = "C(a) = Σ_i costo[i][a_i]  s.a. Σ_{i: a_i=r} demanda_i ≤ capacidad_r   [Minimización]"
    maximize: bool = False

    @property
    def size(self) -> int:
        """Número de posiciones de la solución (= número de tareas)."""
        return len(self.costs)

    @property
    def resources(self) -> int:
        """Número de valores posibles por posición (= número de recursos)."""
        return len(self.capacities)

    @property
    def labels(self) -> tuple[str, ...]:
        """Nombre de cada tarea (posición de la solución)."""
        return self.task_names or tuple(f"T{i+1}" for i in range(self.size))

    @property
    def resource_labels(self) -> tuple[str, ...]:
        """Nombre de cada recurso (valor que puede tomar una posición)."""
        return self.resource_names or tuple(f"R{r+1}" for r in range(self.resources))

    def validate(self) -> None:
        """Exige tamaños coherentes, costos > 0, demandas > 0, capacidades ≥ 0 y una asignación posible."""
        if not 1 <= self.size <= 60:
            raise ValueError("La asignación requiere entre 1 y 60 tareas.")
        if not 1 <= self.resources <= 20:
            raise ValueError("La asignación requiere entre 1 y 20 recursos.")
        for i, row in enumerate(self.costs):
            if len(row) != self.resources:
                raise ValueError(f"La tarea {i+1} necesita un costo por recurso ({self.resources}).")
            if not all(_finite(c) and c > 0 for c in row):
                raise ValueError(f"Los costos de la tarea {i+1} deben ser números positivos.")
        if len(self.demands) != self.size or not all(_finite(d) and d > 0 for d in self.demands):
            raise ValueError("Debe haber una demanda positiva por tarea.")
        if not all(_finite(c) and c >= 0 for c in self.capacities):
            raise ValueError("Las capacidades deben ser números no negativos.")
        if self.task_names and len(self.task_names) != self.size:
            raise ValueError("Debe haber un nombre por tarea.")
        if self.resource_names and len(self.resource_names) != self.resources:
            raise ValueError("Debe haber un nombre por recurso.")
        if sum(self.demands) > sum(self.capacities):
            raise ValueError("La demanda total supera la capacidad total: no existe asignación factible.")
        if max(self.demands) > max(self.capacities):
            raise ValueError("Hay una tarea que no cabe en ningún recurso.")

    def check_assignment(self, assignment: CategoricalSolution) -> None:
        """Verifica longitud y que cada valor sea un índice de recurso existente."""
        if len(assignment) != self.size:
            raise ValueError(f"La asignación requiere {self.size} posiciones (una por tarea).")
        if any(not isinstance(r, int) or not 0 <= r < self.resources for r in assignment):
            raise ValueError("Cada posición debe contener un recurso existente.")

    def loads(self, assignment: CategoricalSolution) -> tuple[float, ...]:
        """Carga total asignada a cada recurso."""
        totals = [0.0] * self.resources
        for task, resource in enumerate(assignment):
            totals[resource] += self.demands[task]
        return tuple(totals)

    def overflow(self, assignment: CategoricalSolution) -> float:
        """Suma de excesos sobre la capacidad; 0 significa que respeta las restricciones."""
        return sum(max(0.0, load - cap) for load, cap in zip(self.loads(assignment), self.capacities))

    def is_feasible(self, assignment: CategoricalSolution) -> bool:
        """True si ningún recurso supera su capacidad."""
        self.check_assignment(assignment)
        return self.overflow(assignment) <= 1e-9

    def total_cost(self, assignment: CategoricalSolution) -> float:
        """Costo puro Σ costs[i][a_i], sin penalización."""
        self.check_assignment(assignment)
        return sum(self.costs[task][resource] for task, resource in enumerate(assignment))

    @property
    def penalty(self) -> float:
        """Penalización por unidad de exceso: mayor que cualquier costo total posible."""
        return sum(max(row) for row in self.costs) + 1.0

    def evaluate(self, assignment: CategoricalSolution) -> float:
        """Costo + penalización·exceso. Una solución factible siempre vale menos que una infactible."""
        cost = self.total_cost(assignment)
        excess = self.overflow(assignment)
        return cost + (self.penalty * (1.0 + excess) if excess > 1e-9 else 0.0)

    def describe(self, assignment: CategoricalSolution) -> str:
        """Texto legible: T1→R2, T2→R1, ..."""
        return ", ".join(f"{self.labels[t]}→{self.resource_labels[r]}" for t, r in enumerate(assignment))


def load_assignment(path: str | Path = DATA_DIR / "asignacion.json") -> AssignmentProblem:
    """Lee costos, demandas y capacidades desde JSON (ver data/asignacion.json)."""
    data = _read_json(path)
    try:
        problem = AssignmentProblem(
            costs=tuple(tuple(float(c) for c in row) for row in data["costos"]),
            demands=tuple(float(d) for d in data["demandas"]),
            capacities=tuple(float(c) for c in data["capacidades"]),
            task_names=tuple(str(t) for t in data.get("tareas", ())),
            resource_names=tuple(str(r) for r in data.get("recursos", ())),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"Formato inválido en {path}: se esperan 'costos', 'demandas' y 'capacidades' numéricos.") from error
    problem.validate()
    return problem


def default_assignment() -> AssignmentProblem:
    """Ejemplo precargado de 20 tareas y 5 recursos leído de data/asignacion.json (datos editables)."""
    return load_assignment()


def _read_json(path: str | Path) -> dict:
    """Abre un archivo JSON de datos de prueba con mensaje claro si no existe o está mal escrito."""
    try:
        with open(path, encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        raise ValueError(f"No se encontró el archivo de datos: {path}") from None
    except json.JSONDecodeError as error:
        raise ValueError(f"JSON inválido en {path}: {error}") from None


def get_problem(key: str):
    """Devuelve una copia del ejemplo predeterminado por clave ("tsp" o "assignment")."""
    if key == "tsp":
        return default_tsp()
    if key == "assignment":
        return default_assignment()
    raise ValueError(f"Problema categórico no reconocido: {key}")
