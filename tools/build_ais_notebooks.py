"""Genera los capítulos de AIS y verifica sus ejemplos de Python."""
from base64 import b64encode
from contextlib import redirect_stdout
from io import BytesIO, StringIO
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "documentation_staging" / "AM"
CHAPTERS = {
    "12_ais_fundamentos": "AIS · Origen, conceptos y aplicaciones",
    "13_ais_formulas_y_problemas": "AIS · Fórmulas, OneMax y Mochila 0/1",
    "14_ais_codigo_y_pruebas": "AIS · Código, interfaz y pruebas reproducibles",
}
LINKS = " · ".join(f"[{title}]({name}.ipynb)" for name, title in CHAPTERS.items())


def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.strip().splitlines(keepends=True)}


def code(text):
    return {"cell_type": "code", "metadata": {}, "source": text.strip().splitlines(keepends=True),
            "execution_count": None, "outputs": []}


def source(relative):
    """Incluye el archivo vigente como referencia de lectura."""
    path = ROOT / relative
    return md(f"### `{relative}`\n\n```python\n{path.read_text(encoding='utf-8')}\n```")


FOUNDATIONS = [md("""
## Qué es un sistema inmunitario artificial

Un **sistema inmunitario artificial** (*Artificial Immune System*, AIS) es un método computacional inspirado en principios del sistema inmunitario. El campo surgió al estudiar cómo trasladar ideas como reconocimiento de patrones, respuesta selectiva, diversidad y memoria a problemas de informática. En optimización, la idea se aplica a una población de soluciones candidatas que se evalúan y refinan de forma repetida. AIS reúne varias familias de algoritmos. [De Castro y Timmis, *Artificial Immune Systems: A New Computational Approach*, 2002](https://www.cs.kent.ac.uk/pubs/2002/1507/).

## De dónde viene la selección clonal

En **1957**, Frank Macfarlane Burnet propuso una teoría para explicar la especificidad de la respuesta adaptativa. En una descripción simplificada, un antígeno favorece la activación de células con receptores que ya pueden reconocerlo. Las células seleccionadas proliferan y originan clones. En las respuestas de células B pueden surgir variantes que, tras selección, contribuyen a aumentar la afinidad. Parte de la respuesta también puede persistir como memoria inmunitaria. [Contexto histórico y reimpresión de Burnet en *Nature Immunology*](https://www.nature.com/articles/ni1007-1009).

En **2002**, Leandro N. de Castro y Fernando J. Von Zuben publicaron **CLONALG**, un algoritmo que traslada la selección clonal y la maduración de afinidad a problemas de reconocimiento de patrones y optimización. Su trabajo estudia variantes para búsqueda multimodal y combinatoria. El motor de este proyecto toma esa idea y concreta una regla de clonación por rango, una tasa de mutación por bit y una reparación para Mochila. Las fórmulas del capítulo 13 describen este código. [De Castro y Von Zuben, *Learning and Optimization Using the Clonal Selection Principle*, 2002](https://doi.org/10.1109/TEVC.2002.1011539).

## Conceptos clave y su traducción en el proyecto

| Concepto | Idea en la analogía | Cómo se representa aquí |
| --- | --- | --- |
| Antígeno | Aquello que se reconoce | La tarea de encontrar una solución que puntúe alto bajo reglas dadas |
| Anticuerpo | Receptor con cierta capacidad de reconocimiento | Candidato representado por una tupla de bits |
| Afinidad | Grado de correspondencia | Cantidad de unos en OneMax o valor total factible en Mochila |
| Selección clonal | Proliferación de candidatos seleccionados | Se ordena por valor y se clona el cuarto superior de la población |
| Hipermutación | Introducción de variantes en los clones | Cada bit puede invertirse y su probabilidad depende de la afinidad |
| Maduración de afinidad | Ciclos de variación y selección | Se evalúan los clones y compiten con la población anterior |
| Memoria | Conservación de información sobre una respuesta | El mejor candidato se preserva en la población y su valor se registra |
| Diversidad | Presencia de alternativas | Se reservan lugares para candidatos aleatorios en cada ciclo |
| Factibilidad | Restricciones del problema computacional | Una mochila que supera la capacidad se repara antes de puntuarla |

La analogía guía el diseño. En el programa, la afinidad es un número calculado a partir del problema y la memoria consiste en preservar soluciones que ya se evaluaron. El algoritmo combina **explotación**, al refinar candidatos prometedores, con **exploración**, al probar clones, mutaciones e individuos nuevos.

## Familias y aplicaciones

| Área | Qué se intenta resolver | Ejemplo publicado o relación con el proyecto |
| --- | --- | --- |
| Optimización | Encontrar una configuración de alta calidad en un espacio grande | De Castro y Von Zuben estudiaron optimización multimodal y combinatoria con CLONALG. El proyecto usa selección clonal para OneMax y Mochila 0/1. [Artículo de CLONALG](https://www.cs.unm.edu/~forrest/classes/immuno-class/readings/DeCastro.pdf) |
| Detección de cambios | Reconocer patrones que se apartan de una referencia | Forrest y sus coautores estudiaron detección de cambios mediante discriminación propio/ajeno. Es una línea asociada a **selección negativa**. [Forrest et al., 1994](https://conferences.computer.org/sp/pdfs/sp/1994/00044264.pdf) |
| Clasificación supervisada | Asignar una etiqueta a una observación a partir de ejemplos etiquetados | **AIRS** estudia reconocimiento con prototipos y memoria. [Watkins, Timmis y Boggess, 2004](https://kar.kent.ac.uk/14200/) |
| Análisis de datos | Representar estructuras y relaciones entre observaciones | Las **redes inmunes artificiales** modelan interacciones entre unidades y se han estudiado en herramientas de análisis de datos. [Timmis, Neal y Hunt, 2000](https://pure.york.ac.uk/portal/en/publications/an-artificial-immune-system-for-data-analysis/) |

Mochila 0/1 modela decisiones indivisibles como seleccionar pedidos, componentes o tareas con un límite de recurso, siempre que los consumos y beneficios sean aditivos. Un mismo objeto puede seleccionarse una sola vez. Para problemas con dependencias o varios recursos, habría que representar y validar esas restricciones adicionales.

## Comparación con los algoritmos de la aplicación

| Algoritmo | Movimiento o variación | Información que conserva |
| --- | --- | --- |
| AIS de este proyecto | Clonación por rango e inversión de bits según afinidad | Candidatos de alto valor y mejor valor acumulado |
| Evolutivo de la aplicación | Selección de padres, cruza y mutación | Población y mejor individuo por elitismo |
| PSO de la aplicación | Actualización de posición mediante una velocidad | Mejor posición personal y mejor posición del enjambre |

La navegación de la app es compartida y cada panel configura su propio motor. En AIS las opciones son **OneMax y Mochila 0/1** y las unidades son bits. Evolutivo y PSO usan el registro de funciones continuas de la actividad anterior. En la literatura, adaptar selección clonal a otro dominio requiere definir cómo representar y mutar sus soluciones. [CLONALG, secciones de optimización](https://www.cs.unm.edu/~forrest/classes/immuno-class/readings/DeCastro.pdf).

## Cuándo tiene sentido aplicarlo

La selección clonal puede ser útil cuando se puede evaluar una solución y generar variaciones, y explorar el espacio exhaustivamente resulta costoso. La afinidad permite ordenar soluciones sin derivadas. La población permite trabajar con varias alternativas a la vez. La eficacia depende de la representación, la mutación, el tratamiento de restricciones y el presupuesto de evaluaciones.

OneMax permite comprobar la lógica porque su óptimo es conocido. Mochila permite practicar restricciones de capacidad y distinguir una solución factible del óptimo. Para instancias de mochila pequeñas, la enumeración sirve como verificación. En instancias con pesos enteros y una capacidad moderada, la programación dinámica es una opción exacta. La selección clonal entrega el mejor candidato evaluado dentro del presupuesto y conviene comparar varias semillas antes de afirmar que una configuración suele funcionar mejor.
""")]


