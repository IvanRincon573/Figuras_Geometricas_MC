"""Conversión de figuras regulares en bloques enteros.

Una celda (x, y) pertenece a la figura si su centro (x + 0,5, y + 0,5) cae
dentro de la figura continua o sobre su borde. En el hexágono, cada lado inclinado
se desplaza menos de media fila para que sus escalones sean simétricos. El contorno
son los bloques del relleno con algún vecino ortogonal fuera de la figura.
"""

from __future__ import annotations

import functools
import itertools
import math
from dataclasses import dataclass, field, replace
from functools import cached_property
from typing import Callable, Iterator, TypeVar

TAMANO_MINIMO = 1
TAMANO_MAXIMO = 1000
EPS = 1e-9  # incluye los centros que caen exactamente sobre el borde
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
MEDIDA_TAMANO = {
    "circulo": "diámetro",
    "triangulo": "ancho de la base",
    "hexagono": "ancho total",
}

Tramo = tuple[int, int]
Fila = tuple[Tramo, ...]
T = TypeVar("T")


class ErrorDeTamano(ValueError):
    """Parámetros no válidos, con un mensaje pensado para el usuario."""


@dataclass(frozen=True)
class Configuracion:
    figura: str = "hexagono"
    tamano: int = 21
    orientacion: str = "plano"
    modo: str = "contorno"
    color: str = "#5B8C3A"

    def validada(self) -> Configuracion:
        if self.figura not in FIGURAS:
            raise ErrorDeTamano(f"Figura desconocida: «{self.figura}».")
        if self.modo not in MODOS:
            raise ErrorDeTamano(f"Modo desconocido: «{self.modo}».")
        orientacion = self._orientacion_valida()
        self._validar_tamano()
        return replace(self, orientacion=orientacion, color=normalizar_color(self.color))

    def _orientacion_valida(self) -> str:
        if self.orientacion in ORIENTACIONES[self.figura]:
            return self.orientacion
        if self.figura == "circulo":
            return ""
        validas = ", ".join(ORIENTACIONES[self.figura])
        raise ErrorDeTamano(
            f"Orientación «{self.orientacion}» no válida para "
            f"{NOMBRES_FIGURA[self.figura].lower()} (opciones: {validas})."
        )

    def _validar_tamano(self) -> None:
        if isinstance(self.tamano, bool) or not isinstance(self.tamano, int):
            raise ErrorDeTamano("El tamaño debe ser un número entero de bloques.")
        if not TAMANO_MINIMO <= self.tamano <= TAMANO_MAXIMO:
            raise ErrorDeTamano(
                f"El {MEDIDA_TAMANO[self.figura]} debe estar entre {TAMANO_MINIMO} y "
                f"{TAMANO_MAXIMO} bloques (has puesto {self.tamano})."
            )


def normalizar_color(color: str) -> str:
    c = (color or "").strip()
    if not c.startswith("#"):
        c = "#" + c
    if len(c) == 4:
        c = "#" + "".join(ch * 2 for ch in c[1:])
    if len(c) != 7 or any(ch not in "0123456789abcdefABCDEF" for ch in c[1:]):
        raise ErrorDeTamano(f"Color no válido: «{color}». Usa el formato #RRGGBB.")
    return c.upper()


@dataclass(frozen=True)
class Figura:
    """Bloques de una figura agrupados por filas.

    ``filas[y]`` son los tramos ``(x0, x1)``, con ambos extremos incluidos.
    Filas y columnas empiezan en 0 en la esquina superior izquierda. ``centro``
    está en unidades de bloque: x,5 es el centro de una celda y un entero es la
    línea entre dos celdas.
    """

    config: Configuracion
    filas: tuple[Fila, ...]
    ancho: int
    alto: int
    ancho_teorico: float
    alto_teorico: float
    centro: tuple[float, float]
    filas_relleno: tuple[Fila, ...] = field(repr=False)

    @cached_property
    def total(self) -> int:
        return sum(self.bloques_por_fila())

    def bloques_por_fila(self) -> list[int]:
        return [sum(x1 - x0 + 1 for x0, x1 in fila) for fila in self.filas]

    def iter_celdas(self) -> Iterator[tuple[int, int]]:
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
        """Bloques de la fila superior (lado plano arriba) o filas de ancho completo (vértice arriba)."""
        if self.config.figura != "hexagono":
            return None
        if self.config.orientacion == "plano":
            x0, x1 = self.filas_relleno[0][0]
            return x1 - x0 + 1
        ancho_completo = ((0, self.ancho - 1),)
        return sum(1 for fila in self.filas_relleno if fila == ancho_completo)


@dataclass(frozen=True)
class _Rasterizado:
    filas: list[Tramo]
    ancho: int
    ancho_teorico: float
    alto_teorico: float
    centro: tuple[float, float]


