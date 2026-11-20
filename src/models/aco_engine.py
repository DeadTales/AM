"""Motor de Colonia de Hormigas (ACO) para problemas categóricos: TSP y asignación de tareas.

Variante: Ant System con refuerzo elitista de la mejor solución encontrada.

En cada iteración:
  1. Cada hormiga construye una solución completa eligiendo, posición por posición, un valor j
     con probabilidad  p(j) = τ[i][j]^α · η[i][j]^β / Σ_k τ[i][k]^α · η[i][k]^β
       - TSP:        i = ciudad actual, j = ciudad siguiente no visitada, η = 1 / distancia.
       - Asignación: i = tarea,          j = recurso con capacidad libre,  η = 1 / costo.
  2. Se evalúa cada solución (distancia total o costo + penalización).
  3. Evaporación:  τ ← (1 − ρ) · τ
  4. Depósito:     cada hormiga suma Q / costo en los componentes que usó y la mejor
     solución global vuelve a depositar Q / mejor_costo (refuerzo elitista).

La salida sigue el mismo estilo que GA y PSO: list[Generation] con índice, soluciones
(population) y evaluaciones (scores). La iteración 0 son las soluciones construidas con la
feromona inicial uniforme, antes de cualquier depósito.
"""
import random
from models.categorical import AssignmentProblem, CategoricalSolution, TSPProblem
from models.contracts import ACOConfig, Generation

Matrix = list[list[float]]