FORMULAS = [md(r"""
## Representación de un candidato

Un vector $x=(x_1,\ldots,x_L)$ tiene $L$ posiciones y $x_i\in\{0,1\}$. Hay $2^L$ vectores posibles. La afinidad $f(x)$ es el valor que el motor maximiza. El mejor candidato es el de mayor $f(x)$ entre los evaluados y admitidos por las reglas del problema.

| Símbolo | Significado | Campo del código |
| --- | --- | --- |
| $L$ | Longitud del vector | `problem.length` |
| $N$ | Tamaño de la población | `config.population_size` |
| $T$ | Iteraciones después de la inicialización | `config.iterations` |
| $M$ | Máximo de clones del candidato de primer rango | `config.max_clones` |
| $f(x)$ | Valor que se maximiza | `problem.evaluate(x)` |
| $B$ | Capacidad de la mochila | `problem.capacity` |
"""), md(r"""
## OneMax

Se maximiza el número de unos en un vector de longitud elegida por el usuario.

$$
\max_{x\in\{0,1\}^L} f_{\mathrm{OneMax}}(x),\qquad
f_{\mathrm{OneMax}}(x)=\sum_{i=1}^{L}x_i.
$$

Por ejemplo, si $x=(1,0,1,1,0)$, el valor es $1+0+1+1+0=3$. Como cada bit aporta como máximo uno, el valor óptimo es $L$ y se alcanza con $x=(1,\ldots,1)$. En Python, `OneMax.evaluate()` valida la longitud y los bits y luego devuelve `sum(vector)`.
"""), code("""
x = (1, 0, 1, 1, 0)
assert sum(x) == 3
print(f"OneMax para {x}: {sum(x)} unos de {len(x)} bits")
"""), md(r"""
## Mochila 0/1

Para cada objeto $i$, $w_i>0$ es su peso y $v_i\ge 0$ su valor. $x_i=1$ indica inclusión y $x_i=0$ exclusión. La capacidad $B\ge 0$ limita la suma de los pesos.

$$
\begin{aligned}
\max_{x}\quad & f_{\mathrm{Mochila}}(x)=\sum_{i=1}^{L} v_i x_i,\\
\text{sujeto a}\quad & W(x)=\sum_{i=1}^{L} w_i x_i\le B,\\
& x_i\in\{0,1\}.
\end{aligned}
$$

**Evaluación manual del ejemplo.** Con pesos $(2,3,4,5,7,8,9,10)$, valores $(6,8,9,10,13,14,17,18)$ y $B=17$, el vector $(1,1,1,0,0,1,0,0)$ incluye los objetos 1, 2, 3 y 6. Su peso es $2+3+4+8=17$ y su valor es $6+8+9+14=37$. Por lo tanto, es factible. La prueba del capítulo 14 comprueba además si alcanza el óptimo.

**Reparación.** Si se añade también el objeto 4, el peso pasa a $22$. El código mezcla los índices seleccionados y retira objetos hasta que $W\le B$. Si el primer objeto retirado fuera el 4, recuperaría el vector factible anterior. Con otro orden puede llegar a una mochila factible de distinto valor. La reparación prioriza el cumplimiento de capacidad. Después, `Knapsack.evaluate()` vuelve a comprobar la restricción y suma los valores.
"""), code("""
weights = (2, 3, 4, 5, 7, 8, 9, 10)
values = (6, 8, 9, 10, 13, 14, 17, 18)
x = (1, 1, 1, 0, 0, 1, 0, 0)
weight = sum(w * bit for w, bit in zip(weights, x))
value = sum(v * bit for v, bit in zip(values, x))
assert weight == 17 and value == 37
print(f"Mochila {x} · peso {weight}/17 · valor {value}")
"""), md(r"""
## Reglas de selección clonal implementadas

### 1. Inicialización y orden

Se construyen $N$ vectores aleatorios de longitud $L$. `getrandbits(1)` genera cada bit. Si el problema es Mochila, cada vector se repara cuando hace falta. Los candidatos se ordenan de mayor a menor valor. La población inicial se registra como iteración 0.

### 2. Selección, rango y número de clones

Se seleccionan los $S$ primeros candidatos de la población ordenada. Para una población de tamaño $N$ y un candidato de rango $r$ con $r=1$ para el primero:

$$
S=\max\left(1,\left\lfloor \frac{N}{4}\right\rfloor\right),\qquad
k_r=\max\left(1,\left\lfloor \frac{M}{r}\right\rfloor\right).
$$

En Python, `//` devuelve la división entera para estos tamaños positivos. Con $N=32$ y $M=8$, se seleccionan ocho candidatos, que producen $(8,4,2,2,1,1,1,1)$ clones. Los empates de valor mantienen el orden anterior porque `sort` y `sorted` son estables. Dos candidatos empatados pueden tener distinto rango y número de clones.

### 3. Afinidad relativa y tasa de mutación

Sean $f_{\max}$ y $f_{\min}$ los valores extremos de **toda** la población al inicio de esa iteración. La afinidad relativa $a(x)$ está entre 0 y 1. Su valor se toma como 1 si todos los candidatos tienen el mismo valor.

$$
a(x)=\begin{cases}
\dfrac{f(x)-f_{\min}}{f_{\max}-f_{\min}}, & f_{\max}>f_{\min},\\[4pt]
1, & f_{\max}=f_{\min}.
\end{cases}
\qquad
p(x)=\min\left(1,\frac{1+3\bigl(1-a(x)\bigr)}{L}\right).
$$

Para cada clon y cada bit se obtiene un valor pseudoaleatorio $u_i\in[0,1)$ y se usa la regla siguiente:

$$
x'_i=\begin{cases}
1-x_i,&u_i<p(x),\\
x_i,&u_i\ge p(x).
\end{cases}
$$

Por ejemplo, $L=16$, $f_{\min}=8$, $f_{\max}=12$ y $f(x)=10$ dan $a=0.5$ y $p=2.5/16=0.15625$. El mejor candidato tiene $a=1$ y $p=1/16$. Antes de reparar la mochila, el número esperado de inversiones por clon es $L\,p(x)$, aunque cada clon concreto puede tener cero, una o varias inversiones. La normalización evita que la escala de valores de Mochila determine directamente la tasa de mutación.

### 4. Supervivencia, diversidad e historial

El motor une candidatos anteriores y clones evaluados. Retiene los $N-D$ de mayor valor y añade $D$ candidatos aleatorios nuevos, donde:

$$
D=\max\left(1,\left\lfloor\frac{N}{10}\right\rfloor\right).
$$

Para $N\ge 2$ queda al menos un sobreviviente, por lo que el mejor valor previo se conserva o mejora. Si $P_t$ es la población tras la iteración $t$:

$$
h_t=\max_{x\in P_t}f(x),\qquad h_t\ge h_{t-1},\qquad t=1,\ldots,T.
$$

El historial contiene $T+1$ valores. $h_0$ corresponde a la población inicial. Un tramo plano indica que durante esos pasos el mejor valor se mantuvo. Puede haber cambios en otros candidatos incluso cuando la curva se mantiene plana.

### Coste y efectos de los parámetros

Con $K=\sum_{r=1}^{S}k_r$ clones por ciclo, el código evalúa $N+T(K+D)$ candidatos. Retiene los valores de los sobrevivientes para reutilizarlos en la siguiente iteración. Con los valores por defecto, $N=32$, $T=40$, $K=20$ y $D=3$, se hacen **952 evaluaciones**. Construir, reparar y evaluar un vector toma tiempo proporcional a $L$. Además se ordenan hasta $N+K$ candidatos durante el ciclo. El coste aproximado total es $O(NL+N\log N+T[(K+D)L+(N+K)\log(N+K)])$.

| Parámetro | Efecto práctico |
| --- | --- |
| Población | Cambia los puntos de partida, el número de seleccionados y la cantidad de recién llegados |
| Iteraciones | Define el presupuesto de ciclos y la longitud de la gráfica |
| Máximo de clones | Aumenta las variantes que se prueban cerca de candidatos de mejor rango |
| Semilla | Permite repetir la secuencia pseudoaleatoria y comparar ejecuciones con los mismos datos |

La búsqueda puede encontrar el óptimo antes del último ciclo, como ocurre en las pruebas de este proyecto. El motor completa los ciclos solicitados y devuelve el mejor vector encontrado. En una instancia nueva, conocer el óptimo exige una cota verificable o un método exacto adicional.
"""), code("""
N, T, M = 32, 40, 8
selected = max(1, N // 4)
clones_by_rank = [max(1, M // rank) for rank in range(1, selected + 1)]
newcomers = max(1, N // 10)
evaluation_count = N + T * (sum(clones_by_rank) + newcomers)
assert evaluation_count == 952
print("Clones por rango:", clones_by_rank)
print("Candidatos aleatorios por ciclo:", newcomers)
print("Evaluaciones en total:", evaluation_count)
""")]


