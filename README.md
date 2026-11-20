# Evolución Lab

Aplicación de escritorio en español con Flet 1.0.4 para configurar problemas de optimización, ejecutar cinco algoritmos reales y examinar sus soluciones e historiales. Primero se elige el tipo de problema; el menú muestra los algoritmos compatibles y conserva la última selección de cada tipo.

## Instalación y ejecución

Desde la carpeta del proyecto, con Python 3.13 para Windows:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe src\main.py
```

Después de instalar las dependencias basta con el último comando. No se necesita activar el entorno. Los ejemplos se encuentran por su ruta dentro del proyecto, aunque se ejecute la aplicación desde otra carpeta.

## Representaciones y combinaciones disponibles

| Representación | Problemas | Algoritmos conectados |
| --- | --- | --- |
| Continua: vectores de números reales | Sphere, Rastrigin, Ackley, Rosenbrock y otras funciones del catálogo | GA, PSO y DE |
| Binaria: vectores de ceros y unos | OneMax y mochila 0/1 | AIS |
| Discreta: permutaciones o índices de categorías | TSP y asignación de tareas a recursos | ACO |

Cada panel ofrece los problemas que admite su motor. Las otras combinaciones no están implementadas. TSP y asignación minimizan sus costos; OneMax y mochila maximizan su beneficio por definición. Los problemas continuos permiten elegir el sentido de optimización.

## Configuración dinámica y nombres de los parámetros

Todos los controles tienen etiquetas del algoritmo seleccionado, ayuda visible o contextual y validación de tipo o rango. El tamaño utilizado se corresponde con la lista de individuos guardada: al cambiar la cantidad se debe pulsar **Generar población**; agregar o quitar individuos actualiza esa cantidad.

| Algoritmo | Parámetros disponibles |
| --- | --- |
| GA | Tamaño de población, tasa de cruza, tasa de mutación, método de selección, número de generaciones y semilla |
| ACO | Número de hormigas, feromona inicial, evaporación, influencia de feromona, influencia heurística, número de iteraciones, depósito Q, paciencia y semilla |
| PSO | Número de partículas, coeficientes cognitivo y social, inercia, límites de velocidad, número de iteraciones y semilla |
| AIS | Número de anticuerpos, tasa de clonación, tasa de mutación, selección clonal, máximo de clones por anticuerpo, fracción de renovación, número de iteraciones y semilla |
| DE | Tamaño de población, factor de mutación, tasa de cruza, estrategia de selección / variante, número de generaciones y semilla |

GA conserva al mejor candidato y utiliza cruza BLX con α=0.25 y mutación gaussiana con σ=10 % del intervalo. La selección de padres puede ser torneo, ruleta o elitista. PSO es global-best: las velocidades iniciales se generan uniformemente en ±5 % del intervalo y su límite de movimiento es configurable por porcentaje (20 % inicialmente). DE admite rand/1/bin y best/1/bin con cruza binomial y reemplazo voraz.

## Problemas continuos

GA, PSO y DE comparten la selección de función, la dimensión, el control **Minimizar / Maximizar** y un par de límites por variable. Los límites deben ser números finitos, con mínimo menor que máximo. El sentido elegido cambia la comparación del motor y queda registrado en el resumen y en las comparaciones PSO.

Sphere, Schwefel y Griewank admiten entre 1 y 10 variables. Se conservan las variantes originales 1D o 2D de las otras funciones; el selector muestra su dimensión fija. La fórmula y el dominio se muestran en la configuración.

**Aplicar límites y regenerar población** crea individuos dentro de los nuevos intervalos. **Generar población** hace lo mismo con la cantidad indicada. También se pueden agregar, editar o eliminar individuos. Si un cambio de límites deja individuos fuera del dominio, se informa el error antes de ejecutar y se puede regenerar la población o corregirla manualmente. No se descartan silenciosamente los datos por una entrada inválida.

En resultados se muestran el sentido y los límites realmente utilizados. Las ejecuciones 1D ofrecen una curva; las 2D, superficie o mapa de calor. Para más variables se dibujan las coordenadas de los individuos y los límites, destacando el mejor vector. La convergencia conserva el historial real desde la generación 0 y se puede recorrer con el deslizador o reproducir.

La lista de resultados coloca primero **Mejor encontrado**, con su vector, evaluación e iteración de origen. Después presenta los individuos de la iteración seleccionada ordenados de mejor a peor según el sentido. El orden de los datos del motor se conserva. En PSO, el primer vector puede provenir de una iteración anterior: se muestra el récord histórico real, aunque las partículas actuales se hayan alejado de él. Al terminar se abre la última iteración disponible.

Las implementaciones están en `src/models/genetic_engine.py`, `pso_engine.py` y `de_engine.py`. `DemoEngine` y `PSODemoEngine` se conservan como ejemplos y pruebas; el menú conecta los motores reales.

## Problemas binarios

AIS utiliza selección clonal, clonación, hipermutación y conservación de los mejores candidatos.

La selección clonal configura la fracción de anticuerpos de mayor afinidad que se clonan (0.25 inicialmente). El número de clones disminuye con el rango: `max(1, int(max_clones * tasa_clonación) // rango)`; una tasa de clonación 0 desactiva los clones. La tasa de mutación vacía utiliza `1 / longitud` como base; si se especifica un valor de 0 a 1, se usa como base. La probabilidad por bit es `min(1, base * (1 + 3 * (1 - afinidad_relativa)))`. La fracción de renovación introduce candidatos aleatorios y siempre se conserva al menos un superviviente. Los valores iniciales mantienen la variante previa.

- **OneMax:** cada posición contiene 0 o 1. Se configura la longitud y se maximiza `Σ xᵢ`; todos los vectores de esa longitud son factibles.
- **Mochila 0/1:** el bit `xᵢ` indica si se incluye el objeto i. Se editan pesos, valores y capacidad en la interfaz. Se maximiza `Σ valorᵢ·xᵢ`, sujeto a `Σ pesoᵢ·xᵢ ≤ capacidad`. Debe haber un valor por peso; los pesos son enteros positivos y los valores y la capacidad, enteros no negativos. El motor repara candidatos con sobrepeso antes de evaluarlos.

La interfaz cambia los campos al elegir el problema y valida los datos antes de ejecutar. Los resultados incluyen vector, valor, historial y la configuración aplicada, incluidos los pesos, valores y capacidad usados.

## Problemas categóricos o discretos

El panel ACO permite editar las instancias sin modificar archivos. Los ejemplos originales de `data/` se usan como datos iniciales y pueden recuperarse con **Restaurar ejemplo del problema**. Cada formulario conserva sus datos al cambiar entre TSP y asignación. Al cambiar de problema se limpian los resultados, las gráficas, el historial y la exportación de la ejecución anterior.

### Viajante TSP

Cada categoría es una ciudad identificada por su índice y nombre. La solución es una permutación: visita cada ciudad una vez y regresa al inicio. El objetivo es minimizar la suma de distancias euclidianas de la ruta cerrada.

Se pueden agregar o quitar ciudades, cambiar sus nombres y coordenadas y elegir la ciudad inicial. Se admiten 3–60 ciudades, con coordenadas finitas y distintas y nombres completos y únicos. Los índices del selector inicial coinciden con los de las filas. La mejor ruta se muestra en texto y en una gráfica.

### Asignación de tareas

La posición i del vector representa la tarea i. Su valor es el índice del recurso asignado, de modo que cada tarea tiene un único recurso. Se minimiza la suma de los costos seleccionados, respetando que la demanda acumulada por recurso no exceda su capacidad.

Se configuran 1–60 tareas y 1–20 recursos. **Ajustar tabla** aplica sus cantidades y conserva los valores de las celdas que permanecen. Se editan nombres, demandas, capacidades y cada costo de la matriz. Las columnas R0, R1… corresponden a los índices de los recursos. Costos y demandas deben ser positivos; capacidades, no negativas.

El modelo verifica tamaños, valores finitos, demanda total y que cada tarea quepa en algún recurso. Estas comprobaciones necesarias no garantizan por sí solas que exista una partición factible. Durante la búsqueda se penalizan los excesos de capacidad. Los resultados indican si la solución encontrada es factible y muestran sus cargas frente a las capacidades.

### Ejecución ACO

Se configuran hormigas, iteraciones, feromona inicial, α, β, evaporación, depósito Q, paciencia y semilla. La variante es Ant System con refuerzo elitista. El motor se ejecuta en un hilo; **Detener** y cambiar de algoritmo solicitan su detención al completar la iteración actual. No se permite iniciar otra búsqueda hasta que el hilo termine.

Se conservan la instancia y los parámetros realmente utilizados. Al terminar o detener se muestran mejor solución, costo, iteraciones completadas, motivo de término y curva del mejor costo acumulado desde la iteración 0. El historial permite recorrer las rutas o asignaciones intermedias. **Reiniciar resultados** limpia la salida y conserva el formulario.

## Ejecución y recorrido del historial

Los cinco motores publican estados reales desde la inicialización y aceptan una solicitud de detención cooperativa. El cálculo ocurre en un hilo; las actualizaciones de Flet se procesan en el bucle de la interfaz. Mientras se calcula se muestran el problema, los parámetros, la iteración actual frente al límite, el mejor valor y las gráficas. La actualización visual se agrupa para mantener la respuesta de la aplicación.

Si la búsqueda termina antes de que se puedan observar todos los pasos, el historial completo queda disponible. GA, PSO y DE tienen deslizador, paso anterior/siguiente y reproducción. AIS y ACO incorporan además accesos a Inicio, 1/3, 2/3 y Final. El candidato destacado corresponde al mejor encontrado hasta el paso visualizado.

**Detener** termina el paso en curso y conserva los estados completados; cambiar de algoritmo o volver a configuración durante el cálculo también solicita la detención. **Reiniciar** prepara una nueva ejecución conservando los datos del formulario y deshabilita los resultados y exportaciones anteriores. Volver al inicio del historial únicamente rebobina la reproducción y es un control distinto.

## Exportación de resultados

Los cinco paneles incluyen **Exportar CSV y JSON** al terminar o detener una ejecución. Los archivos se guardan con nombres únicos en `artifacts/results/` dentro del proyecto y la interfaz muestra ambas rutas. No se sobrescriben exportaciones anteriores.

El CSV contiene una fila por iteración, con la evaluación y el vector del mejor candidato acumulado, el mejor de esa iteración, el motivo de término y la configuración. El JSON añade todos los individuos y evaluaciones por paso, la instancia, parámetros, sentido, semilla y procedencia del récord. Se exporta la configuración aplicada a esa ejecución, aunque después se editen los controles o se recorra otro punto del historial. En AIS se registra también la tasa base de mutación efectiva.

## Comparaciones PSO

**Comparar pruebas** genera una base y variantes de w, c1 y c2 manteniendo función, sentido, dominio, población, semilla e iteraciones. Se muestran convergencia y dispersión, se pueden añadir observaciones y exportar CSV y JSON a `artifacts/pso_comparisons`. Los registros permanecen en memoria hasta cerrar la aplicación; hay que exportarlos para conservarlos.

## Organización y comprobaciones

`src/models/` contiene contratos, funciones objetivo, problemas y motores independientes de Flet. `src/views/` contiene navegación, formularios, edición de instancias y gráficos con Matplotlib/Agg. `src/main.py` inicia el cliente de escritorio.

```powershell
.\.venv\Scripts\python.exe tools\check_de.py
.\.venv\Scripts\python.exe tools\check_pso.py
.\.venv\Scripts\python.exe tools\check_ais.py
.\.venv\Scripts\python.exe tools\check_aco.py
.\.venv\Scripts\python.exe tools\check_aco_panel.py
.\.venv\Scripts\python.exe tools\check_problem_configuration.py
.\.venv\Scripts\python.exe tools\check_run_workflow.py
```

Las comprobaciones de configuración cubren los datos editados de las tres representaciones, ambos sentidos, dominios y dimensiones, validaciones e instantáneas. Las de flujo comprueban nombres por algoritmo, parámetros que afectan realmente a la búsqueda, mejor individuo primero, progreso y detención, recorrido de iteraciones, reinicio y exportaciones de los cinco motores.

Prueba opcional con una ventana Flet real y capturas: `.\.venv\Scripts\python.exe tools\check_problem_configuration_desktop.py`. Guarda las evidencias en `artifacts/problem_configuration_desktop/`.

Para verificar los nombres de parámetros, el mejor candidato primero y diez archivos exportados desde botones reales: `.\.venv\Scripts\python.exe tools\check_run_workflow_desktop.py`. Guarda capturas y datos ficticios en `artifacts/run_workflow_desktop/`.

## Alcance implementado y pendientes

Implementado: cinco motores reales; selección por tipo y algoritmo compatible; nombres y ayudas específicos; problemas editables; dimensión nD, límites y sentido cuando corresponden; parámetros AIS y límites de velocidad PSO configurables; progreso, detención y reinicio; solución e historial explorable; mejor candidato histórico primero; configuración aplicada y exportación CSV/JSON para todos los algoritmos.

Pendiente para la entrega académica completa: consolidación de los cinco experimentos documentados, comparación e interpretación, reporte PDF/LaTeX y video demostrativo. Las comprobaciones automáticas son evidencia técnica y no sustituyen esos entregables.