def _tramo_centrado(cx: float, semiancho: float | None) -> Tramo | None:
    """Columnas cuyo centro cae en [cx − semiancho, cx + semiancho]."""
    if semiancho is None or semiancho < -EPS:
        return None
    x0 = math.ceil(cx - semiancho - 0.5 - EPS)
    x1 = math.floor(cx + semiancho - 0.5 + EPS)
    return (x0, x1) if x0 <= x1 else None


def _apilar(semiancho_de_fila: Callable[[int], float | None], cx: float) -> list[Tramo]:
    """Tramos de las filas k = 0, 1, 2… hasta la primera que queda vacía."""
    tramos: list[Tramo] = []
    for k in itertools.count():
        tramo = _tramo_centrado(cx, semiancho_de_fila(k))
        if tramo is None:
            return tramos
        tramos.append(tramo)
    raise AssertionError("inalcanzable")


def _mas_cercano(candidatos: list[tuple[list[Tramo], T]], alto_teorico: float) -> tuple[list[Tramo], T]:
    """Colocación con el alto más próximo al teórico; en empate gana la primera."""
    validos = [c for c in candidatos if c[0]]
    if not validos:
        raise ErrorDeTamano("La figura es demasiado pequeña para ocupar algún bloque.")
    return min(validos, key=lambda c: abs(len(c[0]) - alto_teorico))


def _contorno(filas: list[Tramo]) -> list[Fila]:
    """Quita de cada fila su interior: los bloques con los cuatro vecinos dentro."""
    ultima = len(filas) - 1
    contorno: list[Fila] = []
    for y, (x0, x1) in enumerate(filas):
        if y in (0, ultima):
            contorno.append(((x0, x1),))
            continue
        arriba, abajo = filas[y - 1], filas[y + 1]
        i0 = max(x0 + 1, arriba[0], abajo[0])
        i1 = min(x1 - 1, arriba[1], abajo[1])
        contorno.append(((x0, x1),) if i0 > i1 else ((x0, i0 - 1), (i1 + 1, x1)))
    return contorno


def _primeras_filas(filas: list[Tramo], ancho: int) -> list[int]:
    """Primera fila que cubre cada columna en una figura convexa."""
    primera = [0] * ancho
    izq, der = ancho, -1
    for y, (x0, x1) in enumerate(filas):
        for x in itertools.chain(range(x0, min(izq, x1 + 1)), range(max(der + 1, x0), x1 + 1)):
            primera[x] = y
        izq, der = min(izq, x0), max(der, x1)
    return primera


def _transponer(filas: list[Tramo], ancho: int) -> list[Tramo]:
    """Columnas de una figura convexa, en tiempo proporcional a su contorno."""
    ultima = len(filas) - 1
    desde_abajo = _primeras_filas(filas[::-1], ancho)
    return [(y0, ultima - y1) for y0, y1 in zip(_primeras_filas(filas, ancho), desde_abajo)]


def _circulo(diametro: int) -> _Rasterizado:
    radio = centro = diametro / 2
    filas = []
    for y in range(diametro):
        dy = y + 0.5 - centro
        filas.append(_tramo_centrado(centro, math.sqrt(max(radio * radio - dy * dy, 0.0))))
    return _Rasterizado(filas, diametro, diametro, diametro, (centro, centro))


