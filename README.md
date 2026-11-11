<p align="center"><img src="figuras_bloques/recursos/marca/logo_nombre.png" alt="Hexabloq" width="420"></p>

# Hexabloq

**Figuras con bloques, fila a fila.** Aplicación de escritorio para Windows que genera **círculos, triángulos equiláteros y hexágonos regulares** hechos con bloques cuadrados, como plantilla para construir en Minecraft u otros juegos de bloques. Cada celda de la cuadrícula es un bloque completo: sin suavizado ni bloques parciales.

- Programa con ventana propia (Python + PySide6). No usa navegador, servidor ni conexión a internet.
- El conteo, el dibujo, la guía por filas, el PNG y el JSON salen **del mismo conjunto de bloques**.

---

## Identidad visual

- **Nombre:** *Hexabloq* une «hexágono» y «bloque». Es corto, fácil de recordar y apunta a la figura principal de la aplicación.
- **Logo:** un hexágono de 15 bloques generado con el propio algoritmo de la app. El borde va en verde claro y el interior en verde más intenso; cada bloque tiene un relieve de luz y sombra.
- **Icono:** la versión simplificada, sin relieve, sobre un cuadrado redondeado oscuro. En cada resolución se dibuja con bloques de píxeles enteros: hexágono de 7 bloques para 16–24 px, de 9 para 32–48 px y de 15 a partir de 64 px. Así se reconoce incluso en la barra de tareas.
- **Paleta:**

  | Uso | Color |
  |---|---|
  | Fondos | `#121417` (base), `#1A1D21` (paneles), `#22262B` (superficies) |
  | Texto | `#E8EAED` (principal), `#A3ABB4` (secundario) |
  | Acento | verde esmeralda `#3FC98A` |
  | Fila resaltada | ámbar `#F5B83D` |
  | Errores | `#F07171` |

- **Tipografía:** Segoe UI, la fuente del sistema en Windows.

Los recursos están en [figuras_bloques/recursos/](figuras_bloques/recursos/):

- **`marca/`**:
  - `logo.svg` y `logo.png`: el hexágono solo.
  - `logo_nombre.svg` y `logo_nombre.png`: el hexágono con el nombre.
  - `icono.svg`: el icono simplificado.
  - `icono.ico`: con 9 resoluciones, de 16 a 256 px.
  - `icono_256.png`.
- **`iconos/`**: iconos de interfaz en SVG, de trazo uniforme, que la app colorea según el estado del botón.

Se regeneran con `python tools/generar_identidad.py`. Todos son originales y locales.

---

## Instalación y ejecución

### Opción A: ejecutable (no necesita Python)

Ejecuta `dist\Hexabloq.exe`. Es un único archivo que puedes copiar donde quieras; lleva incrustados el icono, el logo y la información de versión.

Para volver a generarlo, haz doble clic en **`construir_exe.bat`**. El script:

1. crea el entorno virtual `.venv` si no existe;
2. instala `requirements-dev.txt`;
3. ejecuta las pruebas y se detiene si alguna falla;
4. genera `dist\Hexabloq.exe` con PyInstaller, según `Hexabloq.spec`.

El `.spec` incluye la carpeta `figuras_bloques/recursos`, el icono `icono.ico` y los datos de versión de [empaquetado/version_info.txt](empaquetado/version_info.txt).

Para comprobar que un ejecutable carga todos sus recursos:

```bat
dist\Hexabloq.exe --comprobar-recursos estado.json
```

Escribe en `estado.json` si cada recurso se carga, y termina con código 0 si todo está bien.

### Opción B: desde el código fuente

Requisitos: Python 3.10 o superior.

```bat
py -3 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python main.py
```

También puedes hacer doble clic en `ejecutar.bat`, que hace lo mismo.

### Pruebas

```bat
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest
```

---

## Uso

