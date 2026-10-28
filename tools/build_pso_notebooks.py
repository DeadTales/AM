"""Genera guía PSO, análisis ejecutado y enlaces sin reescribir el contenido de capítulos previos."""
import ast
from base64 import b64encode
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT/"documentation_staging"/"AM"
EXTERNAL = ROOT.parent/"documentación"/"AM"
NEW = ("10_pso_simulacion_e_integracion", "11_pso_pruebas_y_analisis")
sys.path.insert(0, str(ROOT/"src"))


def md(text):
    """Construye celda Markdown a partir de texto con saltos de línea preservados."""
    return {"cell_type":"markdown", "metadata":{}, "source":text.splitlines(keepends=True)}


def code(text):
    """Construye celda Python ejecutable; las salidas se registran al generar el notebook."""
    return {"cell_type":"code", "metadata":{}, "source":text.splitlines(keepends=True), "execution_count":None, "outputs":[]}


SETUP = """from pathlib import Path
import sys
from dataclasses import replace

candidates = [Path.cwd(), *Path.cwd().parents]
project = next((base/'AM' for base in candidates if (base/'AM'/'src').is_dir()), None)
if project is None:
    project = next(base for base in candidates if (base/'src').is_dir())
sys.path.insert(0, str(project/'src'))
from models.contracts import PSOConfig, validate_generations
from models.demo_engine import initial_population
from models.objectives import FUNCTIONS, get_objective
from models.pso_demo_engine import PSODemoEngine
from models.pso_experiments import compare_parameters, export_trials, best_history
print('Proyecto:', project)
"""

