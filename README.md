# Evolución Lab

Interfaz de escritorio en español con Flet 1.0.4, tema claro y vistas separadas de configuración y resultados. Incluye editor de población vectorial, parámetros de evolución, gráficas con zoom y reproducción de generaciones.

El **Menú** permite alternar entre Configuración y Resultados; la flecha **Volver** recorre las vistas visitadas. Navegar conserva parámetros, ediciones pendientes y resultados, y pausa la reproducción. Resultados se habilita después de aplicar una configuración válida.

El menú y las acciones quedan fijos; sólo el cuerpo se desplaza. **Ver resultados** está accesible incluso a 760×640. En Resultados aparece **Editar configuración** en la misma barra inferior.

`src/views/menu.py` contiene `Menu` y `MenuItem`; `src/views/router.py`, `ViewRouter` con rutas, historial y condiciones de acceso. Para añadir una vista, registra su control en el router y una opción del menú con el mismo identificador. Los campos usan `OutlineInputBorder` y `BorderSide` en lugar de las propiedades obsoletas `TextField.border_radius` y `TextField.border_color`.

```powershell
& 'venv\Scripts\Activate.ps1'
python -m pip install -r requirements.txt
python src/main.py
```

**NOTA:** la ruta del entorno virtual depende de donde este el tuyo.

---

Las funciones provisionales son:
 * Esfera. 
 * Rastrigin. 
 * Ackley. 
 * Cuártica.
 * Ondulada. 

Dichas funciones son de una o dos variables y orientadas a minimización. Se pueden reemplazar en `src/models/objectives.py`. En 2D la vista muestra un mapa de calor de f(x,y) con individuos superpuestos.

Para funciones de dos variables, Resultados ofrece **Superficie 3D** (predeterminada) y **Mapa de calor**. La superficie representa `(x, y, f(x,y))`, incluidos los individuos y el mejor destacado. Los sliders **Giro horizontal** e **Inclinación** cambian la cámara al soltarlos; zoom y arrastre amplían o desplazan la imagen, mientras que la rotación se controla con esos sliders. No cambia la dimensión del individuo ni los parámetros del algoritmo.

Selecciona función y número de variables. **Generar población** crea una muestra reproducible; la cantidad del generador no te obliga a conservar dicho tamaño o individuos, es decir, se pueden agregar, quitar y/o editar. Ingresa una coordenada por campo y pulsa **Agregar individuo**. Los botones de cada fila permiten editar o eliminar. **Guardar cambios** confirma una edición y **Cancelar edición** descarta el formulario pendiente. Pulsa **Ver resultados** para usar la lista guardada. Cambiar función o variables vacía la lista porque cambian sus etiquetas o dominio.

`PopulationEditor` en `src/views/population_editor.py` es un contenedor reutilizable. Sus parámetros son `dimensions`, `labels`, `bounds`, `on_change`, `on_refresh`, `list_height` y `max_individuals`. Admite más dimensiones; las funciones y gráficas de esta app cubren 1D/2D.

El recorrido es una interpolación ilustrativa hacia un mínimo muestreado, no un algoritmo genético. Selección y mutación no se utilizan en esta simulación, pero se definen para la integración posterior. El historial muestra el recorrido completo previsto; un punto marca la generación visible. La generación 0 es la población inicial.

Para conectar el algoritmo genetico:

1. Implementar `run(config)` en un motor para el algoritmo genetico. `AlgorithmConfig` contiene `population`, `objective`, `mutation_rate` entre 0 y 1, `selection` y `generations`.
2. Devuelve `list[Generation]` con generaciones consecutivas desde 0. Cada una contiene `index`, `population` y `scores`. La generación 0 conserva la población inicial y cada individuo tiene una puntuación. En este contrato se mantiene el tamaño de población.
3. En `src/main.py`, sustituir `DemoEngine()` por el motor de algoritmo genetico al construir `Dashboard(page, engine=...)`.
4. Definir las funciones de la actividad, etiquetas y dominios en `src/models/objectives.py`.

El contrato está en `src/models/contracts.py`; el ejemplo reemplazable está en `src/models/demo_engine.py`. `Dashboard.apply()` llama al motor en un hilo mediante `asyncio.to_thread`, valida su salida y descarta el resultado si cambió la configuración durante el cálculo. Se necesita  implementar un mecanismo de frenado si esto pasa.

`Dashboard.render()` sólo presenta resultados, `charts.py` dibuja y `theme.py` centraliza colores. Las gráficas se renderizan a PNG con Matplotlib/Agg y se presentan en un `Chart` persistente con `Image` e `InteractiveViewer`. El visor tiene dimensiones explícitas y conserva zoom al cambiar de generación. Esto evita comparar miles de primitivas Canvas al actualizar la página.

`python tools/check_desktop.py` abre una ventana temporal, despacha eventos reales de Flet, verifica gráficas, navegación y pausa, guarda capturas de ventanas pequeñas en `artifacts/desktop_check` y cierra la ventana. `python tools/check_interface.py` verifica contratos y estado sin abrir cliente. La primera ejecución de Matplotlib puede crear una caché de fuentes en tu perfil de usuario.

Referencias oficiales: [Flet](https://flet.dev/docs/), [Slider](https://flet.dev/docs/controls/slider/), [Dropdown](https://flet.dev/docs/controls/dropdown/).