| Zona | Qué hace |
|---|---|
| **Barra superior** | Logo, nombre y diseño actual (indica si hay cambios sin guardar). Acciones *Nuevo*, *Abrir*, *Guardar* y *Exportar PNG*. A la derecha, *Guía* muestra u oculta el panel de construcción, y **?** da acceso a la ayuda, los atajos, *Guardar como* y la información de la app. |
| **Panel izquierdo** | Selector de figura (el hexágono va primero), tamaño con campo numérico y deslizador sincronizados, orientación (solo en las figuras que la tienen), proporciones calculadas, contorno o relleno, y color. Cualquier cambio se aplica al instante. |
| **Cuadrícula central** | La figura, centrada al iniciar. Sobre ella, una barra con zoom, *Ajustar*, *Centrar* e interruptores de cuadrícula, ejes, marca del centro, numeración, fondo claro u oscuro y *Auto-ajuste*. Si falta espacio, la barra muestra solo los iconos. Rueda del ratón: zoom. Arrastrar: mover la vista. Clic: resaltar una fila. |
| **Construcción (derecha)** | Ancho, alto y bloques necesarios; centro y lado del hexágono; tabla por filas que se puede plegar; botones de fila anterior y siguiente; y *Copiar instrucciones*. El panel se redimensiona arrastrando su borde y se oculta con *Guía* (Ctrl+B). |
| **Barra de estado** | Columna y fila bajo el cursor (con su distancia al centro), resumen de la figura, nivel de zoom y avisos breves al guardar, copiar o exportar. |

**Cambios sin guardar:**

- El título de la ventana y la barra superior indican cuándo hay cambios sin guardar.
- Antes de cerrar, abrir otro diseño o empezar uno nuevo, la app pregunta si quieres guardarlos.
- Cambiar el color o el modo no reinicia el zoom ni el desplazamiento.

**Preferencias:** se guardan localmente el tamaño y la posición de la ventana, el ancho de los paneles, las opciones de vista, el fondo del lienzo, la última figura y la carpeta de trabajo.

**Seguir la construcción paso a paso:** haz clic en una fila del dibujo o de la tabla y avanza con *Anterior* y *Siguiente* o con ↑/↓. La fila se resalta en ámbar en ambos sitios; si está fuera de la vista, el lienzo se desplaza hasta ella.

**Leer la tabla:** `1 | 9–10` significa que esa fila tiene un bloque en la columna 1 y otro tramo de las columnas 9 a 10, ambas incluidas.

**Guías de lectura:**

- Las líneas más marcadas de la cuadrícula aparecen cada 5 bloques, contando desde la esquina superior izquierda de la figura.
- Los ejes y la marca del centro son solo ayudas visuales: **no cuentan como bloques** y nunca se exportan.
- El zoom y el desplazamiento solo cambian la vista; la figura y su número de bloques no se tocan.

### Atajos de teclado

| Teclas | Acción |
|---|---|
| Ctrl+N / Ctrl+O / Ctrl+S / Ctrl+Shift+S | Nuevo / abrir / guardar / guardar como |
| Ctrl+E · Ctrl+Shift+C | Exportar PNG · copiar instrucciones |
| Ctrl+1 / Ctrl+2 / Ctrl+3 | Hexágono / círculo / triángulo |
| Ctrl+L · Ctrl+T | Ir al campo de tamaño · alternar contorno y relleno |
| Ctrl++ / Ctrl+- / Ctrl+0 | Acercar / alejar / ajustar a la ventana |
| Ctrl+B | Mostrar u ocultar la guía de construcción |
| F / C | Ajustar / centrar (con el foco en la cuadrícula) |
| G / X / M / N / B / A | Cuadrícula / ejes / marca del centro / numeración / fondo claro / auto-ajuste (con el foco en la cuadrícula) |
| ↑ / ↓ · Esc | Fila anterior o siguiente · quitar resaltado |
| F1 · Ctrl+/ | Ayuda · lista de atajos |

Todos los controles se recorren con Tab y muestran un borde verde cuando tienen el foco. La cuadrícula también lo muestra.

### Exportar y guardar

- **Exportar PNG** (Ctrl+E): elige los píxeles por bloque, el fondo (claro, oscuro o transparente) y si quieres incluir la cuadrícula y la numeración. La imagen nunca lleva ejes ni marca del centro.
- **Guardar diseño** (Ctrl+S): crea un JSON con la configuración, las dimensiones, el centro, la tabla por filas y las coordenadas `[x, y]` de **todos** los bloques, numeradas desde 1 (columna 1 = izquierda, fila 1 = arriba).
- **Abrir diseño** (Ctrl+O): recalcula la figura a partir de la configuración y comprueba que coincide con los bloques guardados. Si no coinciden, avisa.

