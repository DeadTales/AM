"""Motor de Optimización por Enjambre de Partículas (PSO) para funciones 1D y 2D."""
import random
from models.contracts import Generation, Individual, Objective, PSOConfig


class PSOEngine:
    """Implementa el algoritmo PSO (Global-Best) mediante el método run(config)."""
    is_demo = False

    def run(self, config: PSOConfig) -> list[Generation]:
        """Ejecuta el enjambre de partículas durante config.generations iteraciones.

        Ecuaciones por dimensión:
            V^(k+1) = w * V^k + c1 * r1 * (pbest - X^k) + c2 * r2 * (gbest - X^k)
            X^(k+1) = X^k + V^(k+1)
        """
        # 1. Validar que los parámetros (w, c1, c2, iteraciones, semilla y población) sean correctos
        config.validate()

        objective = config.objective
        maximize = objective.maximize
        rng = random.Random(config.seed)

        # 2. Estado inicial (Iteración k = 0)
        positions: tuple[Individual, ...] = tuple(config.population)
        scores: tuple[float, ...] = tuple(objective.evaluate(p) for p in positions)
        velocities: list[Individual] = self._init_velocities(len(positions), objective, rng)

        # 3. Inicializar memorias personales (pbest) con la posición y evaluación inicial
        pbest_positions: list[Individual] = list(positions)
        pbest_scores: list[float] = list(scores)

        # Guardar la generación/iteración 0 intacta (exigido por validate_generations)
        generations: list[Generation] = [
            Generation(index=0, population=positions, scores=scores)
        ]

        # 4. Ciclo principal de iteraciones (k = 1 hasta config.generations)
        for iteration in range(1, config.generations + 1):
            # Identificar la mejor posición global (gbest) entre todos los pbest actuales
            gbest_idx = self._best_index(pbest_scores, maximize)
            gbest_position = pbest_positions[gbest_idx]

            next_positions: list[Individual] = []
            next_velocities: list[Individual] = []

            # Actualizar velocidad y posición de cada partícula
            for i, current_pos in enumerate(positions):
                new_pos, new_vel = self._update_particle(
                    position=current_pos,
                    velocity=velocities[i],
                    pbest=pbest_positions[i],
                    gbest=gbest_position,
                    config=config,
                    objective=objective,
                    rng=rng,
                )
                next_positions.append(new_pos)
                next_velocities.append(new_vel)

            positions = tuple(next_positions)
            velocities = next_velocities
            scores = tuple(objective.evaluate(p) for p in positions)

            # 5. Actualizar el récord personal (pbest) de cada partícula si mejoró su evaluación
            for i, score in enumerate(scores):
                improved = (
                    score > pbest_scores[i]
                    if maximize
                    else score < pbest_scores[i]
                )
                if improved:
                    pbest_scores[i] = score
                    pbest_positions[i] = positions[i]

            generations.append(
                Generation(index=iteration, population=positions, scores=scores)
            )

        return generations

    def _init_velocities(
        self, pop_size: int, objective: Objective, rng: random.Random
    ) -> list[Individual]:
        """Genera velocidades iniciales aleatorias dentro del ±5 % del ancho del dominio."""
        velocities: list[Individual] = []
        for _ in range(pop_size):
            vel = tuple(
                rng.uniform(-0.05 * (high - low), 0.05 * (high - low))
                for low, high in objective.bounds
            )
            velocities.append(vel)
        return velocities

    def _best_index(self, scores: list[float] | tuple[float, ...], maximize: bool) -> int:
        """Obtiene el índice del mejor valor según si la función maximiza o minimiza."""
        if maximize:
            return max(range(len(scores)), key=lambda i: scores[i])
        return min(range(len(scores)), key=lambda i: scores[i])

    def _update_particle(
        self,
        position: Individual,
        velocity: Individual,
        pbest: Individual,
        gbest: Individual,
        config: PSOConfig,
        objective: Objective,
        rng: random.Random,
    ) -> tuple[Individual, Individual]:
        """Calcula V^(k+1) y X^(k+1) por coordenada aplicando límites de velocidad y dominio."""
        new_pos: list[float] = []
        new_vel: list[float] = []

        for d, (x_k, (low, high)) in enumerate(zip(position, objective.bounds)):
            v_k = velocity[d]
            r1 = rng.random()
            r2 = rng.random()

            # Ecuación de velocidad PSO: Inercia + Cognitivo + Social
            inertia_term = config.inertia * v_k
            cognitive_term = config.cognitive * r1 * (pbest[d] - x_k)
            social_term = config.social * r2 * (gbest[d] - x_k)
            v_next = inertia_term + cognitive_term + social_term

            # Límite de velocidad máxima (Vmax = 20 % del rango del eje) para evitar explosiones
            v_max = 0.2 * (high - low)
            v_next = max(-v_max, min(v_max, v_next))

            # Ecuación de posición: X^(k+1) = X^k + V^(k+1)
            candidate_x = x_k + v_next

            # Recorte (clamping) a los límites del dominio [-5, 5], [-512, 512], etc.
            clamped_x = max(low, min(high, candidate_x))
            new_pos.append(clamped_x)

            # Si la partícula chocó contra el borde del dominio, su velocidad en ese eje se frena a 0
            new_vel.append(0.0 if clamped_x != candidate_x else v_next)

        return tuple(new_pos), tuple(new_vel)