"""Algoritmos geométricos: convierten figuras regulares en bloques enteros.

Este módulo no depende de Qt. Todo lo que ve el usuario (lienzo, conteo,
guía, PNG y JSON) se obtiene de la :class:`Figura` que generan estas funciones.

Sistema de coordenadas
----------------------
* Cada bloque es la celda ``(x, y)`` con ``x`` = columna, ``y`` = fila,
  ambos enteros empezando en 0 en la esquina superior izquierda de la figura.
  La celda ocupa el cuadrado ``[x, x+1] × [y, y+1]`` en "unidades de bloque".
  La ``y`` crece hacia abajo (como al leer una plantilla fila a fila).
* La interfaz y los archivos muestran columnas y filas empezando en 1.

Criterio de pertenencia (muestreo por centro)
---------------------------------------------
Se construye la figura continua (círculo, triángulo o hexágono regular) con
su tamaño exacto y se coloca sobre la cuadrícula. Una celda pertenece a la
figura **si su centro** ``(x + 0.5, y + 0.5)`` **está dentro de la figura o
sobre su borde**. Como las tres figuras son convexas, cada fila queda formada
por un único tramo continuo, que se calcula de forma analítica (sin recorrer
todas las celdas), así que el coste es proporcional al número de filas.

Contorno
--------
El contorno es el subconjunto del relleno formado por los bloques que tienen
al menos un vecino *ortogonal* (arriba, abajo, izquierda o derecha) fuera de
la figura. El resultado es un borde de un bloque de grosor que se une en
diagonal en los escalones (como en las construcciones típicas de Minecraft) y
que cierra completamente la figura: rellenar el interior del contorno da
exactamente la figura rellena.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import cached_property
from typing import Callable, Iterator

# --------------------------------------------------------------------------
# Constantes y configuración
# --------------------------------------------------------------------------

TAMANO_MINIMO = 1
TAMANO_MAXIMO = 1000

#: Tolerancia para considerar que un centro situado exactamente sobre el borde
#: pertenece a la figura (evita depender de errores de redondeo).
EPS = 1e-9

RAIZ3 = math.sqrt(3.0)

FIGURAS = ("circulo", "triangulo", "hexagono")
MODOS = ("contorno", "relleno")
ORIENTACIONES = {
    "circulo": ("",),
    "triangulo": ("arriba", "abajo", "izquierda", "derecha"),
    "hexagono": ("plano", "vertice"),
}
ORIENTACION_POR_DEFECTO = {"circulo": "", "triangulo": "arriba", "hexagono": "plano"}

NOMBRES_FIGURA = {
    "circulo": "Círculo",
    "triangulo": "Triángulo equilátero",
    "hexagono": "Hexágono regular",
}
NOMBRES_ORIENTACION = {
    "": "",
    "arriba": "vértice arriba",
    "abajo": "vértice abajo",
    "izquierda": "vértice a la izquierda",
    "derecha": "vértice a la derecha",
    "plano": "lado plano arriba",
    "vertice": "vértice arriba",
}
NOMBRES_MODO = {"contorno": "contorno", "relleno": "relleno"}

Tramo = tuple[int, int]  # (x_inicio, x_fin) ambos incluidos, base 0
Fila = tuple[Tramo, ...]


class ErrorDeTamano(ValueError):
    """Parámetros no válidos, con un mensaje pensado para el usuario."""


@dataclass(frozen=True)
class Configuracion:
    figura: str = "hexagono"
    tamano: int = 21
    orientacion: str = "plano"
    modo: str = "contorno"
    color: str = "#5B8C3A"

    def validada(self) -> "Configuracion":
        """Devuelve la configuración normalizada o lanza :class:`ErrorDeTamano`."""
        if self.figura not in FIGURAS:
            raise ErrorDeTamano(f"Figura desconocida: «{self.figura}».")
        if self.modo not in MODOS:
            raise ErrorDeTamano(f"Modo desconocido: «{self.modo}».")
        orient = self.orientacion
        if orient not in ORIENTACIONES[self.figura]:
            if self.figura == "circulo":
                orient = ""
            else:
                validas = ", ".join(ORIENTACIONES[self.figura])
                raise ErrorDeTamano(
                    f"Orientación «{orient}» no válida para {NOMBRES_FIGURA[self.figura].lower()} "
                    f"(opciones: {validas})."
                )
        if isinstance(self.tamano, bool) or not isinstance(self.tamano, int):
            raise ErrorDeTamano("El tamaño debe ser un número entero de bloques.")
        if not TAMANO_MINIMO <= self.tamano <= TAMANO_MAXIMO:
            medida = MEDIDA_TAMANO[self.figura]
            raise ErrorDeTamano(
                f"El {medida} debe estar entre {TAMANO_MINIMO} y {TAMANO_MAXIMO} bloques "
                f"(has puesto {self.tamano})."
            )
        color = normalizar_color(self.color)
        return Configuracion(self.figura, self.tamano, orient, self.modo, color)


MEDIDA_TAMANO = {
    "circulo": "diámetro",
    "triangulo": "ancho de la base",
    "hexagono": "ancho total",
}


def normalizar_color(color: str) -> str:
    c = (color or "").strip()
    if not c.startswith("#"):
        c = "#" + c
    if len(c) == 4:  # #abc -> #aabbcc
        c = "#" + "".join(ch * 2 for ch in c[1:])
    if len(c) != 7 or any(ch not in "0123456789abcdefABCDEF" for ch in c[1:]):
        raise ErrorDeTamano(f"Color no válido: «{color}». Usa el formato #RRGGBB.")
    return c.upper()


# --------------------------------------------------------------------------
# Resultado
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Figura:
    """Conjunto determinista de bloques de una figura.

    ``filas[y]`` contiene los tramos ``(x0, x1)`` (incluidos) ocupados en la
    fila ``y``. Las filas van de 0 (arriba) a ``alto - 1`` (abajo) y las
    columnas de 0 (izquierda) a ``ancho - 1`` (derecha).
    """

    config: Configuracion
    filas: tuple[Fila, ...]
    ancho: int
    alto: int
    ancho_teorico: float
    alto_teorico: float
    #: Centro de la figura continua en unidades de bloque (0 = borde superior
    #: izquierdo). Si vale un entero + 0,5 cae en el centro de una celda; si es
    #: entero cae sobre una línea de la cuadrícula (entre dos bloques).
    centro: tuple[float, float]
    #: Relleno completo (útil para el modo contorno: el interior es relleno − contorno).
    filas_relleno: tuple[Fila, ...] = field(repr=False, default=())

    @cached_property
    def total(self) -> int:
        return sum(x1 - x0 + 1 for fila in self.filas for x0, x1 in fila)

    def bloques_por_fila(self) -> list[int]:
        return [sum(x1 - x0 + 1 for x0, x1 in fila) for fila in self.filas]

    def iter_celdas(self) -> Iterator[tuple[int, int]]:
        """Recorre los bloques en orden (fila, columna)."""
        for y, fila in enumerate(self.filas):
            for x0, x1 in fila:
                for x in range(x0, x1 + 1):
                    yield (x, y)

    @cached_property
    def celdas(self) -> tuple[tuple[int, int], ...]:
        return tuple(self.iter_celdas())

    @cached_property
    def conjunto(self) -> frozenset[tuple[int, int]]:
        return frozenset(self.celdas)

    def contiene(self, x: int, y: int) -> bool:
        if not 0 <= y < self.alto:
            return False
        return any(x0 <= x <= x1 for x0, x1 in self.filas[y])

    @property
    def lado_plano(self) -> int | None:
        """Bloques del lado recto principal del hexágono (None para otras figuras).

        * Lado plano arriba: longitud de la fila superior.
        * Vértice arriba: número de filas que ocupan todo el ancho (lados verticales).
        """
        if self.config.figura != "hexagono":
            return None
        relleno = self.filas_relleno or self.filas
        if self.config.orientacion == "plano":
            x0, x1 = relleno[0][0]
            return x1 - x0 + 1
        return sum(1 for f in relleno if f and f[0][0] == 0 and f[-1][1] == self.ancho - 1)


# --------------------------------------------------------------------------
# Utilidades de rasterizado
# --------------------------------------------------------------------------


def _tramo_centrado(cx: float, semiancho: float) -> Tramo | None:
    """Columnas cuyo centro (x + 0,5) cae en [cx − semiancho, cx + semiancho]."""
    if semiancho < -EPS:
        return None
    x0 = math.ceil(cx - semiancho - 0.5 - EPS)
    x1 = math.floor(cx + semiancho - 0.5 + EPS)
    if x0 > x1:
        return None
    return (x0, x1)


def _filas_simetricas(
    ancho: int,
    semiancho: Callable[[float], float | None],
    alto_teorico: float,
) -> tuple[list[Tramo], float]:
    """Rasteriza una figura convexa con simetría vertical y horizontal.

    ``semiancho(dy)`` da la mitad del ancho de la figura continua a una
    distancia vertical ``dy >= 0`` de su centro (o ``None`` si queda fuera).

    El centro horizontal está fijado en ``ancho / 2`` (el ancho exacto). El
    centro vertical puede caer en el centro de una fila (alto impar) o en la
    línea entre dos filas (alto par). Se prueban ambas opciones y se elige la
    que deja un alto en bloques más próximo al alto teórico; en caso de empate,
    la de alto impar (tiene una fila central clara).
    """
    cx = ancho / 2.0
    candidatos: list[tuple[float, int, list[Tramo]]] = []
    for impar in (True, False):
        # Distancias de los centros de fila al centro: 0, 1, 2… o 0,5, 1,5…
        mitad: list[Tramo] = []
        k = 0
        while True:
            dy = k if impar else k + 0.5
            s = semiancho(dy)
            tramo = _tramo_centrado(cx, s) if s is not None else None
            if tramo is None:
                break
            mitad.append(tramo)
            k += 1
        if not mitad:
            continue
        if impar:
            filas = list(reversed(mitad[1:])) + mitad
        else:
            filas = list(reversed(mitad)) + mitad
        alto = len(filas)
        candidatos.append((abs(alto - alto_teorico), 0 if impar else 1, filas))
    if not candidatos:
        raise ErrorDeTamano("La figura es demasiado pequeña para ocupar algún bloque.")
    candidatos.sort(key=lambda c: (c[0], c[1]))
    filas = candidatos[0][2]
    return filas, len(filas) / 2.0


def _contorno(filas: list[Tramo | None]) -> list[Fila]:
    """Bloques del relleno con algún vecino ortogonal fuera de la figura.

    ``filas`` tiene un único tramo por fila (figuras convexas). Para cada
    fila, el interior es el tramo de bloques cuyos cuatro vecinos están en la
    figura: ``[max(x0+1, x0_arriba, x0_abajo), min(x1−1, x1_arriba, x1_abajo)]``.
    El contorno es la fila menos ese interior (uno o dos tramos).
    """
    resultado: list[Fila] = []
    n = len(filas)
    for y, tramo in enumerate(filas):
        if tramo is None:
            resultado.append(())
            continue
        x0, x1 = tramo
        arriba = filas[y - 1] if y > 0 else None
        abajo = filas[y + 1] if y + 1 < n else None
        if arriba is None or abajo is None:
            resultado.append(((x0, x1),))
            continue
        i0 = max(x0 + 1, arriba[0], abajo[0])
        i1 = min(x1 - 1, arriba[1], abajo[1])
        if i0 > i1:
            resultado.append(((x0, x1),))
            continue
        partes: list[Tramo] = []
        if i0 > x0:
            partes.append((x0, i0 - 1))
        if i1 < x1:
            partes.append((i1 + 1, x1))
        resultado.append(tuple(partes))
    return resultado


def _transponer(filas: list[Tramo], ancho: int) -> list[Tramo]:
    """Intercambia filas y columnas de una figura convexa (una fila = un tramo)."""
    alto = len(filas)
    nuevas: list[Tramo] = []
    for x in range(ancho):
        ys = [y for y in range(alto) if filas[y][0] <= x <= filas[y][1]]
        nuevas.append((min(ys), max(ys)))
    return nuevas


# --------------------------------------------------------------------------
# Figuras
# --------------------------------------------------------------------------


def _filas_circulo(diametro: int) -> tuple[list[Tramo], int, int, float, float, tuple[float, float]]:
    r = diametro / 2.0
    c = diametro / 2.0
    filas: list[Tramo] = []
    for y in range(diametro):
        dy = (y + 0.5) - c
        resto = r * r - dy * dy
        s = math.sqrt(resto) if resto > 0 else (0.0 if resto > -EPS else -1.0)
        tramo = _tramo_centrado(c, s)
        assert tramo is not None
        filas.append(tramo)
    return filas, diametro, diametro, float(diametro), float(diametro), (c, c)


def _filas_hexagono(ancho: int, orientacion: str):
    if orientacion == "plano":
        # Lado plano arriba: vértices a izquierda y derecha. Ancho = 2R.
        radio = ancho / 2.0
        alto_teorico = ancho * RAIZ3 / 2.0
        mitad_alto = alto_teorico / 2.0

        def semiancho(dy: float) -> float | None:
            if dy > mitad_alto + EPS:
                return None
            return radio - dy / RAIZ3

    else:
        # Vértice arriba: lados verticales a izquierda y derecha. Ancho = 2·apotema.
        apotema = ancho / 2.0
        radio = ancho / RAIZ3
        alto_teorico = 2.0 * radio

        def semiancho(dy: float) -> float | None:
            if dy > radio + EPS:
                return None
            if dy <= radio / 2.0:
                return apotema
            return (radio - dy) * RAIZ3

    filas, cy = _filas_simetricas(ancho, semiancho, alto_teorico)
    return filas, ancho, len(filas), float(ancho), alto_teorico, (ancho / 2.0, cy)


def _filas_triangulo(base: int, orientacion: str):
    """Triángulo equilátero de base ``base``.

    Se calcula con el vértice arriba y la base apoyada exactamente en la línea
    inferior de la cuadrícula; las demás orientaciones son reflejos o la
    transpuesta de esa misma figura, así que son idénticas salvo por el giro.
    """
    altura = base * RAIZ3 / 2.0
    cx = base / 2.0
    # La base puede apoyarse en la línea inferior de la cuadrícula (desfase 0,5:
    # los centros de fila quedan a 0,5, 1,5… de la base) o pasar por los centros
    # de la fila inferior (desfase 0). Igual que en el hexágono, se elige la
    # colocación cuyo alto en bloques se acerca más al teórico; si empatan,
    # la base sobre la línea de la cuadrícula.
    candidatos = []
    for preferencia, desfase in enumerate((0.5, 0.0)):
        desde_base: list[Tramo] = []
        k = 0
        while True:
            d = k + desfase  # altura del centro de la fila sobre la base
            if d > altura + EPS:
                break
            tramo = _tramo_centrado(cx, (altura - d) / RAIZ3)
            if tramo is None:
                break
            desde_base.append(tramo)
            k += 1
        if desde_base:
            candidatos.append((abs(len(desde_base) - altura), preferencia, desfase, desde_base))
    if not candidatos:
        raise ErrorDeTamano("La figura es demasiado pequeña para ocupar algún bloque.")
    candidatos.sort(key=lambda c: (c[0], c[1]))
    _, _, desfase, desde_base = candidatos[0]
    filas = list(reversed(desde_base))  # de arriba (vértice) a abajo (base)
    alto = len(filas)
    # La base continua está en y = alto − 0,5 + desfase. El centroide del
    # triángulo está a un tercio de la altura por encima de la base.
    cy = (alto - 0.5 + desfase) - altura / 3.0
    if orientacion == "arriba":
        return filas, base, alto, float(base), altura, (cx, cy)
    if orientacion == "abajo":
        return list(reversed(filas)), base, alto, float(base), altura, (cx, alto - cy)
    # Izquierda / derecha: la base pasa a ser vertical.
    transpuesta = _transponer(filas, base)  # vértice a la izquierda
    ancho, nuevo_alto = alto, base
    if orientacion == "izquierda":
        return transpuesta, ancho, nuevo_alto, altura, float(base), (cy, cx)
    # derecha: reflejo horizontal
    reflejada = [(ancho - 1 - x1, ancho - 1 - x0) for x0, x1 in transpuesta]
    return reflejada, ancho, nuevo_alto, altura, float(base), (ancho - cy, cx)


def generar(config: Configuracion) -> Figura:
    """Genera la figura en bloques para una configuración (validándola antes)."""
    cfg = config.validada()
    if cfg.figura == "circulo":
        datos = _filas_circulo(cfg.tamano)
    elif cfg.figura == "hexagono":
        datos = _filas_hexagono(cfg.tamano, cfg.orientacion)
    else:
        datos = _filas_triangulo(cfg.tamano, cfg.orientacion)
    filas, ancho, alto, ancho_t, alto_t, centro = datos

    relleno: tuple[Fila, ...] = tuple(((t,) if t else ()) for t in filas)
    if cfg.modo == "relleno":
        visibles = relleno
    else:
        visibles = tuple(_contorno(list(filas)))
    return Figura(
        config=cfg,
        filas=visibles,
        ancho=ancho,
        alto=alto,
        ancho_teorico=ancho_t,
        alto_teorico=alto_t,
        centro=centro,
        filas_relleno=relleno,
    )


def descripcion(config: Configuracion) -> str:
    nombre = NOMBRES_FIGURA[config.figura]
    orient = NOMBRES_ORIENTACION.get(config.orientacion, "")
    partes = [nombre]
    if orient:
        partes.append(f"({orient})")
    partes.append(f"— {NOMBRES_MODO[config.modo]}")
    return " ".join(partes)
