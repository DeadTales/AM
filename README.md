# Evolución Lab

Interfaz de escritorio en español con Flet 1.0.4, tema claro y vistas separadas de configuración y resultados. Incluye editor de población vectorial, parámetros de evolución, gráficas con zoom y reproducción de generaciones.

El menú superior permite cambiar entre **Evolutivo** y **Partículas · PSO**. Cada algoritmo conserva sus parámetros, individuos y resultados. Para partículas se hace uso de una **simulación didáctica**, mientras otra persona implementa el motor definitivo.

## Instalación y ejecución

```powershell
& 'venv\Scripts\Activate.ps1'
python -m pip install -r requirements.txt
python src/main.py
```

**NOTA:** la ruta del entorno virtual depende de donde este el tuyo.

## Funciones de prueba

Se hace uso de funciones provisionales para poder hacer una versión de prueba de formularoo y procesos, asi como simular el comportamiento en la muestra de gráficos, dichas funciones de prueba son:

* Seno oscilante (1D, maximización).
* Exponencial simple (1D, maximización).
* Ackley.
* Eggholder.
* Rosenbrock.

Las tres últimas funciones son de dos variables y orientadas a minimización. Ambos algoritmos usan el mismo registro en `src/models/objectives.py`.

## Uso de la interfaz

### Población

Selecciona función y número de variables. **Generar población** crea una muestra reproducible; la cantidad del generador no te obliga a conservar dicho tamaño o individuos, es decir, se pueden agregar, quitar y/o editar. Ingresa una coordenada por campo y pulsa **Agregar individuo**. Los botones de cada fila permiten editar o eliminar. **Guardar cambios** confirma una edición y **Cancelar edición** descarta el formulario pendiente. Pulsa **Ver resultados** para usar la lista guardada. Cambiar función o variables vacía la lista porque cambian sus etiquetas o dominio.

### Navegación

El **Menú** permite cambiar de algoritmo. El **Submenú** permite alternar entre Configuración y Simulación / Resultados; su flecha **Volver** recorre las etapas visitadas del algoritmo actual. Navegar conserva parámetros, ediciones pendientes y resultados, y pausa la reproducción. Resultados se habilita después de aplicar una configuración válida.

### Gráficas

Para funciones de dos variables, Resultados ofrece **Superficie 3D** (predeterminada) y **Mapa de calor**. La superficie representa `(x, y, f(x,y))`, incluidos los individuos y el mejor destacado. Los sliders **Giro horizontal** e **Inclinación** cambian la cámara al soltarlos; zoom y arrastre amplían o desplazan la imagen, mientras que la rotación se controla con esos sliders. Este comportamiento no cambia la dimensión del individuo ni los parámetros del algoritmo.

## Comportamiento de la simulación

El recorrido es una interpolación ilustrativa hacia un mínimo muestreado, no un algoritmo genético. Selección y mutación no se utilizan en esta simulación, pero se definen para la integración posterior. El historial muestra el recorrido completo previsto; un punto marca la generación visible. La generación 0 es la población inicial.

Este apartado describe `DemoEngine`, conservado como ejemplo. El menú Evolutivo sigue usando `GeneticEngine`. La simulación de partículas está en `src/models/pso_demo_engine.py`; sí actualiza velocidades y memorias personales/sociales para observar el efecto de los parámetros, y se identifica como simulación en la interfaz y exportaciones.

## Simulación de partículas (PSO)

En **Partículas · PSO** se definen inercia **w**, coeficiente cognitivo **c1**, coeficiente social **c2**, semilla e iteraciones. No se usan selección, cruza ni mutación. Se conservan las mismas funciones, editor de posiciones, gráficas 1D/2D/3D y reproducción del recorrido.

Cada ejecución registra una prueba. **Comparar pruebas → Comparar w, c1 y c2** genera una base y hasta seis variantes, cambiando un coeficiente a la vez. Se mantienen posiciones iniciales, función, dominio, número de partículas, semilla e iteraciones. La gráfica muestra mejor valor encontrado hasta cada paso y dispersión del enjambre; se pueden agregar observaciones y exportar **CSV y JSON** en `artifacts/pso_comparisons`. Los registros quedan en memoria hasta cerrar la app; exporta lo que quieras conservar.

