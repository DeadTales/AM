"""Simulación didáctica PSO global-best para probar interfaz y parámetros; reemplazable."""
import random
from models.contracts import Generation, PSOConfig


class PSODemoEngine:
    """Referencia numérica para la interfaz; el motor PSO definitivo se conectará por run(config)."""
    is_demo = True

    def run(self, config: PSOConfig) -> list[Generation]:
        """Simula velocidad, memoria personal y atracción social con semilla reproducible.

        v = w*v + c1*r1*(pbest-x) + c2*r2*(gbest-x), x = x+v.
        Velocidad limitada al 20 % del dominio por eje. Al chocar con una cota,
        se fija la coordenada en esa cota y se anula su velocidad.
        """
        config.validate()
        objective = config.objective
        rng = random.Random(config.seed)
        positions = config.population
        velocities = [tuple(rng.uniform(-0.05*(hi-lo), 0.05*(hi-lo)) for lo, hi in objective.bounds) for _ in positions]
        personal_positions = list(positions)
        personal_scores = [objective.evaluate(vector) for vector in positions]
        result = [Generation(0, positions, tuple(personal_scores))]
        choose = max if objective.maximize else min
        for iteration in range(1, config.generations+1):
            leader = choose(range(len(positions)), key=lambda i: personal_scores[i])
            global_best = personal_positions[leader]
            updated = []
            for i, vector in enumerate(positions):
                next_vector, next_velocity = [], []
                for d, (x, (lo, hi)) in enumerate(zip(vector, objective.bounds)):
                    r1, r2 = rng.random(), rng.random()
                    velocity = config.inertia*velocities[i][d] + config.cognitive*r1*(personal_positions[i][d]-x) + config.social*r2*(global_best[d]-x)
                    limit = 0.2*(hi-lo)
                    velocity = max(-limit, min(limit, velocity))
                    candidate = x+velocity
                    coordinate = max(lo, min(hi, candidate))
                    next_vector.append(coordinate)
                    next_velocity.append(0.0 if coordinate != candidate else velocity)
                updated.append(tuple(next_vector))
                velocities[i] = tuple(next_velocity)
            positions = tuple(updated)
            scores = tuple(objective.evaluate(vector) for vector in positions)
            for i, score in enumerate(scores):
                improved = score > personal_scores[i] if objective.maximize else score < personal_scores[i]
                if improved:
                    personal_scores[i], personal_positions[i] = score, positions[i]
            result.append(Generation(iteration, positions, scores))
        return result