class ACOEngine:
    """Implementa ACO mediante run(config); conserva la última feromona y el motivo de término."""
    is_demo = False

    def __init__(self):
        """Estado de la última ejecución, útil para mostrar resultados en la interfaz."""
        self.last_pheromone: Matrix = []
        self.stop_reason: str = ""

    def run(self, config: ACOConfig, should_stop=None) -> list[Generation]:
        """Ejecuta la colonia durante config.generations iteraciones.

        should_stop es opcional: una función sin argumentos que devuelve True para detener la
        ejecución antes de tiempo (botón Detener). En ese caso se devuelven solo las iteraciones
        completadas y stop_reason lo indica. Con config.patience > 0 también se detiene si el
        mejor costo no mejora en esa cantidad de iteraciones seguidas (convergencia anticipada).
        """
        # 1. Validar datos del problema y parámetros
        config.validate()
        problem = config.problem
        rng = random.Random(config.seed)

        # 2. Heurística η (fija) y feromona inicial τ0: la indicada por el usuario o, si es 0,
        #    una automática a partir de una solución voraz de referencia
        heuristic = self._heuristic(problem)
        if config.initial_pheromone > 0:
            tau0 = config.initial_pheromone
        else:
            reference = problem.evaluate(self._greedy(problem))
            tau0 = config.ants * config.q / reference
        pheromone = [[tau0] * len(row) for row in heuristic]

        best_solution: CategoricalSolution | None = None
        best_score = float("inf")
        stagnant = 0  # iteraciones seguidas sin mejorar el mejor costo (convergencia anticipada)
        generations: list[Generation] = []
        self.stop_reason = f"Límite de iteraciones alcanzado ({config.generations})."

        # 3. Iteración 0 (sin depósito previo) y ciclo principal 1..N
        for iteration in range(config.generations + 1):
            if should_stop is not None and should_stop():
                self.stop_reason = f"Detenido por el usuario en la iteración {iteration}."
                break

            # 3a. Construcción: cada hormiga arma una solución completa
            solutions = tuple(self._construct(problem, pheromone, heuristic, config, rng) for _ in range(config.ants))
            # 3b. Evaluación de cada solución
            scores = tuple(problem.evaluate(s) for s in solutions)
            generations.append(Generation(index=iteration, population=solutions, scores=scores))

            # 3c. Actualizar la mejor solución global (minimización)
            improved = False
            for solution, score in zip(solutions, scores):
                if score < best_score - 1e-12:
                    best_solution, best_score, improved = solution, score, True
            stagnant = 0 if improved else stagnant + 1

            # 3d. Convergencia anticipada: el mejor costo no mejoró en `patience` iteraciones seguidas
            if config.patience and stagnant >= config.patience and iteration < config.generations:
                self.stop_reason = (f"Convergencia anticipada en la iteración {iteration}: "
                                    f"sin mejora durante {config.patience} iteraciones.")
                break

            # 3e. Actualización de feromona: evaporación + depósito de cada hormiga + elitista
            self._evaporate(pheromone, config.rho, floor=tau0 * 1e-6)
            for solution, score in zip(solutions, scores):
                self._deposit(problem, pheromone, solution, config.q / score)
            self._deposit(problem, pheromone, best_solution, config.q / best_score)

        self.last_pheromone = pheromone
        return generations

    # ------------------------------------------------------------------
    # Construcción de soluciones
    # ------------------------------------------------------------------
    def _construct(self, problem, pheromone: Matrix, heuristic: Matrix, config: ACOConfig, rng: random.Random) -> CategoricalSolution:
        """Delegación según el tipo de problema."""
        if isinstance(problem, TSPProblem):
            return self._construct_route(problem, pheromone, heuristic, config, rng)
        return self._construct_assignment(problem, pheromone, heuristic, config, rng)

    def _construct_route(self, problem: TSPProblem, pheromone: Matrix, heuristic: Matrix, config: ACOConfig, rng: random.Random) -> CategoricalSolution:
        """Ruta que inicia en problem.start y visita cada ciudad una sola vez (lista tabú)."""
        route = [problem.start]
        unvisited = set(range(problem.size)) - {problem.start}
        while unvisited:
            current = route[-1]
            candidates = sorted(unvisited)
            weights = [pheromone[current][j] ** config.alpha * heuristic[current][j] ** config.beta for j in candidates]
            chosen = self._roulette(candidates, weights, rng)
            route.append(chosen)
            unvisited.remove(chosen)
        # El regreso al inicio es implícito: problem.evaluate suma el tramo final route[-1] → start
        return tuple(route)

    def _construct_assignment(self, problem: AssignmentProblem, pheromone: Matrix, heuristic: Matrix, config: ACOConfig, rng: random.Random) -> CategoricalSolution:
        """Asigna un recurso a cada tarea respetando la capacidad restante cuando es posible.

        Las tareas se recorren de mayor a menor demanda (las difíciles primero). Si ningún recurso
        tiene espacio, se elige entre todos y la penalización de evaluate() castiga el exceso.
        """
        remaining = list(problem.capacities)
        assignment = [0] * problem.size
        order = sorted(range(problem.size), key=lambda t: -problem.demands[t])
        for task in order:
            demand = problem.demands[task]
            candidates = [r for r in range(problem.resources) if remaining[r] + 1e-9 >= demand]
            if not candidates:
                candidates = list(range(problem.resources))
            weights = [pheromone[task][r] ** config.alpha * heuristic[task][r] ** config.beta for r in candidates]
            chosen = self._roulette(candidates, weights, rng)
            assignment[task] = chosen
            remaining[chosen] -= demand
        return tuple(assignment)

    @staticmethod
    def _roulette(candidates: list[int], weights: list[float], rng: random.Random) -> int:
        """Selección proporcional a los pesos; si todos son 0 elige al azar uniforme."""
        total = sum(weights)
        if total <= 0:
            return rng.choice(candidates)
        pick = rng.random() * total
        accumulated = 0.0
        for candidate, weight in zip(candidates, weights):
            accumulated += weight
            if pick <= accumulated:
                return candidate
        return candidates[-1]

    # ------------------------------------------------------------------
    # Feromona y heurística
    # ------------------------------------------------------------------
    @staticmethod
    def _heuristic(problem) -> Matrix:
        """η = 1/distancia (TSP, diagonal 0) o η = 1/costo (asignación)."""
        if isinstance(problem, TSPProblem):
            d = problem.distance_matrix()
            return [[0.0 if i == j else 1.0 / d[i][j] for j in range(problem.size)] for i in range(problem.size)]
        return [[1.0 / c for c in row] for row in problem.costs]

    @staticmethod
    def _evaporate(pheromone: Matrix, rho: float, floor: float) -> None:
        """τ ← (1 − ρ)·τ con un mínimo positivo para no anular ninguna opción."""
        for row in pheromone:
            for j, value in enumerate(row):
                row[j] = max(floor, (1.0 - rho) * value)

    @staticmethod
    def _deposit(problem, pheromone: Matrix, solution: CategoricalSolution, amount: float) -> None:
        """Suma amount en los componentes usados: aristas de la ruta o pares (tarea, recurso)."""
        if isinstance(problem, TSPProblem):
            closed = problem.closed_route(solution)
            for a, b in zip(closed, closed[1:]):
                pheromone[a][b] += amount
                pheromone[b][a] += amount  # TSP simétrico
        else:
            for task, resource in enumerate(solution):
                pheromone[task][resource] += amount

    @staticmethod
    def _greedy(problem) -> CategoricalSolution:
        """Solución voraz de referencia para escalar τ0 (vecino más cercano / recurso más barato)."""
        if isinstance(problem, TSPProblem):
            route = [problem.start]
            unvisited = set(range(problem.size)) - {problem.start}
            while unvisited:
                nearest = min(unvisited, key=lambda j: problem.distance(route[-1], j))
                route.append(nearest)
                unvisited.remove(nearest)
            return tuple(route)
        remaining = list(problem.capacities)
        assignment = [0] * problem.size
        for task in sorted(range(problem.size), key=lambda t: -problem.demands[t]):
            fits = [r for r in range(problem.resources) if remaining[r] + 1e-9 >= problem.demands[task]] or list(range(problem.resources))
            chosen = min(fits, key=lambda r: problem.costs[task][r])
            assignment[task] = chosen
            remaining[chosen] -= problem.demands[task]
        return tuple(assignment)


def best_solution(generations: list[Generation]) -> tuple[CategoricalSolution, float, int]:
    """Mejor solución de toda la ejecución, su evaluación y la iteración en que apareció."""
    best = (None, float("inf"), -1)
    for generation in generations:
        for solution, score in zip(generation.population, generation.scores):
            if score < best[1]:
                best = (solution, score, generation.index)
    return best


def best_history(generations: list[Generation]) -> tuple[float, ...]:
    """Mejor costo encontrado hasta cada iteración (curva de convergencia, no creciente)."""
    history: list[float] = []
    for generation in generations:
        current = min(generation.scores)
        history.append(min(history[-1], current) if history else current)
    return tuple(history)