guide = [md("""## Alcance de esta entrega
Se conserva el motor evolutivo existente y se añade **Partículas · PSO**. La palabra partículas se refiere a candidatos de solución, no a moléculas físicas. PSO usa las mismas cinco funciones que están actualmente en objectives.py: Seno oscilante y Exponencial simple en 1D (maximización), Ackley, Eggholder y Rosenbrock en 2D (minimización).

El motor activo de partículas es **PSODemoEngine**, una simulación didáctica con ecuaciones de velocidad y memoria, para probar interfaz y estudiar parámetros. No se presenta como implementación definitiva de la actividad: otra persona escribirá PSOEngine. Este último está reservado y lanza NotImplementedError hasta que se implemente. No se conecta automáticamente ni sustituye silenciosamente al motor real.

## Archivos y responsabilidades
| Archivo | Apartado | Propósito |
|---|---|---|
| src/views/application.py | OptimizationApp.__init__ | menú Evolutivo/PSO y conexión del motor |
| src/models/contracts.py | PSOConfig | entrada sin parámetros de genética |
| src/models/pso_demo_engine.py | PSODemoEngine.run | simulación numérica reemplazable |
| src/models/pso_engine.py | PSOEngine.run | **aquí se implementará el PSO definitivo** |
| src/models/pso_experiments.py | PSOTrial y funciones | registros, comparación y exportación |
| src/views/dashboard.py | settings, apply, compare_pso | captura de parámetros y ejecución fuera del hilo visual |
| src/views/pso_comparison.py | PSOComparison | gráficas de convergencia/dispersión y observaciones |
| tools/check_pso.py | comprobaciones | contrato, ecuación, sensibilidad y exportación |
| tools/check_pso_desktop.py | main | prueba del cliente real, capturas y navegación |

## Preparación
Selecciona el kernel Python del entorno AM. La celda localiza src desde la ubicación actual; si inicias el kernel en otra carpeta, establece project con la ruta absoluta del proyecto. No requiere abrir Flet para ejecutar el motor.
"""), code(SETUP), md("""## PSOConfig: cada parámetro
| Campo | Tipo | Uso |
|---|---|---|
| population | tuple de tuplas float | posiciones iniciales; cada vector tiene una o dos coordenadas |
| objective | Objective | función, fórmula, etiquetas, límites y maximize |
| generations | int | iteraciones; mantiene nombre compartido con el contrato de gráficas |
| inertia | float | w: conserva velocidad previa |
| cognitive | float | c1: atracción a la mejor posición propia |
| social | float | c2: atracción a la mejor del enjambre |
| seed | int | semilla local para velocidades y factores aleatorios |

La interfaz admite 2–200 partículas, 1–500 iteraciones, w entre 0 y 2 y c1/c2 entre 0 y 4. Son límites del formulario para experimentar, no una garantía matemática de estabilidad. validate() rechaza NaN, infinitos, coordenadas fuera de dominio y semillas inválidas. PSOConfig es dataclass(frozen=True): evita cambiar sus campos durante el cálculo. Tuplas protegen las coordenadas de modificación externa.

Generar población conserva la semilla 42 de la función initial_population existente. La semilla PSO controla las velocidades iniciales y los r1/r2 de movimiento. Cambiarla no cambia automáticamente las coordenadas de la lista; así puedes comparar exactamente la misma población.
"""), code("objective = get_objective('ackley')\npopulation = tuple(initial_population(20, objective))\nconfig = PSOConfig(population, objective, generations=40, inertia=0.7, cognitive=1.5, social=1.5, seed=42)\nconfig.validate()\nprint(config.objective.name, len(config.population), config.inertia, config.cognitive, config.social)"), md("""## Ecuación y recorrido de la simulación
Para cada coordenada de una partícula:

`v_nueva = w*v_anterior + c1*r1*(pbest-x) + c2*r2*(gbest-x)`

`x_nueva = x + v_nueva`

r1 y r2 son uniformes independientes entre 0 y 1; se extraen por partícula, dimensión e iteración. pbest es la mejor posición histórica de esa partícula. gbest se elige entre todas las memorias personales al comenzar la iteración. Para maximizar se escoge max; para minimizar min.

1. Se validan parámetros, se crea random.Random(seed) y se conservan posiciones iniciales.
2. Velocidades iniciales se muestrean en ±5 % de la amplitud de cada eje.
3. Se inicializan pbest y puntuaciones con la población inicial; se registra paso 0.
4. Se elige un gbest común antes de mover a las partículas: actualización síncrona.
5. Se calcula velocidad; se limita a ±20 % del ancho del dominio por eje.
6. Se actualizan posiciones. Una coordenada fuera del dominio se recorta a la cota y su velocidad se anula.
7. Se evalúa la población nueva y se actualiza cada memoria personal si mejoró estrictamente.
8. Se guarda Generation(index,population,scores). Se devuelven iteraciones+1 estados.

La función objetivo no se conoce de antemano como mínimo global: gbest es sólo la mejor solución que la simulación ha encontrado. El recorte y el límite de velocidad son políticas concretas de esta demostración. Si la persona encargada cambia esas políticas, debe documentarlas y mantenerlas constantes al comparar coeficientes.

En el primer paso pbest coincide con x; por eso el término cognitivo vale cero inicialmente. c1 influye cuando una partícula se aleja de su mejor posición histórica. No confundir c1=0 con ausencia completa de movimiento: quedan inercia y término social.

Fuente de la formulación: [documentación oficial de PySwarms, GlobalBestPSO](https://pyswarms.readthedocs.io/en/latest/api/pyswarms.single.html). No se instala ni utiliza PySwarms: la simulación está escrita en Python estándar.
"""), code("engine = PSODemoEngine()\nsnapshots = engine.run(config)\nvalidate_generations(snapshots, config)\nassert len(snapshots) == 41\nassert snapshots == engine.run(config)\nhistory = best_history(snapshots, objective.maximize)\nassert all(b <= a for a,b in zip(history,history[1:]))\nprint('Inicial:', history[0], 'mejor encontrado:', history[-1])"), md("""## Cómo leer el Python de este motor
`random.Random(seed)` crea estado aleatorio local: no afecta otros generadores de la app. `rng.random()` devuelve un float en [0,1). `rng.uniform(lo,hi)` muestrea una velocidad. `list(positions)` copia el contenedor exterior; los vectores internos son tuplas.

`for d,(x,(lo,hi)) in enumerate(zip(vector,bounds))` primero empareja coordenada y dominio; enumerate añade índice; los paréntesis desempaquetan los niveles. Es equivalente a recorrer d, leer x=vector[d] y leer lo,hi=bounds[d]. Como zip termina en el iterable más corto, se valida dimensión antes de usarlo.

`tuple(objective.evaluate(vector) for vector in positions)` consume un generador y construye una tupla de puntuaciones. No es una tupla que contiene un for: el for produce valores para el constructor. `max(-limit,min(limit,velocity))` aplica saturación. `a if condición else b` elige una expresión; `coordinate != candidate` detecta choque con una cota.

No se modifican coordenadas dentro de las tuplas: se construyen listas temporales con append, se transforman a tuplas y se sustituyen entradas de la lista velocities. personal_positions y personal_scores son listas editables para conservar memorias. La variable result es una lista de Generation inmutables.

## Integración exacta del motor que hará otra persona
1. Implementar **src/models/pso_engine.py → PSOEngine.run(config)**.
2. Recibir PSOConfig y respetar objetivo, maximize, límites, semilla y tamaño fijo.
3. Devolver list[Generation] con paso 0 y todas las iteraciones. El paso 0 conserva posiciones originales. scores contiene evaluación finita de cada vector en el mismo orden.
4. En **src/views/application.py** importar PSOEngine y cambiar únicamente la instancia del panel pso.

```python
from models.pso_engine import PSOEngine
# Dentro de self.panels:
'pso': Dashboard(page, engine=PSOEngine(), algorithm='pso')
```

No hace falta añadir selección, cruza o mutación a PSOConfig. No se vuelve a crear EvolutionEngine en contracts.py. El punto reservado usa is_demo=False; PSODemoEngine usa is_demo=True para que títulos, registros y exportaciones indiquen si se trata de simulación.

## Interfaz y flujo de Flet
OptimizationApp crea dos Dashboard persistentes. Menu/MenuItem de views/menu.py navega exclusivamente entre algoritmos, se conecta a Application.router.go y marca el activo mediante select(route). Su constructor recibe items y on_navigate; no tiene flecha Volver. Cada Dashboard crea Submenu/SubmenuItem de views/submenu.py para Configuración, Simulación / Resultados y Comparar pruebas de PSO. Submenu(items,on_navigate,on_back) tiene set_enabled(route,enabled), select(route,can_go_back=False), buttons y back_button. Su flecha recorre sólo el router del panel. Las dos clases heredan directamente Container y tienen estilos distintos: principal con fondo azul activo; submenú con superficie blanca y acento suave. No son dos instancias de la misma clase.

Cada nivel utiliza un ViewRouter independiente, conservando campos, etapa activa y resultados al cambiar de algoritmo. Cambiar de algoritmo pausa la reproducción anterior e invalida resultados pendientes, pero no mata un hilo de cálculo: una cancelación real requiere cooperación del motor. Los callbacks de botones capturan route=item.route para conservar la opción de cada iteración. Cada tipo de item es dataclass(frozen=True) con route,label,icon.

Dashboard.settings lee TextField.value (texto), convierte a float/int, valida y construye PSOConfig. apply usa await asyncio.to_thread(engine.run,config). render dibuja datos recibidos. PSO oculta genética y muestra w/c1/c2/semilla. El menú y las acciones permanecen fijos para ventanas pequeñas.

history es mejor valor acumulado. La lista y la gráfica espacial muestran partículas actuales, que pueden alejarse de gbest; por eso mejor actual y mejor acumulado pueden diferir. El historial ya calculado se reproduce con slider y botones: no es progreso en vivo del cálculo.

## PSOTrial y comparación
PSOTrial contiene name, config, history, spread, simulated y notes. history almacena mejor observado por iteración; spread es dispersión RMS respecto al centro del enjambre, normalizada por ancho de dominio y cantidad de dimensiones. No es velocidad ni error respecto al óptimo verdadero.

compare_parameters crea base y variantes bajas/altas de cada coeficiente, cambiando sólo uno. El incremento de w es 0.3 y de c1/c2 es 0.75; se recortan a los límites de formulario y se omite una variante si coincide con base. Por eso pueden aparecer menos de siete en valores extremos.

comparable exige misma función/fórmula, etiquetas, dominio, dirección, posiciones iniciales en el mismo orden, iteraciones y semilla. La UI también separa simulaciones y motor conectado. Mantiene hasta 40 registros recientes en memoria, sin cargar pruebas automáticamente al reiniciar. Cada ejecución manual añade un registro; la base de la serie puede duplicar una prueba manual idéntica y ambas curvas coincidirán.

PSOComparison construye dos gráficas y campos de observación. on_change de cada campo guarda notes en el registro capturado por lambda. Los botones exportan el grupo visible. CSV tiene una fila por prueba e iteración; JSON además conserva posiciones iniciales, dominio y fórmula. Salida en artifacts/pso_comparisons. Las observaciones sólo sobreviven al cierre si las exportas.

## Cómo interpretar sin inventar conclusiones
Mayor w conserva más velocidad y puede favorecer exploración; mayor c1 refuerza memoria personal y mayor c2 atracción social. Son mecanismos, no promesas de mejor convergencia. Mira tanto mejor valor como dispersión, y verifica oscilaciones recorriendo posiciones. Con velocidad saturada o choques de cota los efectos pueden quedar limitados. Una única semilla sirve para una comparación controlada, no para declarar un parámetro universalmente superior.
""")]