def _columnas_borde(alto: int, desfase: float) -> list[int]:
    """Primera columna de cada fila, de la central hacia arriba, con el borde inclinado
    desplazado ``desfase`` filas respecto al del hexágono exacto."""
    dy0 = 0.0 if alto % 2 else 0.5
    return [math.ceil((dy0 + k - desfase) / RAIZ3 - 0.5 - EPS) for k in range((alto + 1) // 2)]


def _asimetria(columnas: list[int]) -> int:
    """Escalones interiores que no coinciden con su simétrico respecto al punto medio del lado."""
    escalones = [len(list(grupo)) for _, grupo in itertools.groupby(columnas)][1:-1]
    return sum(a != b for a, b in zip(escalones, reversed(escalones)))


def _desfases(alto: int, base: float) -> list[float]:
    """Un desfase por cada patrón de escalones distinto a menos de media fila de ``base``,
    ordenados de menor a mayor alejamiento."""
    dy0 = 0.0 if alto % 2 else 0.5
    cortes = {base - 0.5, base + 0.5}
    for j in range(alto // 2 + 2):
        corte = dy0 - (j + 0.5) * RAIZ3
        corte += math.ceil(base - 0.5 - corte)
        if corte < base + 0.5:
            cortes.add(corte)
    puntos = sorted(cortes)
    desfases = []
    for a, b in zip(puntos, puntos[1:]):
        if a < base < b:
            desfases.append(base)
        else:
            desfases.append(b - 1e-6 if b <= base else a + 1e-6)
    return sorted(desfases, key=lambda d: abs(d - base))


@functools.lru_cache(maxsize=256)
def _hexagono_plano(ancho: int, alto: int, base: float) -> tuple[Tramo, ...]:
    """Hexágono de lado plano arriba en ``ancho`` × ``alto`` bloques.

    Cada lado inclinado se desplaza menos de media fila (≈0,3 bloques en horizontal)
    para que sus escalones se lean igual desde ambos extremos, sin alargar ni acortar
    el lado plano más de un bloque."""
    lado_ideal = ancho - (alto - 2 * base) / RAIZ3
    mejor: tuple[bool, int, float, list[int]] | None = None
    for desfase in _desfases(alto, base):
        columnas = _columnas_borde(alto, desfase)
        if columnas[0] != 0:
            continue
        lado = ancho - 2 * columnas[-1]
        clave = (abs(lado - lado_ideal) > 1.5, _asimetria(columnas), abs(desfase - base))
        if mejor is None or clave < mejor[:3]:
            mejor = (*clave, columnas)
        if not clave[0] and clave[1] == 0:
            break
    assert mejor is not None
    mitad = [(x0, ancho - 1 - x0) for x0 in mejor[3]]
    return tuple(mitad[:0:-1] + mitad if alto % 2 else mitad[::-1] + mitad)


def _hexagono(ancho: int, orientacion: str) -> _Rasterizado:
    if orientacion == "plano":
        alto_teorico = ancho * RAIZ3 / 2
        filas = list(_hexagono_plano(ancho, round(alto_teorico), 0.0))
        return _Rasterizado(filas, ancho, ancho, alto_teorico, (ancho / 2, len(filas) / 2))
    alto_teorico = 2 * ancho / RAIZ3
    largo = round(alto_teorico)
    tumbado = list(_hexagono_plano(largo, ancho, ancho - largo * RAIZ3 / 2))
    return _Rasterizado(_transponer(tumbado, largo), ancho, ancho, alto_teorico, (ancho / 2, largo / 2))


def _triangulo(base: int, orientacion: str) -> _Rasterizado:
    """Se calcula con el vértice arriba; las otras orientaciones son reflejos o la transpuesta."""
    altura = base * RAIZ3 / 2
    cx = base / 2

    def semiancho(d: float) -> float | None:
        return None if d > altura + EPS else (altura - d) / RAIZ3

    # Desfase 0,5: base sobre una línea de la cuadrícula; 0: base por los centros de la última fila.
    candidatos = [
        (_apilar(lambda k, s=desfase: semiancho(k + s), cx), desfase) for desfase in (0.5, 0.0)
    ]
    desde_base, desfase = _mas_cercano(candidatos, altura)
    filas = desde_base[::-1]
    alto = len(filas)
    cy = alto - 0.5 + desfase - altura / 3

    if orientacion == "arriba":
        return _Rasterizado(filas, base, base, altura, (cx, cy))
    if orientacion == "abajo":
        return _Rasterizado(filas[::-1], base, base, altura, (cx, alto - cy))
    transpuesta = _transponer(filas, base)
    if orientacion == "izquierda":
        return _Rasterizado(transpuesta, alto, altura, base, (cy, cx))
    reflejada = [(alto - 1 - x1, alto - 1 - x0) for x0, x1 in transpuesta]
    return _Rasterizado(reflejada, alto, altura, base, (alto - cy, cx))


def _rasterizar(cfg: Configuracion) -> _Rasterizado:
    if cfg.figura == "circulo":
        return _circulo(cfg.tamano)
    if cfg.figura == "hexagono":
        return _hexagono(cfg.tamano, cfg.orientacion)
    return _triangulo(cfg.tamano, cfg.orientacion)


def generar(config: Configuracion) -> Figura:
    cfg = config.validada()
    r = _rasterizar(cfg)
    relleno = tuple((tramo,) for tramo in r.filas)
    visibles = relleno if cfg.modo == "relleno" else tuple(_contorno(r.filas))
    return Figura(
        config=cfg,
        filas=visibles,
        ancho=r.ancho,
        alto=len(r.filas),
        ancho_teorico=float(r.ancho_teorico),
        alto_teorico=float(r.alto_teorico),
        centro=r.centro,
        filas_relleno=relleno,
    )


def descripcion(config: Configuracion) -> str:
    texto = NOMBRES_FIGURA[config.figura]
    orientacion = NOMBRES_ORIENTACION.get(config.orientacion, "")
    if orientacion:
        texto += f" ({orientacion})"
    return f"{texto} — {config.modo}"