IMPLEMENTATION = [md("""
## Mapa del código

| Archivo | Responsabilidad |
| --- | --- |
| `src/models/ais_problems.py` | Define los vectores, las funciones objetivo y la restricción de Mochila |
| `examples/ais_mochila.json` | Guarda pesos, valores y capacidad iniciales que precarga el formulario |
| `src/models/ais_engine.py` | Define los parámetros, ejecuta selección clonal y devuelve el mejor resultado |
| `src/views/application.py` | Crea una instancia de `AISEngine` y registra AIS como opción del menú |
| `src/views/ais_panel.py` | Lee los campos, llama al motor y presenta el vector y el historial |
| `tools/check_ais.py` | Ejecuta las pruebas por terminal con instancias reproducibles |

El motor y los modelos usan la biblioteca estándar de Python. Los imports de Flet viven en las vistas. Se puede ejecutar el motor desde este notebook, desde terminal o desde la interfaz.
"""), md("""
## 1. Datos del problema y validación

`BitVector = tuple[int, ...]` es un alias para una tupla de enteros de longitud variable. La anotación describe la intención y `_validate_bits()` comprueba en ejecución que sólo haya ceros y unos enteros y que la longitud coincida. Por eso un vector escrito con `1.0` se rechaza igual que un vector con `2`.

`@dataclass(frozen=True)` genera un constructor a partir de los atributos y bloquea su reasignación. `__post_init__()` se ejecuta después de ese constructor. `OneMax` verifica que `length` sea positivo. `Knapsack` convierte `weights` y `values` a tuplas, comprueba tamaños, tipos y rangos, y guarda las tuplas validadas con `object.__setattr__()` durante la inicialización. La conversión copia listas proporcionadas por el formulario o el JSON, así que editar esas listas después no modifica la instancia.

- `OneMax.evaluate(vector)` valida el vector y usa `sum(vector)`.
- `Knapsack.length` usa `@property` para exponer la cantidad de objetos de `weights`.
- `Knapsack.weight(vector)` empareja bit y peso con `zip` y suma los pesos incluidos.
- `Knapsack.evaluate(vector)` verifica la capacidad y suma los valores incluidos.
- `Knapsack.repair(vector, rng)` conserva el vector factible tal como llega. Si hay exceso, convierte la tupla en lista, mezcla los índices seleccionados con el generador de la ejecución y retira objetos restando sus pesos. Devuelve otra tupla binaria.
- `load_knapsack_example(path)` abre un JSON UTF-8, valida las claves y construye `Knapsack`. `Path(__file__).resolve().parents[2]` localiza la raíz del proyecto desde el archivo del modelo, con independencia del directorio desde el que se abrió la app.

Por ejemplo, `sum(weight for bit, weight in zip(vector, self.weights) if bit)` se lee como «recorre parejas bit/peso y suma sólo los pesos cuyo bit es uno». El par de variables en el `for` desempaca cada pareja. El `if bit` filtra elementos y `sum` consume el generador.
"""), source("src/models/ais_problems.py"), md("""
## 2. Configuración, resultados y recorrido del motor

| Elemento | Qué contiene o hace |
| --- | --- |
| `AISConfig.population_size` | Cantidad fija de candidatos por población. Mínimo 2 y valor inicial 32. |
| `AISConfig.iterations` | Ciclos posteriores al estado inicial. Mínimo 1 y valor inicial 40. |
| `AISConfig.max_clones` | Máximo por seleccionado. Mínimo 1 y valor inicial 8. |
| `AISConfig.seed` | Entero para repetir una ejecución o `None` para inicializar el generador sin semilla explícita. Valor inicial 4. |
| `AISResult.vector` | Tupla de bits del mejor candidato. |
| `AISResult.value` | Afinidad de ese vector. |
| `AISResult.history` | Tupla de los mejores valores, con la población inicial en el índice 0. |
| `AISResult.weight` | Peso del vector en Mochila. En OneMax vale `None`. |

`AISEngine.run(problem, config)` acepta `OneMax | Knapsack`, una unión de tipos. `AISConfig()` se construye como valor por defecto de la función y puede reutilizarse con seguridad porque sus campos son inmutables. `Random(config.seed)` se crea dentro de cada llamada. Una instancia del motor puede atender varias ejecuciones y cada una empieza con su propio generador y sus variables locales.

### Cómo leer `run` paso a paso

1. `evaluate_candidate` es una función interna que usa `problem` y `rng` de la llamada exterior. `isinstance(problem, Knapsack)` activa la reparación cuando corresponde. Devuelve el par `(valor, vector)` para guardar el dato evaluado junto al candidato.
2. `random_candidate` construye el vector con `tuple(rng.getrandbits(1) for _ in range(problem.length))`. El generador entrega un bit por vuelta y `tuple` los reúne. `_` indica que el índice sólo se usa para repetir.
3. `[random_candidate() for _ in range(config.population_size)]` sí es una comprensión de lista. Genera la población inicial. `population.sort(key=affinity, reverse=True)` ordena esa lista por el primer elemento de cada par, de mayor a menor.
4. `population[:selected_count]` toma los candidatos de mayor valor. `enumerate(..., start=1)` agrega el rango y `for rank, (value, vector)` desempaca a la vez ese rango y el par evaluado.
5. `clone_count` usa división entera por rango. `relative_affinity` y `mutation_rate` aplican las expresiones del capítulo 13. En `1 - bit if rng.random() < mutation_rate else bit`, el `if` decide el valor de cada posición. Se conserva la longitud del vector.
6. `sorted(population + clones, key=affinity, reverse=True)` combina y ordena candidatos anteriores y nuevos. `[:survivors]` reserva espacio para diversidad. `extend` agrega los candidatos aleatorios a la lista. `history.append(population[0][0])` agrega un único número, que es el valor del primer candidato tras ordenar.
7. `value, vector = population[0]` desempaca la mejor solución final. El resultado reúne vector, valor, historial y, para Mochila, peso.
"""), source("src/models/ais_engine.py"), md("""
### La mutación escrita con un bucle tradicional

Las dos funciones siguientes consumen la misma secuencia de números aleatorios. La primera sirve para aprender a leer el recorrido. La segunda usa la expresión que aparece en el motor.
"""), code("""
from random import Random

def mutate_with_loop(vector, rate, rng):
    cloned_bits = []
    for bit in vector:
        if rng.random() < rate:
            cloned_bits.append(1 - bit)
        else:
            cloned_bits.append(bit)
    return tuple(cloned_bits)

def mutate_with_generator(vector, rate, rng):
    return tuple(1 - bit if rng.random() < rate else bit for bit in vector)

sample = (1, 0, 1, 1, 0)
explicit = mutate_with_loop(sample, 0.3, Random(4))
compact = mutate_with_generator(sample, 0.3, Random(4))
assert explicit == compact
print(f"Original {sample} · clon {explicit}")
"""), md("""
## 3. Conexión con Flet

1. Al arrancar, `OptimizationApp.__init__()` registra `AISPanel(page, engine=AISEngine())` con la clave `ais`. El menú principal llama a `ViewRouter.go("ais")`; el router muestra ese panel y conserva su instancia al cambiar a otro algoritmo.
2. `AISPanel.__init__()` crea el formulario, precarga la mochila y registra un router propio para Configuración y Resultados. El acceso a Resultados queda habilitado a partir del primer cálculo exitoso. `change_problem()` alterna los campos visibles y conserva los valores que ya se escribieron.
3. `build()` reúne submenú, formulario o resultados y barra de acciones. `change_stage()` sincroniza la opción seleccionada y los botones. `_show_message()` controla los mensajes de error o progreso del panel.
4. `settings()` lee `TextField.value` y usa `_integer()` y `_integer_list()` para convertir entradas. Las listas se escriben separadas por comas. Luego construye el problema y el `AISConfig`. Un error de formato o validación se muestra en Configuración.
5. `apply()` registra la revisión actual y ejecuta `await asyncio.to_thread(self.engine.run, problem, config)`. `await` espera el resultado mientras Flet sigue atendiendo su bucle de eventos. El indicador `busy` evita una segunda ejecución simultánea en el panel. El bloque `finally` restablece los controles aun si hay error.
6. `_pause()` incrementa la revisión al navegar fuera del panel o cambiar de etapa. Si el cálculo ya arrancó, el hilo puede terminar. `apply()` descarta la respuesta si la revisión cambió durante la ejecución.
7. `_render_result()` construye el resumen, muestra la tupla como lista legible y prepara la gráfica con `list(enumerate(result.history))`. Cada pareja contiene el número de iteración y el mejor valor de ese paso.

El menú cambia la **vista activa**. Esa vista ya tiene su motor asociado desde que se creó. Al pulsar **Ver resultados**, se invoca ese motor con los campos que estén vigentes en ese momento.
"""), source("src/views/application.py"), source("src/views/ais_panel.py"), md("""
## 4. Pruebas ejecutables con el motor real

Ejecuta las siguientes celdas en orden. El primer bloque localiza el proyecto partiendo de la carpeta del kernel de Jupyter. Si abriste el notebook desde otra ubicación, ajusta `project` a la raíz de AM. La gráfica requiere Matplotlib, incluido en las dependencias del proyecto.
"""), code("""
from pathlib import Path
import sys

project = next(
    (folder for folder in (Path.cwd(), *Path.cwd().parents)
     if (folder / "src" / "models" / "ais_engine.py").is_file()),
    None,
)
if project is None:
    raise RuntimeError("Abre el notebook desde AM o asigna la ruta de AM a project.")
sys.path.insert(0, str(project / "src"))

from models.ais_engine import AISConfig, AISEngine
from models.ais_problems import OneMax, load_knapsack_example

engine = AISEngine()
config = AISConfig(population_size=32, iterations=40, max_clones=8, seed=4)
"""), md("""
### Prueba 1 · OneMax

El óptimo se conoce a partir de la longitud. La prueba verifica el valor y el vector, comprueba que el historial sea creciente o constante y ejecuta de nuevo el modelo con la misma semilla para comprobar reproducibilidad.
"""), code("""
def check_history(result, iterations):
    assert len(result.history) == iterations + 1
    assert result.history[-1] == result.value
    assert all(previous <= current for previous, current in zip(result.history, result.history[1:]))

one_max = OneMax(length=16)
one_result = engine.run(one_max, config)
assert one_result.vector == (1,) * one_max.length
assert one_result.value == one_max.evaluate(one_result.vector) == 16
assert one_result == engine.run(one_max, config)
check_history(one_result, config.iterations)
print("Vector:", list(one_result.vector))
print("Valor:", one_result.value)
print("Historial:", list(one_result.history))
"""), md("""
### Prueba 2 · Mochila 0/1

Esta celda carga los datos de ejemplo que usa el formulario. Verifica que el peso y el valor devueltos correspondan al vector y que el peso respete la capacidad. `product((0, 1), repeat=n)` genera todas las combinaciones para una comprobación exacta del ejemplo. `max(...)` se aplica únicamente a las factibles. Con ocho objetos se enumeran 256 combinaciones. Si editas el JSON para usar muchos más objetos, utiliza la verificación exhaustiva únicamente en el ejemplo original o en una instancia pequeña.
"""), code("""
from itertools import product

knapsack = load_knapsack_example()
knap_result = engine.run(knapsack, config)
assert knap_result.weight == knapsack.weight(knap_result.vector) <= knapsack.capacity
assert knap_result.value == knapsack.evaluate(knap_result.vector)
check_history(knap_result, config.iterations)
print("Vector:", list(knap_result.vector))
print("Valor:", knap_result.value)
print(f"Peso {knap_result.weight} de {knapsack.capacity}")
print("Historial:", list(knap_result.history))

if knapsack.length <= 12:
    exact = max(
        knapsack.evaluate(bits)
        for bits in product((0, 1), repeat=knapsack.length)
        if knapsack.weight(bits) <= knapsack.capacity
    )
    assert knap_result.value <= exact
    print(f"Óptimo por enumeración: {exact}. Brecha: {exact - knap_result.value}.")
"""), md("""
### Leer las curvas de convergencia

El eje horizontal incluye el estado inicial. Cada línea escalonada muestra el mejor valor alcanzado hasta el paso indicado. Se usan ejes verticales separados porque los valores de OneMax y Mochila tienen significados distintos. Con el JSON original y semilla 4, OneMax alcanza 16 en la iteración 6 y Mochila alcanza 37 en la iteración 4. La meseta final muestra que el resultado se conservó hasta completar el presupuesto.
"""), code("""
from matplotlib.figure import Figure

figure = Figure(figsize=(8, 5), layout="constrained")
axes = figure.subplots(2, 1, sharex=True)
for axis, title, result, color in zip(
    axes, ("OneMax", "Mochila 0/1"), (one_result, knap_result), ("#456A91", "#9C5837")
):
    axis.step(range(len(result.history)), result.history, where="post", color=color)
    axis.set_title(f"{title} · valor final {result.value}")
    axis.set_ylabel("Mejor valor")
    axis.grid(alpha=0.25)
axes[-1].set_xlabel("Iteración")
figure
"""), md("""
## 5. Ejecutar y extender los experimentos

Desde la raíz de AM, `python tools/check_ais.py` imprime las dos pruebas y comprueba el óptimo del caso fijo de Mochila. `python tools/check_ais.py --longitud 24` prueba otra longitud. `python tools/check_ais.py --mochila` carga el JSON actual y se puede indicar un archivo alternativo después de la opción. En esas ejecuciones personalizadas el programa muestra el mejor candidato encontrado.

Para estudiar parámetros, cambia la semilla, ejecuta varias veces y registra valor final, tiempo y primer paso en que aparece cierto valor. Mantén fijos problema, población y demás parámetros mientras cambias un único factor. Si comparas distintas cantidades de clones o iteraciones, indica cuántas evaluaciones usó cada configuración. El capítulo 13 muestra cómo calcularlas.

Como ejercicio, prueba capacidad cero con objetos de peso positivo y verifica que el único vector factible sea el vector de ceros. Después utiliza una capacidad suficiente para que quepan todos los objetos y compara el peso, el valor y el historial.
"""), source("tools/check_ais.py")]