analysis = [md("""## Pruebas ejecutadas de la simulación
Este notebook registra resultados de **PSODemoEngine**, no del PSO definitivo pendiente. Son ejecuciones reproducibles, no datos inventados ni resultados de la persona que implementará el motor final. Se mantienen 20 partículas, 40 iteraciones, semilla 42 y posiciones iniciales idénticas entre variantes de cada función.

Se usa base w=0.7, c1=1.5 y c2=1.5. Las seis variantes son w=0.4/1.0, c1=0.75/2.25 y c2=0.75/2.25, cambiando una sola variable. No se comparan directamente valores absolutos de funciones diferentes: escalas, dominios y dirección son distintos.
"""), code(SETUP), code("groups = {}\nexports = []\nfor key in FUNCTIONS:\n    objective = get_objective(key)\n    base = PSOConfig(tuple(initial_population(20, objective)), objective, 40, 0.7, 1.5, 1.5, 42)\n    trials = compare_parameters(base, PSODemoEngine())\n    groups[key] = trials\n    exports.append(export_trials(trials, project/'artifacts'/'pso_examples'))\n    print('\\n'+objective.name, 'MAX' if objective.maximize else 'MIN', 'dominio:', objective.bounds)\n    print('Prueba          w    c1    c2      Inicial       Final     Dispersión final')\n    for t in trials:\n        c = t.config\n        print(f'{t.name:12} {c.inertia:4.2f} {c.cognitive:5.2f} {c.social:5.2f} {t.history[0]:12.6g} {t.history[-1]:12.6g} {t.spread[-1]:12.6g}')\nprint('\\nCSV y JSON generados en artifacts/pso_examples')"), md("""## Curvas por función
Cada gráfica compara el mejor valor acumulado encontrado por las siete variantes. La dirección correcta es subir en las dos funciones simples y bajar en las tres complejas. Curvas coincidentes pueden indicar una solución encontrada por varios parámetros o un efecto todavía no visible con esta semilla. No se presupone monotonicidad de la mejor **posición actual**, sólo de la memoria acumulada.
""")]
for key, label in (("sine_1d", "Seno oscilante"), ("exp_1d", "Exponencial simple"), ("ackley", "Ackley"), ("eggholder", "Eggholder"), ("rosenbrock", "Rosenbrock")):
    analysis.extend([md("### "+label), code(f"from matplotlib.figure import Figure\nfrom views.charts import _png\ntrials = groups[{key!r}]\nfigure = Figure(figsize=(8,4.5), dpi=100, layout='constrained')\naxes = figure.add_subplot(111)\nfor trial in trials:\n    c = trial.config\n    axes.plot(trial.history, label=f'{{trial.name}} ({{c.inertia:g}},{{c.cognitive:g}},{{c.social:g}})')\naxes.set_title(trials[0].config.objective.name+' · simulación PSO')\naxes.set_xlabel('Iteración')\naxes.set_ylabel('Mejor valor encontrado')\naxes.legend(fontsize=8)\naxes.grid(alpha=0.2)\n__display_png__ = _png(figure)")])