Los tamaños válidos van de 1 a 1000 bloques. Si escribes un valor fuera de ese rango:

- el campo se marca en rojo;
- un mensaje explica cómo corregirlo;
- se desactivan la exportación y el guardado.

---

## Cómo se interpretan las medidas

| Figura | Tamaño que introduces | Medida que se calcula |
|---|---|---|
| Círculo | **Diámetro** = ancho = alto | — |
| Triángulo equilátero | **Ancho de la base** (con el vértice a izquierda o derecha, la base es vertical) | Altura = base × √3/2 |
| Hexágono, **lado plano arriba** | **Ancho total de vértice a vértice** (= 2 × lado) | Alto = ancho × √3/2 ≈ 0,866 × ancho; lado = ancho/2 |
| Hexágono, **vértice arriba** | **Ancho total de lado plano a lado plano** | Alto = ancho × 2/√3 ≈ 1,155 × ancho; lado = ancho/√3 |

- **El ancho en bloques es siempre exactamente el que pides.** La otra dimensión se calcula con la proporción geométrica de la figura y después se convierte a bloques. La app muestra los dos valores; por ejemplo, «Alto calculado: 8,66 → 9 bloques».
- **Centro con tamaños impares:** hay una columna central (y una fila central, si el alto también es impar).
- **Centro con tamaños pares:** el centro cae sobre la línea entre dos columnas (o filas). La guía lo indica, por ejemplo: «fila 5, entre las columnas 5 y 6».
- En el triángulo, el «centro» es el centroide, a un tercio de la altura medido desde la base.

---

## Algoritmo geométrico

El código está en [figuras_bloques/geometria.py](figuras_bloques/geometria.py) y no depende de la interfaz.

1. **Figura continua exacta.** Se construye la figura regular ideal con el ancho pedido. El hexágono tiene sus seis lados iguales y ángulos de 120°; el triángulo es equilátero.

2. **Colocación sobre la cuadrícula.** La figura ocupa exactamente `[0, ancho]` en horizontal y queda centrada. En vertical caben dos colocaciones:
   - con el centro en una fila (alto impar);
   - con el centro en la línea entre dos filas (alto par).

   Se generan las dos y **se elige la que da un alto en bloques más cercano al teórico**; si empatan, la impar. En el triángulo se prueba la base apoyada en una línea de la cuadrícula o pasando por los centros de la última fila.

3. **Criterio de pertenencia: muestreo por centro.** Un bloque forma parte de la figura **si el centro de su celda está dentro de la figura o sobre su borde**. Para el borde se usa una tolerancia fija de 10⁻⁹, así que el resultado es determinista. Como las tres figuras son convexas, cada fila es un único tramo `[x0, x1]` que se calcula de forma analítica. La figura más grande, de 1000 bloques, se genera en milisegundos.

4. **Contorno.** Son los bloques del relleno que tienen al menos un vecino **ortogonal** (arriba, abajo, izquierda o derecha) fuera de la figura. Esto da un borde de un bloque de grosor que, en los escalones, se une en diagonal (como en las construcciones típicas) y que encierra el interior por completo.

5. **Simetrías.** El hexágono y el círculo se calculan a partir de la distancia al centro, así que salen exactamente simétricos de izquierda a derecha y de arriba abajo; el círculo, además, por la diagonal. Las orientaciones del triángulo son reflejos o la transpuesta de la misma figura.

### Por qué son aproximaciones

Un hexágono o un círculo regulares no se pueden formar exactamente con cuadrados. Sus bordes inclinados tienen pendientes irracionales: √3 en el hexágono, curva en el círculo. La cuadrícula solo conserva las simetrías de espejo horizontal y vertical, no los giros de 60°. Lo que da la app es **la mejor aproximación con bloques completos según un criterio único y consistente**:

- Los lados inclinados del hexágono con lado plano arriba avanzan 0 o 1 bloque por fila (pendiente real ≈ 0,58).
- Los del hexágono con vértice arriba avanzan 1 o 2 bloques por fila (pendiente real ≈ 1,73), y siguen la recta exacta con menos de un bloque de error.
- El alto real se aleja del teórico como máximo **0,5 bloques** en el hexágono con lado plano arriba y **0,58** en el de vértice arriba, para todos los anchos de 1 a 1000.
- En los vértices agudos del triángulo (60°), la diferencia puede llegar a 0,87 bloques.
- En tamaños muy pequeños (menos de unos 6 bloques), las figuras se parecen inevitablemente a cuadrados o rombos.

---

## Estructura del proyecto

```
main.py                         Punto de entrada
figuras_bloques/
  geometria.py                  Algoritmos (sin Qt): Configuracion → Figura (filas de tramos)
  guia.py                       Guía por filas, resumen y texto para copiar
  archivo.py                    Guardar y abrir JSON
  app.py                        Arranque, icono en la barra de tareas y --comprobar-recursos
  recursos/marca/               Logo e icono (SVG, PNG, ICO)
  recursos/iconos/              Iconos de interfaz (SVG) y marca de las casillas
  ui/tema.py                    Identidad: paleta, tipografía, hoja de estilos y paletas del lienzo
  ui/recursos.py                Carga de logo, iconos y miniaturas de figuras
  ui/ventana.py                 Ventana principal: barras, acciones, archivos y preferencias
  ui/panel_config.py            Panel de parámetros de la figura
  ui/panel_guia.py              Panel de construcción y tabla por filas
  ui/lienzo.py                  Cuadrícula interactiva (zoom, desplazamiento, fila resaltada)
  ui/render.py                  Dibujo compartido por el lienzo y el PNG
  ui/exportar.py                Exportación PNG
  ui/dialogos.py                Ayuda, atajos, información y confirmación de cambios
tests/                          Pruebas (pytest)
tools/generar_identidad.py      Regenera logo, icono e ICO a partir de la geometría
empaquetado/version_info.txt    Datos de versión del ejecutable
Hexabloq.spec                   Configuración de PyInstaller
construir_exe.bat               Genera dist\Hexabloq.exe
ejecutar.bat                    Ejecuta desde el código fuente
```

Los estilos y recursos visuales están separados de los cálculos: `geometria.py`, `guia.py` y `archivo.py` no dependen de Qt.

## Qué comprueban las pruebas

- **Hexágonos:**
  - Tamaños de 1 a 80 y también 99, 100, 127, 128, 255, 256, 499, 500, 999 y 1000; ambas orientaciones y ambos modos.
  - El ancho es exacto y el alto queda a 0,6 bloques o menos del teórico.
  - Hay simetría de izquierda a derecha y de arriba abajo, y el centro está donde debe.
  - La forma es convexa y los bordes inclinados avanzan 0–1 o 1–2 bloques por fila.
  - Los lados verticales son consecutivos y están centrados.
  - El borde sigue la recta real con menos de un bloque de error.
  - El contorno coincide con una comprobación por fuerza bruta, es una sola pieza continua, cierra el interior y no tiene nunca un grupo de 2×2 bloques.
- **Círculos y triángulos:** dimensiones, simetrías, continuidad del contorno y equivalencia entre las cuatro orientaciones del triángulo.
- **En todas las figuras:**
  - No hay coordenadas duplicadas.
  - El total coincide con la suma por filas, con la guía, con el JSON y con los bloques que aparecen en el PNG, con cualquier fondo.
  - El resultado es el mismo en cada ejecución.
  - Los tamaños no válidos dan un mensaje claro.
- **Interfaz** (sin mostrar la ventana):
  - El zoom y el desplazamiento no cambian la figura.
  - Cambiar el color o el modo no reinicia la vista.
  - El deslizador y el campo de tamaño están sincronizados.
  - Solo se muestran los parámetros de la figura elegida.
  - Los errores de tamaño explican cómo corregirlos.
  - La fila seleccionada está sincronizada entre el dibujo y la tabla.
  - Las coordenadas bajo el cursor y el zoom aparecen en la barra de estado.
  - Abrir, guardar y la confirmación de cambios sin guardar funcionan.
  - Las preferencias persisten entre sesiones.
  - Los atajos principales existen.
- **Recursos:** el logo, los iconos y el ICO (con varias resoluciones) cargan, también al ejecutar la app desde otro directorio.