def run_cells(cells):
    """Ejecuta ejemplos propios y guarda salidas legibles en Jupyter."""
    namespace = {}
    count = 0
    for cell in cells:
        if cell["cell_type"] != "code":
            continue
        count += 1
        buffer = StringIO()
        with redirect_stdout(buffer):
            exec(compile("".join(cell["source"]), f"<ais-example-{count}>", "exec"), namespace)
        cell["execution_count"] = count
        if buffer.getvalue():
            cell["outputs"].append({"output_type": "stream", "name": "stdout",
                                    "text": buffer.getvalue().splitlines(keepends=True)})
        figure = namespace.pop("figure", None)
        if figure is not None:
            from matplotlib.backends.backend_agg import FigureCanvasAgg

            png = BytesIO()
            FigureCanvasAgg(figure).print_png(png)
            cell["outputs"].append({"output_type": "display_data", "metadata": {},
                                    "data": {"image/png": b64encode(png.getvalue()).decode("ascii"),
                                             "text/plain": ["Curvas de convergencia de OneMax y Mochila 0/1"]}})
    return count


def main():
    pages = {}
    counts = {}
    for (name, title), content in zip(CHAPTERS.items(), (FOUNDATIONS, FORMULAS, IMPLEMENTATION)):
        cells = [md(f"# {title}\n\n[Volver al índice](00_indice.ipynb) · {LINKS}"), *content]
        for index, cell in enumerate(cells):
            cell["id"] = f"ais-{name[:2]}-{index:02}"
        counts[name] = run_cells(cells)
        pages[FOLDER / (name + ".ipynb")] = {
            "nbformat": 4, "nbformat_minor": 5,
            "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3 (AM)", "language": "python"},
                         "language_info": {"name": "python"}},
            "cells": cells,
        }

    index_path = FOLDER / "00_indice.ipynb"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    ais_cell = md(f"## AIS · Selección clonal\n\n{LINKS}\n\nFundamentos, ecuaciones y casos prácticos del motor de OneMax y Mochila 0/1.")
    ais_cell["id"] = "ais-index"
    index["cells"] = [cell for cell in index["cells"] if cell.get("id") != ais_cell["id"]]
    index["cells"].append(ais_cell)
    pages[index_path] = index
    for path, page in pages.items():
        path.write_text(json.dumps(page, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for name, count in counts.items():
        print(f"{name}.ipynb: {count} celdas de código ejecutadas")


if __name__ == "__main__":
    main()
