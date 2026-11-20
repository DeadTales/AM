"""Verificación visual de parámetros, mejor individuo, historial y exportaciones.

Abre un cliente temporal y guarda evidencias ficticias en artifacts/run_workflow_desktop/.
"""
import asyncio
import json
from pathlib import Path
import sys
import traceback

import flet as ft

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from views.application import OptimizationApp
from views.theme import ACCENT, BACKGROUND
SUCCESS = False


async def main(page: ft.Page):
    global SUCCESS
    folder = ROOT / "artifacts" / "run_workflow_desktop"
    folder.mkdir(parents=True, exist_ok=True)
    errors, exported = [], {}
    page.on_error = lambda event: errors.append(str(event.data))
    page.title = "Comprobación de parámetros y resultados"
    page.window.width, page.window.height = 1280, 1000
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(color_scheme_seed=ACCENT)
    page.bgcolor, page.padding = BACKGROUND, 16
    app = OptimizationApp(page)
    capture = ft.Screenshot(content=ft.Container(content=app.build(), bgcolor=BACKGROUND, expand=True), expand=True)
    page.add(capture)

    async def shot(name):
        await asyncio.sleep(0.5)
        (folder / name).write_bytes(await asyncio.wait_for(capture.capture(), 15))
        assert not errors, errors[-3:]

    async def save(kind, panel):
        panel.exporter.directory = folder / "exports" / kind
        previous = set(panel.exporter.directory.glob("*.json"))
        await panel.exporter.button._trigger_event("click", None)
        files = list(set(panel.exporter.directory.glob("*.json")) - previous)
        assert files, panel.exporter.status.value
        record = json.loads(files[-1].read_text(encoding="utf-8"))
        assert record["algorithm"] == kind and list(panel.exporter.directory.glob("*.csv"))
        exported[kind] = record["best"]

    try:
        for index, kind in enumerate(("genetic", "pso", "de")):
            app.router.go(kind)
            panel = app.panels[kind]
            panel.function.value, panel.dimensions.value = "sphere", "2"
            await panel.function._trigger_event("select", None)
            panel.size.value, panel.generations.value = "12", "8"
            if kind == "pso":
                panel.seed.value = "0"
            panel.configure()
            await panel.body.scroll_to(offset=500, duration=0)
            await shot(f"{index*2+1:02d}_{kind}_parametros.png")
            await panel.apply_button._trigger_event("click", None)
            assert panel.run_record, panel.message.value
            assert panel.index == 8
            assert panel.table.controls[0].content.controls[0].value == "Mejor encontrado"
            if kind == "pso":
                assert panel.displayed_best.fitness < min(panel.snapshots[-1].scores)
            await shot(f"{index*2+2:02d}_{kind}_mejor_primero.png")
            await save(kind, panel)

        app.problem_type.value = "binary"
        await app.problem_type._trigger_event("select", None)
        assert app.active == "ais"
        ais = app.panels["ais"]
        ais.population_size.value, ais.iterations.value = "12", "6"
        ais.cloning_rate.value, ais.mutation_rate.value, ais.selection_fraction.value = "0.5", "0.1", "0.5"
        page.update()
        await shot("07_ais_parametros.png")
        await ais.configuration_view.scroll_to(offset=360, duration=0)
        await shot("08_ais_parametros_inferiores.png")
        await ais.apply_button._trigger_event("click", None)
        assert ais.run_record and len(ais.generations) == 7, ais.message.value
        ais.browser.select(2)
        await shot("09_ais_historial.png")
        await save("ais", ais)
        await ais.reset_button._trigger_event("click", None)
        assert ais.result is None and ais.population_size.value == "12"

        app.problem_type.value = "categorical"
        await app.problem_type._trigger_event("select", None)
        assert app.active == "aco"
        aco = app.panels["aco"]
        for name, value in (("ants", "5"), ("generations", "6"), ("patience", "0")):
            aco.parameter_fields[name].value = value
        page.update()
        await aco.view.scroll_to(offset=650, duration=0)
        await shot("10_aco_parametros.png")
        await aco.btn_run._trigger_event("click", None)
        assert aco.run_record and len(aco.generations) == 7, aco.lbl_status.value
        aco.browser.select(2)
        await aco.view.scroll_to(offset=1300, duration=0)
        await shot("11_aco_historial.png")
        await save("aco", aco)
        await aco.view.scroll_to(offset=1100, duration=0)
        await shot("12_exportacion.png")

        page.window.width, page.window.height = 760, 640
        app.router.go("pso")
        app.panels["pso"].reset()
        await shot("13_760x640.png")
        assert not errors, errors
        (folder / "report.json").write_text(json.dumps({"ok": True, "errors": errors, "exportados": exported},
                                                       ensure_ascii=False, indent=2), encoding="utf-8")
        print("Cliente real: nombres por algoritmo, mejor primero, historial, reinicio y diez archivos exportados correctos.", flush=True)
        SUCCESS = True
    except Exception:
        (folder / "failure.txt").write_text(traceback.format_exc(), encoding="utf-8")
        raise
    finally:
        await page.window.close()


if __name__ == "__main__":
    ft.run(main)
    if not SUCCESS:
        raise SystemExit(1)
