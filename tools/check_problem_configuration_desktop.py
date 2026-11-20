"""Prueba del cliente Flet real para las tres representaciones.

Abre una ventana temporal, comprueba el flujo y guarda capturas en artifacts/.
Uso: python tools/check_problem_configuration_desktop.py
"""
import asyncio
import json
from pathlib import Path
import sys
import traceback

import flet as ft

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from models.aco_engine import best_solution
from views.application import OptimizationApp
from views.theme import ACCENT, BACKGROUND


async def main(page: ft.Page):
    folder = ROOT / "artifacts" / "problem_configuration_desktop"
    folder.mkdir(parents=True, exist_ok=True)
    errors, results = [], {}
    page.on_error = lambda event: errors.append(str(event.data))
    page.title = "Comprobación de tipos de problema"
    page.window.width, page.window.height = 1200, 960
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(color_scheme_seed=ACCENT)
    page.bgcolor, page.padding = BACKGROUND, 16
    app = OptimizationApp(page)
    capture = ft.Screenshot(content=ft.Container(content=app.build(), bgcolor=BACKGROUND, expand=True), expand=True)
    page.add(capture)

    async def shot(name):
        await asyncio.sleep(0.5)
        (folder / name).write_bytes(await asyncio.wait_for(capture.capture(), 15))

    try:
        app.router.go("de")
        continuous = app.panels["de"]
        continuous.function.value, continuous.dimensions.value = "sphere", "3"
        await continuous.function._trigger_event("select", None)
        continuous.optimization.value = "max"
        await continuous.optimization._trigger_event("select", None)
        for controls, interval in zip(continuous.bound_fields, ((1, 2), (-3, -1), (5, 6))):
            controls[0].value, controls[1].value = map(str, interval)
        continuous.size.value, continuous.generations.value = "8", "8"
        await continuous.apply_bounds_button._trigger_event("click", None)
        await shot("01_continuo_configuracion.png")
        await continuous.apply_button._trigger_event("click", None)
        assert continuous.config.objective.dimensions == 3 and continuous.config.objective.maximize
        assert continuous.config.objective.bounds == ((1, 2), (-3, -1), (5, 6))
        await shot("02_continuo_resultados.png")
        results["continuo"] = {"dimensiones": 3, "sentido": "max", "limites": continuous.config.objective.bounds}

        app.router.go("ais")
        binary = app.panels["ais"]
        binary.problem.value = "knapsack"
        await binary.problem._trigger_event("select", None)
        binary.weights.value, binary.values.value, binary.capacity.value = "2, 3, 4", "3, 4, 5", "5"
        binary.iterations.value, binary.population_size.value = "8", "12"
        page.update()
        await shot("03_mochila_configuracion.png")
        await binary.apply_button._trigger_event("click", None)
        assert binary.last_problem.weights == (2, 3, 4) and binary.result.weight <= 5
        await shot("04_mochila_resultados.png")
        results["mochila"] = {"vector": binary.result.vector, "valor": binary.result.value, "peso": binary.result.weight}

        app.router.go("aco")
        aco = app.panels["aco"]
        editor = aco.problem_editor
        for name, value in (("ants", "8"), ("generations", "8"), ("patience", "0")):
            aco.parameter_fields[name].value = value
        editor.cities[0][0].value, editor.cities[0][1].value = "Inicio ficticio", "-10"
        editor.start.value = "2"
        page.update()
        await shot("05_tsp_editor.png")
        await aco.btn_run._trigger_event("click", None)
        assert aco.config.problem.coordinates[0][0] == -10 and aco.config.problem.start == 2
        assert aco.generations, aco.lbl_status.value
        results["tsp"] = {"ciudades": aco.config.problem.size, "inicio": aco.config.problem.start,
                          "costo": best_solution(aco.generations)[1]}

        editor.problem.value = "assignment"
        await editor.problem._trigger_event("select", None)
        editor.task_count.value, editor.resource_count.value = "3", "2"
        editor.resize_assignment()
        for (name, capacity), label, limit in zip(editor.resources, ("Equipo A", "Equipo B"), (3, 5)):
            name.value, capacity.value = label, str(limit)
        for (_, demand, costs), row in zip(editor.tasks, ((1, 10), (2, 5), (7, 1))):
            demand.value = "2"
            for control, cost in zip(costs, row):
                control.value = str(cost)
        page.update()
        await aco.view.scroll_to(offset=0, duration=0)
        await shot("06_asignacion_editor.png")
        await aco.btn_run._trigger_event("click", None)
        assert aco.config.problem.capacities == (3, 5) and aco.generations, aco.lbl_status.value
        await aco.view.scroll_to(offset=1600, duration=0)
        await shot("07_asignacion_resultados.png")
        results["asignacion"] = {"costos": aco.config.problem.costs,
                                 "costo": best_solution(aco.generations)[1]}

        page.window.width, page.window.height = 760, 640
        await aco.view.scroll_to(offset=0, duration=0)
        page.update()
        await shot("08_editor_760x640.png")
        assert not errors, errors
        (folder / "report.json").write_text(json.dumps({"ok": True, "errors": errors, "resultados": results},
                                                       ensure_ascii=False, indent=2), encoding="utf-8")
        print("Cliente Flet real: continuos nD/max/límites, mochila, TSP y asignación editables correctos.", flush=True)
    except Exception:
        (folder / "failure.txt").write_text(traceback.format_exc(), encoding="utf-8")
        raise
    finally:
        await page.window.close()


if __name__ == "__main__":
    ft.run(main)