Para conectar el algoritmo de partículas que hará otra persona:

1. Implementar `PSOEngine.run(config)` en **`src/models/pso_engine.py`**. Por ahora lanza `NotImplementedError` para indicar que está pendiente.
2. Recibir `PSOConfig` de `contracts.py`: posiciones iniciales, objetivo, iteraciones, `inertia`, `cognitive`, `social` y `seed`.
3. Devolver `list[Generation]` con paso 0 y todas las iteraciones, posiciones y evaluaciones; respetar límites, dirección max/min y tamaño de población.
4. En **`src/views/application.py`**, importar `PSOEngine` y cambiar `engine=PSODemoEngine()` por `engine=PSOEngine()` en el panel `pso`.

Documentación detallada en `..\documentación\AM\10_pso_simulacion_e_integracion.ipynb`. Las pruebas ejecutadas con las cinco funciones y sus gráficas están en `11_pso_pruebas_y_analisis.ipynb`. Los resultados son de la simulación y una semilla, no conclusiones definitivas sobre el algoritmo final.

Comprobaciones: `python tools/check_pso.py`; prueba de escritorio con ventana temporal: `python tools/check_pso_desktop.py`. Generar documentación y ejemplos: `python tools/build_pso_notebooks.py`.

## Integración del algoritmo genetico

Para conectar el algoritmo genetico:

1. Implementar `run(config)` en un motor para el algoritmo genetico. `AlgorithmConfig` contiene `population`, `objective`, `mutation_rate` entre 0 y 1, `selection` y `generations`.
2. Devuelve `list[Generation]` con generaciones consecutivas desde 0. Cada una contiene `index`, `population` y `scores`. La generación 0 conserva la población inicial y cada individuo tiene una puntuación. En este contrato se mantiene el tamaño de población.
3. En `src/views/application.py`, el panel `genetic` conecta el motor mediante `Dashboard(page, engine=GeneticEngine(), algorithm="genetic")`.
4. Definir las funciones de la actividad, etiquetas y dominios en `src/models/objectives.py`.

El contrato está en `src/models/contracts.py`; el ejemplo reemplazable está en `src/models/demo_engine.py`. `Dashboard.apply()` llama al motor en un hilo mediante `asyncio.to_thread`, valida su salida y descarta el resultado si cambió la configuración durante el cálculo. Se necesita  implementar un mecanismo de frenado si esto pasa.

## Componentes de la interfaz

### Menú y rutas

Se hace uso de dos componentes independientes:

* `src/views/menu.py`: `Menu` y `MenuItem` para cambiar entre **Evolutivo** y **Partículas · PSO**. El algoritmo activo se muestra con fondo azul.
* `src/views/submenu.py`: `Submenu` y `SubmenuItem` para navegar entre **Configuración**, **Simulación / Resultados** y, en PSO, **Comparar pruebas**. Tiene un estilo más ligero y su botón **Volver** sólo recorre las etapas del algoritmo seleccionado.

`src/views/application.py` usa el menú principal y cada `Dashboard` tiene su propio `submenu`. Ambos utilizan routers independientes de `src/views/router.py`, por lo que cambiar de algoritmo conserva sus ediciones y la etapa en la que se quedó. Para añadir una etapa, registra su control en el router del panel y un `SubmenuItem` con el mismo identificador.

### Editor de población

`PopulationEditor` en `src/views/population_editor.py` es un contenedor reutilizable. Sus parámetros son `dimensions`, `labels`, `bounds`, `on_change`, `on_refresh`, `list_height` y `max_individuals`. Admite más dimensiones; las funciones y gráficas de esta app cubren 1D/2D.

### Presentación y gráficos

`Dashboard.render()` sólo presenta resultados, `charts.py` dibuja y `theme.py` centraliza colores. Las gráficas se renderizan a PNG con Matplotlib/Agg y se presentan en un `Chart` persistente con `Image` e `InteractiveViewer`. El visor tiene dimensiones explícitas y conserva zoom al cambiar de generación. Esto evita comparar miles de primitivas Canvas al actualizar la página.

## Referencias

Referencias oficiales: [Flet](https://flet.dev/docs/), [Slider](https://flet.dev/docs/controls/slider/), [Dropdown](https://flet.dev/docs/controls/dropdown/).
