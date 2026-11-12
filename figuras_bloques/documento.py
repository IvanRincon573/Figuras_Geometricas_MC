"""Modelo del documento: objetos colocados en el mundo, grupos y figuras compuestas.

Coordenadas del mundo vistas desde arriba: X crece hacia el este (derecha) y Z hacia el sur
(abajo), como en Minecraft. La posición de un objeto es la esquina superior izquierda (X y Z
mínimos) de su caja de bloques.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, replace
from functools import lru_cache

from . import intervalos as iv
from .geometria import Configuracion, generar

COMPUESTA = "compuesta"
FUSION_BLOQUES = "bloques"
FUSION_SILUETA = "silueta"
FUSIONES = (FUSION_BLOQUES, FUSION_SILUETA)
COLOR_POR_DEFECTO = "#5B8C3A"

NOMBRES_TIPO = {
    "circulo": "Círculo",
    "triangulo": "Triángulo",
    "hexagono": "Hexágono",
    COMPUESTA: "Compuesta",
}
NOMBRES_FUSION = {
    FUSION_BLOQUES: "bloques conservados",
    FUSION_SILUETA: "silueta conjunta",
}

FilasRelativas = tuple[iv.Fila, ...]


@dataclass(frozen=True)
class Forma:
    """Bloques de un objeto relativos a su esquina: ``filas[dz]`` contiene los tramos en X."""

    filas: FilasRelativas
    superficie: FilasRelativas
    ancho: int
    alto: int
    centro: tuple[float, float]

    @property
    def total(self) -> int:
        return sum(iv.longitud(f) for f in self.filas)


@dataclass(frozen=True)
class Objeto:
    id: str
    nombre: str
    tipo: str
    x: int = 0
    z: int = 0
    tamano: int = 21
    orientacion: str = "plano"
    modo: str = "contorno"
    color: str = COLOR_POR_DEFECTO
    visible: bool = True
    bloqueado: bool = False
    grupo: str | None = None
    fusion: str = ""
    origenes: tuple[Objeto, ...] = ()

    @property
    def es_compuesta(self) -> bool:
        return self.tipo == COMPUESTA

    def configuracion(self) -> Configuracion:
        return Configuracion(self.tipo, self.tamano, self.orientacion, self.modo, self.color)

    def forma(self) -> Forma:
        return _forma(_clave_forma(self))

    def limites(self) -> tuple[int, int, int, int]:
        """(x0, z0, x1, z1) inclusivos de la caja del objeto en el mundo."""
        forma = self.forma()
        return self.x, self.z, self.x + forma.ancho - 1, self.z + forma.alto - 1

    def centro(self) -> tuple[float, float]:
        cx, cz = self.forma().centro
        return self.x + cx, self.z + cz

    def cubre(self, x: int, z: int) -> bool:
        """Si el bloque cae dentro del área del objeto (no solo en sus bloques de contorno)."""
        forma = self.forma()
        dz = z - self.z
        if not 0 <= dz < forma.alto:
            return False
        return any(a <= x - self.x <= b for a, b in forma.superficie[dz])

    def mover(self, dx: int, dz: int) -> Objeto:
        return replace(self, x=self.x + dx, z=self.z + dz)


def _clave_forma(objeto: Objeto) -> Objeto:
    """Copia sin los atributos que no afectan a la forma, para compartir la caché."""
    return replace(objeto, id="", nombre="", x=0, z=0, color="#000000",
                   visible=True, bloqueado=False, grupo=None)


@lru_cache(maxsize=512)
def _forma(objeto: Objeto) -> Forma:
    if objeto.es_compuesta:
        return _forma_compuesta(objeto)
    figura = generar(objeto.configuracion())
    return Forma(
        filas=figura.filas,
        superficie=figura.filas_relleno,
        ancho=figura.ancho,
        alto=figura.alto,
        centro=figura.centro,
    )


def _filas_trasladadas(origenes: tuple[Objeto, ...], atributo: str) -> FilasRelativas:
    por_z: dict[int, list] = defaultdict(list)
    for origen in origenes:
        forma = origen.forma()
        for dz, fila in enumerate(getattr(forma, atributo)):
            por_z[origen.z + dz].append(iv.desplazar(fila, origen.x))
    alto = max(por_z) + 1 if por_z else 0
    return tuple(iv.unir(*por_z.get(z, ())) for z in range(alto))


def _forma_compuesta(objeto: Objeto) -> Forma:
    superficie = _filas_trasladadas(objeto.origenes, "superficie")
    if objeto.fusion == FUSION_BLOQUES:
        filas = _filas_trasladadas(objeto.origenes, "filas")
    elif objeto.modo == "relleno":
        filas = superficie
    else:
        filas = iv.contorno(superficie)
    alto = max(len(filas), len(superficie))
    filas = filas + ((),) * (alto - len(filas))
    ancho = max((fila[-1][1] + 1 for fila in superficie + filas if fila), default=0)
    return Forma(filas=filas, superficie=superficie, ancho=ancho, alto=alto, centro=(ancho / 2, alto / 2))


@dataclass(frozen=True)
class Grupo:
    id: str
    nombre: str


@dataclass(frozen=True)
class Documento:
    """Objetos en orden de apilado: los últimos quedan por encima al resolver colores."""

    objetos: tuple[Objeto, ...] = ()
    grupos: tuple[Grupo, ...] = ()

    def buscar(self, id_objeto: str) -> Objeto | None:
        return next((o for o in self.objetos if o.id == id_objeto), None)

    def indice(self, id_objeto: str) -> int:
        return next(i for i, o in enumerate(self.objetos) if o.id == id_objeto)

    def grupo(self, id_grupo: str | None) -> Grupo | None:
        return next((g for g in self.grupos if g.id == id_grupo), None)

    def miembros(self, id_grupo: str) -> tuple[Objeto, ...]:
        return tuple(o for o in self.objetos if o.grupo == id_grupo)

    def con_grupos(self, ids) -> tuple[str, ...]:
        """Amplía una selección para incluir a todos los miembros de sus grupos, en orden."""
        pedidos = set(ids)
        grupos = {o.grupo for o in self.objetos if o.id in pedidos and o.grupo}
        return tuple(o.id for o in self.objetos if o.id in pedidos or o.grupo in grupos)

    def seleccionados(self, ids) -> tuple[Objeto, ...]:
        conjunto = set(ids)
        return tuple(o for o in self.objetos if o.id in conjunto)


def limites_de(objetos) -> tuple[int, int, int, int] | None:
    cajas = [o.limites() for o in objetos]
    if not cajas:
        return None
    return (min(c[0] for c in cajas), min(c[1] for c in cajas),
            max(c[2] for c in cajas), max(c[3] for c in cajas))