analysis.extend([md("""## Diferencias observadas respecto a la base
La siguiente celda calcula diferencias directamente de los registros. Ganancia positiva significa mejor resultado final que la base, teniendo en cuenta si la función maximiza o minimiza. No equivale a significancia estadística. Las diferencias de dispersión indican contracción o expansión relativa al final; no explican por sí solas toda la trayectoria.
"""), code("for key, trials in groups.items():\n    base = trials[0]\n    print('\\n'+base.config.objective.name)\n    direction = 1 if base.config.objective.maximize else -1\n    for trial in trials[1:]:\n        gain = direction*(trial.history[-1]-base.history[-1])\n        delta_spread = trial.spread[-1]-base.spread[-1]\n        print(f'{trial.name:10}: ganancia final={gain:+.6g}, diferencia de dispersión={delta_spread:+.6g}')"), md("""## Guía para tus observaciones
| Aspecto | Qué registrar |
|---|---|
| Inercia | cambios en avance y dispersión al mantener c1 y c2 constantes |
| Cognitivo | diferencias al cambiar sólo atracción a memoria personal |
| Social | rapidez de agrupamiento y estancamientos al cambiar sólo c2 |
| Oscilaciones | posiciones de partículas al recorrer iteraciones, no sólo curva acumulada |
| Constantes | función, dirección, dominio, posiciones, partículas, pasos, semilla, políticas de límites |
| Limitación | una semilla y una simulación de interfaz; repetir con más semillas y motor final |

## Repetición con otra semilla
Para estudiar variabilidad, repite el grupo con replace(base,seed=otra_semilla) conservando posiciones y los demás controles entre variantes del grupo. Si decides variar también posiciones iniciales, registra cada población y utiliza la misma dentro de ese nuevo grupo. No mezcles en una gráfica comparativa controlada registros con diferente semilla o dominio sin indicarlo.

## Exportación y persistencia
Los CSV y JSON anteriores contienen todos los parámetros, notas, historia y dispersión. La carpeta está ignorada por Git según la configuración actual. Guarda aparte los archivos que quieras entregar. Las gráficas incluidas en este notebook quedan guardadas como salidas y pueden verse sin ejecutar celdas.
""")])


