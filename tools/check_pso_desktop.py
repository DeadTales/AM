"""Prueba con Flet real del menú Evolutivo/PSO, resultados y comparación."""
import asyncio
import json
from pathlib import Path
import sys
import traceback
import flet as ft

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
from views.application import OptimizationApp
from views.theme import ACCENT, BACKGROUND


async def main(page: ft.Page):
    """Captura las dos interfaces, ejecuta PSO y prueba cambiar sin perder datos."""
    folder = ROOT/"artifacts"/"pso_desktop_check"
    folder.mkdir(parents=True, exist_ok=True)
    errors = []
    page.on_error = lambda e: errors.append(str(e.data))
    page.title = "Comprobación · PSO y evolutivo"
    page.window.width, page.window.height = 1000, 780
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(color_scheme_seed=ACCENT)
    page.bgcolor, page.padding = BACKGROUND, 16
    app = OptimizationApp(page)
    capture = ft.Screenshot(content=ft.Container(content=app.build(), bgcolor=BACKGROUND, expand=True), expand=True)
    page.add(capture)

    async def shot(name):
        await asyncio.sleep(0.6)
        (folder/name).write_bytes(await asyncio.wait_for(capture.capture(), 15))

    try:
        await shot("01_evolutivo.png")
        await app.menu.buttons["pso"]._trigger_event("click", None)
        pso = app.panels["pso"]
        assert app.router.active == "pso"
        pso.generations.value = "6"
        pso.function.value = "ackley"
        await pso.function._trigger_event("select", None)
        await shot("02_pso_configuracion.png")
        await pso.apply_button._trigger_event("click", None)
        assert pso.router.active == "results", pso.message.value
        assert pso.config.objective.dimensions == 2
        await shot("03_pso_resultados.png")
        await pso.submenu.back_button._trigger_event("click", None)
        assert app.active == "pso" and pso.router.active == "config"
        await pso.submenu.buttons["results"]._trigger_event("click", None)
        await pso.submenu.buttons["comparison"]._trigger_event("click", None)
        await pso.comparison.compare_button._trigger_event("click", None)
        assert len(pso.comparison.trials) == 8, pso.comparison.status.value
        await shot("04_comparaciones.png")
        await app.menu.buttons["genetic"]._trigger_event("click", None)
        await app.menu.buttons["pso"]._trigger_event("click", None)
        assert pso.generations.value == "6" and pso.router.active == "comparison"
        await pso.submenu.buttons["config"]._trigger_event("click", None)
        page.window.width, page.window.height = 760, 640
        page.update()
        await shot("05_pso_760x640.png")
        assert not errors, errors
        (folder/"report.json").write_text(json.dumps({"ok":True, "errors":errors, "checks":["Menu entre algoritmos", "Submenu de etapas", "Volver local sin cambiar algoritmo", "PSO 2D", "Ocho registros de prueba", "Gráficas", "Estado conservado", "Ventana 760x640"]}, ensure_ascii=False, indent=2), encoding="utf-8")
        print("Cliente real: PSO, menú, comparación y capturas correctos.", flush=True)
    except Exception:
        (folder/"failure.txt").write_text(traceback.format_exc(), encoding="utf-8")
        raise
    finally:
        await page.window.close()


if __name__ == "__main__":
    ft.run(main)
