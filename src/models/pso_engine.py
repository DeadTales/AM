"""Punto reservado para que la persona encargada conecte el PSO definitivo."""
from models.contracts import Generation, PSOConfig


class PSOEngine:
    """Sustituye el cuerpo de run; no hereda ni ejecuta la simulación de la interfaz."""
    is_demo = False

    def run(self, config: PSOConfig) -> list[Generation]:
        """Implementar aquí PSO; devolver población y evaluaciones de los pasos 0..generations.

        config incluye population, objective, generations, inertia (w), cognitive (c1),
        social (c2) y seed. Respetar objective.maximize, bounds y tamaño de población.
        No modificar controles Flet desde este método.
        """
        raise NotImplementedError("Implementa tu PSO en src/models/pso_engine.py y conéctalo en src/views/application.py.")