def source_reference(cells):
    """Añade firmas, docstrings y código de los módulos nuevos para consulta detallada."""
    for relative in ("src/models/contracts.py", "src/models/pso_demo_engine.py", "src/models/pso_engine.py", "src/models/pso_experiments.py", "src/views/menu.py", "src/views/submenu.py", "src/views/application.py", "src/views/dashboard.py", "src/views/pso_comparison.py", "tools/check_pso.py", "tools/check_pso_desktop.py"):
        source = (ROOT/relative).read_text(encoding="utf-8")
        tree = ast.parse(source)
        sections = [f"## Referencia: {relative}\n{ast.get_docstring(tree)}"]
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                sections.append("### "+node.name+"\n```python\n"+ast.unparse(node).splitlines()[0]+"\n```\n"+(ast.get_docstring(node) or "Callback local."))
        sections.append("### Código completo\n```python\n"+source+"\n```")
        cells.append(md("\n\n".join(sections)))


def write_notebook(name, title, cells):
    """Ejecuta ejemplos propios, registra stdout/PNG y guarda notebook con IDs y enlaces."""
    names = sorted({path.stem for path in DEST.glob("*.ipynb")}|set(NEW))
    cells.insert(0, md("# "+title+"\n\n"+" · ".join(f"[{n}]({n}.ipynb)" for n in names)))
    namespace, count = {}, 0
    for index, cell in enumerate(cells):
        cell["id"] = f"{name[:2]}-cell-{index}"
        if cell["cell_type"] != "code":
            continue
        count += 1
        output = StringIO()
        with redirect_stdout(output):
            exec("".join(cell["source"]), namespace)
        cell["execution_count"] = count
        if output.getvalue():
            cell["outputs"].append({"output_type":"stream", "name":"stdout", "text":output.getvalue().splitlines(keepends=True)})
        png = namespace.pop("__display_png__", None)
        if png:
            cell["outputs"].append({"output_type":"display_data", "metadata":{}, "data":{"image/png":b64encode(png).decode(), "text/plain":["Gráfica de comparación de la simulación PSO"]}})
    notebook = {"nbformat":4, "nbformat_minor":5, "metadata":{"kernelspec":{"display_name":"Python 3 (AM)", "name":"python3", "language":"python"}, "language_info":{"name":"python"}}, "cells":cells}
    (DEST/(name+".ipynb")).write_text(json.dumps(notebook, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{name}: {count} celdas ejecutadas")


if __name__ == "__main__":
    DEST.mkdir(parents=True, exist_ok=True)
    # Conservar el contenido del usuario en los capítulos existentes; sólo añadir enlaces.
    existing = sorted(set(DEST.glob("*.ipynb"))|set(EXTERNAL.glob("*.ipynb")))
    for path in existing:
        if path.stem in NEW:
            continue
        origin = EXTERNAL/path.name if (EXTERNAL/path.name).exists() else path
        notebook = json.loads(origin.read_text(encoding="utf-8"))
        if not notebook.get("cells"):
            continue
        if path.stem == "03_controles":
            for cell in notebook["cells"]:
                if cell["cell_type"] != "markdown":
                    continue
                content = "".join(cell["source"])
                start, end = content.find("## Menú y router"), content.find("## PopulationEditor")
                if start >= 0 and end > start:
                    replacement = """## Menú principal, submenú y routers
Menu de views/menu.py permite cambiar entre algoritmos. MenuItem(route,label,icon) describe cada opción. Menu(items,on_navigate) recibe opciones y callback de selección; select(route) destaca el algoritmo activo con fondo azul. Esta clase no contiene Volver ni conoce las etapas de un algoritmo.

Submenu de views/submenu.py navega por Configuración, Simulación / Resultados y Comparar pruebas en PSO. SubmenuItem(route,label,icon) describe etapas. Submenu(items,on_navigate,on_back) recibe callbacks de navegación y regreso; set_enabled(route,enabled) controla acceso visual y select(route,can_go_back=False) destaca etapa y sincroniza flecha Volver. buttons almacena los botones por clave; back_button es la flecha. Su estilo es blanco con acento suave para distinguirlo del menú principal.

Las dos clases heredan Container por separado. Application.menu usa Menu y Dashboard.submenu usa Submenu. Cada nivel tiene un ViewRouter independiente: routes asocia controles a rutas; go(route) cambia visibilidad y conserva instancias; back() vuelve dentro de ese router. La flecha del Submenu sólo navega por etapas, sin cambiar de algoritmo. guards bloquea Resultados hasta tener datos; on_change sincroniza presentación. outlet aloja vistas y can_go_back consulta historial.

Al cambiar algoritmo se conservan parámetros, edición pendiente, resultados y etapa de cada panel, y se pausa reproducción. Para añadir un algoritmo se registra en OptimizationApp.panels y MenuItem. Para añadir una etapa se registra en Dashboard.routes y SubmenuItem.

"""
                    cell["source"] = (content[:start]+replacement+content[end:]).splitlines(keepends=True)
        text = "".join(notebook["cells"][0]["source"])
        if NEW[0]+".ipynb" not in text:
            text += "\n\nPSO: "+" · ".join(f"[{name}]({name}.ipynb)" for name in NEW)+"\n"
        notebook["cells"][0]["source"] = text.splitlines(keepends=True)
        (DEST/path.name).write_text(json.dumps(notebook, ensure_ascii=False, indent=2), encoding="utf-8")
    source_reference(guide)
    write_notebook(NEW[0], "PSO: simulación, parámetros e integración", guide)
    write_notebook(NEW[1], "PSO: pruebas controladas y resultados de simulación", analysis)
