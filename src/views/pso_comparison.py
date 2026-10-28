"""Vista de pruebas PSO con gráficas, observaciones y exportación local."""
from pathlib import Path
import flet as ft
from matplotlib.figure import Figure
from models.pso_experiments import PSOTrial, export_trials
from views.charts import Chart, _png
from views.theme import ERROR, MUTED, SOFT, TEXT, card, field


class PSOComparison(ft.Column):
    """Registra pruebas de condiciones equivalentes; los datos conservan etiqueta de simulación."""

    def __init__(self, on_compare, on_refresh):
        """on_compare ejecuta serie controlada; on_refresh actualiza página al exportar."""
        super().__init__(spacing=18)
        self.trials = []
        self.refresh_page = on_refresh
        self.chart = Chart(height=470)
        self.chart.visible = False
        self.rows = ft.Column(spacing=12)
        self.status = ft.Text("Ejecuta una prueba PSO o compara parámetros desde la configuración.", color=MUTED)
        self.compare_button = ft.Button("Comparar w, c1 y c2", on_click=on_compare)
        self.export_button = ft.TextButton("Exportar CSV y JSON", on_click=self.export, disabled=True)
        self.controls = [card("Pruebas de partículas (PSO)", "Se conserva función, dominio, población inicial, iteraciones y semilla. Cada variante cambia un coeficiente.", [ft.Row([self.compare_button, self.export_button], wrap=True), self.status, self.chart, self.rows])]

    def set_trials(self, trials: list[PSOTrial]):
        """Dibuja mejor valor acumulado y dispersión; permite anotar observaciones por prueba."""
        self.trials = list(trials)
        self.rows.controls = []
        self.chart.visible = bool(trials)
        self.export_button.disabled = not trials
        if not trials:
            return
        config = trials[0].config
        mode = "simulación" if trials[0].simulated else "motor conectado"
        self.status.color = MUTED
        self.status.value = f"{len(trials)} pruebas · {mode} · {config.objective.name} · {len(config.population)} partículas · {config.generations} iteraciones · semilla {config.seed}. Una sola semilla no demuestra superioridad general."
        figure = Figure(figsize=(8, 5.3), dpi=100, layout="constrained", facecolor="white")
        convergence, diversity = figure.subplots(2, 1)
        for trial in trials:
            c = trial.config
            label = f"{trial.name}: w={c.inertia:g}, c1={c.cognitive:g}, c2={c.social:g}"
            convergence.plot(trial.history, label=label, linewidth=1.4)
            diversity.plot(trial.spread, linewidth=1.4)
            self.rows.controls.append(ft.Container(content=ft.Column([
                ft.Text(label, color=TEXT, size=14),
                ft.Text(f"Mejor encontrado: {trial.history[-1]:.7g} · Dispersión final: {trial.spread[-1]:.5g}", color=MUTED, size=12),
                field("Observaciones: convergencia, oscilación, exploración…", trial.notes, multiline=True, on_change=lambda e, record=trial: setattr(record, "notes", e.control.value)),
            ]), padding=14, bgcolor=SOFT, border_radius=10))
        convergence.set_ylabel("Mejor encontrado", fontsize=9)
        convergence.legend(fontsize=7, loc="best")
        diversity.set_ylabel("Dispersión normalizada", fontsize=9)
        diversity.set_xlabel("Iteración", fontsize=9)
        for axes in (convergence, diversity):
            axes.grid(alpha=0.2)
            axes.tick_params(labelsize=8)
        self.chart.set_image(_png(figure))

    def export(self, e=None):
        """Guarda únicamente el grupo visible en artifacts/pso_comparisons de este proyecto."""
        if not self.trials:
            return
        try:
            directory = Path(__file__).resolve().parents[2]/"artifacts"/"pso_comparisons"
            csv_path, json_path = export_trials(self.trials, directory)
            self.status.value = f"Archivos guardados: {csv_path} y {json_path.name}"
            self.status.color = MUTED
        except OSError as error:
            self.status.value, self.status.color = f"No se pudo exportar: {error}", ERROR
        self.refresh_page()
