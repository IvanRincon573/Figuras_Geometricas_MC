# Figuras con bloques

Aplicación de escritorio para Windows que genera **círculos, triángulos equiláteros y hexágonos regulares** hechos con bloques cuadrados, como plantilla para construir en Minecraft. Cada celda de la cuadrícula es un bloque completo: sin suavizado ni bloques parciales.

- Programa con ventana propia (Python + PySide6). No usa navegador, servidor ni conexión a internet.
- El conteo, el dibujo, la guía por filas, el PNG y el JSON salen **del mismo conjunto de bloques**.

---

## Instalación y ejecución

### Opción A: ejecutable (no necesita Python)

Ejecuta `dist\FigurasBloques.exe`. Es un único archivo que puedes copiar donde quieras.

Para volver a generarlo, haz doble clic en **`construir_exe.bat`**. El script:

1. crea el entorno virtual `.venv` si no existe;
2. instala `requirements-dev.txt`;
3. ejecuta las pruebas y se detiene si alguna falla;
4. genera `dist\FigurasBloques.exe` con PyInstaller, según `FigurasBloques.spec`.

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
| **Panel izquierdo** | Figura, tamaño en bloques (con botones ±1 y ±10), orientación, proporciones calculadas, modo contorno o relleno, y color. Cualquier cambio se aplica al instante. |
| **Cuadrícula central** | La figura. Rueda del ratón: zoom. Arrastrar: mover la vista. Clic: resaltar una fila. ↑ / ↓: fila anterior o siguiente. Esc: quitar el resaltado. |
| **Barra superior** | Abrir, guardar, exportar PNG, zoom, *Centrar*, *Ajustar a la ventana* y casillas para mostrar u ocultar cuadrícula, ejes, centro y numeración. *Ajuste automático* reencuadra la vista al cambiar el tamaño. |
| **Guía (derecha)** | Bloques necesarios, ancho y alto reales, centro y longitud del lado del hexágono. Debajo, una tabla por filas con el número de bloques y sus tramos. *Copiar instrucciones* copia toda la guía como texto. |
| **Barra de estado** | Columna y fila bajo el cursor, si esa celda es un bloque de la figura, y su distancia al centro. |

**Seguir la construcción paso a paso:** haz clic en una fila (en el dibujo o en la tabla) y avanza con ▲/▼ o con las flechas del teclado. La fila resaltada se marca en naranja en ambos sitios.

**Leer la tabla:** `1 | 9–10` significa que esa fila tiene un bloque en la columna 1 y otro tramo de las columnas 9 a 10, ambas incluidas. Las filas con bloques separados muestran siempre cada tramo por separado.

**Guías de lectura:**

- Las líneas más marcadas de la cuadrícula aparecen cada 5 bloques, contando desde la esquina superior izquierda de la figura.
- Los ejes (rojo vertical y azul horizontal) y la marca del centro son solo ayudas visuales: **no cuentan como bloques** y nunca se exportan como tales.
- El zoom y el desplazamiento solo cambian la vista; la figura y su número de bloques no se tocan.

### Exportar y guardar

- **Exportar PNG** (Ctrl+E): elige los píxeles por bloque y si quieres incluir la cuadrícula, la numeración y el fondo transparente. La imagen nunca lleva ejes ni marca del centro.
- **Guardar diseño** (Ctrl+S): crea un JSON con la configuración, las dimensiones, el centro, la tabla por filas y las coordenadas `[x, y]` de **todos** los bloques, numeradas desde 1 (columna 1 = izquierda, fila 1 = arriba).
- **Abrir diseño** (Ctrl+O): recalcula la figura a partir de la configuración y comprueba que coincide con los bloques guardados. Si no coinciden, avisa.

Los tamaños válidos van de 1 a 1000 bloques. Si escribes un valor fuera de ese rango, aparece un mensaje en rojo y se desactivan la exportación y el guardado.

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
main.py                     Punto de entrada
figuras_bloques/
  geometria.py              Algoritmos (sin Qt): Configuracion → Figura (filas de tramos)
  guia.py                   Guía por filas, resumen y texto para copiar
  archivo.py                Guardar y abrir JSON
  app.py                    Arranque de la aplicación Qt
  ui/ventana.py             Ventana principal, panel, tabla y exportación PNG
  ui/lienzo.py              Cuadrícula interactiva (zoom, desplazamiento, fila resaltada)
  ui/render.py              Dibujo compartido por el lienzo y el PNG
  ui/estilo.py              Tema visual
tests/                      Pruebas (pytest)
assets/                     Icono y recursos
tools/generar_icono.py      Regenera el icono a partir de la propia geometría
FigurasBloques.spec         Configuración de PyInstaller
construir_exe.bat           Genera dist\FigurasBloques.exe
ejecutar.bat                Ejecuta desde el código fuente
```

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
  - El total coincide con la suma por filas, con la guía, con el JSON y con los bloques que aparecen en el PNG.
  - El resultado es el mismo en cada ejecución.
  - Los tamaños no válidos dan un mensaje claro.
- **Interfaz** (sin mostrar la ventana): el zoom y el desplazamiento no cambian la figura; los cambios de parámetros actualizan la tabla y el total; la selección de fila está sincronizada entre el dibujo y la tabla; las coordenadas bajo el cursor son correctas; y abrir y guardar funciona.
