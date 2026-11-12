"""Resultado final de un diseño: el único conjunto de bloques que se dibuja, cuenta y exporta.

Reglas:
* Solo cuentan los objetos visibles; los bloqueados cuentan igual que los demás.
* Un bloque compartido por varias figuras ocupa una sola posición y cuenta una vez.
* Su color es el del objeto que está más arriba en el orden de apilado (el último de la lista).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from functools import cached_property

from .chunks import chunk_de, limites_chunk, local_de, repartir
from .documento import Objeto

Tramo = tuple[int, int, str]


def pintar(tramos: list[Tramo], x0: int, x1: int, color: str) -> list[Tramo]:
    """Superpone [x0, x1] con ``color`` sobre los tramos existentes de una fila."""
    resultado: list[Tramo] = []
    for a, b, c in tramos:
        if b < x0 or a > x1:
            resultado.append((a, b, c))
            continue
        if a < x0:
            resultado.append((a, x0 - 1, c))
        if b > x1:
            resultado.append((x1 + 1, b, c))
    resultado.append((x0, x1, color))
    resultado.sort()
    return _fusionar_contiguos(resultado)


def _fusionar_contiguos(tramos: list[Tramo]) -> list[Tramo]:
    resultado: list[Tramo] = []
    for a, b, c in tramos:
        if resultado and resultado[-1][2] == c and resultado[-1][1] + 1 == a:
            resultado[-1] = (resultado[-1][0], b, c)
        else:
            resultado.append((a, b, c))
    return resultado


@dataclass(frozen=True)
class Construccion:
    filas: dict[int, tuple[Tramo, ...]]

    @cached_property
    def total(self) -> int:
        return sum(b - a + 1 for tramos in self.filas.values() for a, b, _ in tramos)

    @property
    def vacia(self) -> bool:
        return not self.filas

    @cached_property
    def limites(self) -> tuple[int, int, int, int] | None:
        if not self.filas:
            return None
        return (min(t[0][0] for t in self.filas.values()), min(self.filas),
                max(t[-1][1] for t in self.filas.values()), max(self.filas))

    @property
    def ancho(self) -> int:
        return 0 if self.limites is None else self.limites[2] - self.limites[0] + 1

    @property
    def largo(self) -> int:
        return 0 if self.limites is None else self.limites[3] - self.limites[1] + 1

    @cached_property
    def por_chunk(self) -> dict[tuple[int, int], int]:
        cuenta: Counter = Counter()
        for z, tramos in self.filas.items():
            cz = chunk_de(0, z)[1]
            for a, b, _ in tramos:
                for cx, inicio, fin in repartir(a, b):
                    cuenta[(cx, cz)] += fin - inicio + 1
        return dict(sorted(cuenta.items(), key=lambda k: (k[0][1], k[0][0])))

    @cached_property
    def por_color(self) -> dict[str, int]:
        cuenta: Counter = Counter()
        for tramos in self.filas.values():
            for a, b, c in tramos:
                cuenta[c] += b - a + 1
        return dict(cuenta.most_common())

    def color_en(self, x: int, z: int) -> str | None:
        return next((c for a, b, c in self.filas.get(z, ()) if a <= x <= b), None)

    def celdas(self) -> Iterator[tuple[int, int, str]]:
        for z in sorted(self.filas):
            for a, b, c in self.filas[z]:
                for x in range(a, b + 1):
                    yield x, z, c

    def recortar(self, x0: int, z0: int, x1: int, z1: int) -> Construccion:
        filas = {}
        for z, tramos in self.filas.items():
            if z0 <= z <= z1:
                dentro = tuple((max(a, x0), min(b, x1), c) for a, b, c in tramos if b >= x0 and a <= x1)
                if dentro:
                    filas[z] = dentro
        return Construccion(filas)


def construir(objetos: Iterable[Objeto]) -> Construccion:
    filas: dict[int, list[Tramo]] = {}
    for objeto in objetos:
        if not objeto.visible:
            continue
        forma = objeto.forma()
        for dz, fila in enumerate(forma.filas):
            if not fila:
                continue
            z = objeto.z + dz
            tramos = filas.get(z, [])
            for a, b in fila:
                tramos = pintar(tramos, objeto.x + a, objeto.x + b, objeto.color)
            filas[z] = tramos
    return Construccion({z: tuple(t) for z, t in sorted(filas.items()) if t})


@dataclass(frozen=True)
class FilaGuia:
    z: int
    bloques: int
    tramos: tuple[Tramo, ...]


def filas_guia(c: Construccion) -> list[FilaGuia]:
    return [FilaGuia(z, sum(b - a + 1 for a, b, _ in t), t) for z, t in sorted(c.filas.items())]


def texto_tramos(tramos: tuple[Tramo, ...], con_color: bool, local: bool = False) -> str:
    partes = []
    for a, b, color in tramos:
        if local:
            a, b = local_de(a, 0)[0], local_de(b, 0)[0]
        texto = f"{a}" if a == b else f"{a}–{b}"
        partes.append(f"{texto} [{color}]" if con_color else texto)
    return ", ".join(partes)


def resumen(c: Construccion) -> dict[str, str]:
    if c.vacia:
        return {"Bloques únicos": "0"}
    x0, z0, x1, z1 = c.limites
    return {
        "Bloques únicos": f"{c.total}",
        "Dimensiones": f"{c.ancho} × {c.largo} bloques (X × Z)",
        "Extensión X": f"{x0} … {x1}",
        "Extensión Z": f"{z0} … {z1}",
        "Chunks ocupados": f"{len(c.por_chunk)}",
    }


def _cabecera(c: Construccion, titulo: str) -> list[str]:
    lineas = [titulo, ""]
    lineas += [f"{k}: {v}" for k, v in resumen(c).items()]
    if len(c.por_color) > 1:
        lineas.append("Bloques por color: " + ", ".join(f"{col} × {n}" for col, n in c.por_color.items()))
    lineas += [
        "",
        "Coordenadas globales: X hacia el este, Z hacia el sur. Los tramos incluyen ambos extremos.",
        "Chunk (0, 0) = bloques X 0…15, Z 0…15.",
        "",
    ]
    return lineas


def instrucciones(c: Construccion, titulo: str = "Instrucciones de construcción") -> str:
    con_color = len(c.por_color) > 1
    lineas = _cabecera(c, titulo)
    for fila in filas_guia(c):
        plural = "bloque" if fila.bloques == 1 else "bloques"
        lineas.append(f"Z {fila.z}: {fila.bloques} {plural} — X {texto_tramos(fila.tramos, con_color)}")
    lineas += ["", f"TOTAL: {c.total} bloques únicos"]
    return "\n".join(lineas)


def instrucciones_por_chunk(c: Construccion, titulo: str = "Instrucciones por chunk") -> str:
    con_color = len(c.por_color) > 1
    lineas = _cabecera(c, titulo)
    for (cx, cz), cantidad in c.por_chunk.items():
        x0, z0, x1, z1 = limites_chunk(cx, cz)
        lineas.append(f"=== Chunk ({cx}, {cz}) — X {x0}…{x1}, Z {z0}…{z1} — {cantidad} bloques ===")
        for fila in filas_guia(c.recortar(x0, z0, x1, z1)):
            local_z = local_de(0, fila.z)[1]
            lineas.append(
                f"Z {fila.z} (local {local_z}): {fila.bloques} — X {texto_tramos(fila.tramos, con_color)}"
                f" (local {texto_tramos(fila.tramos, False, local=True)})"
            )
        lineas.append("")
    lineas.append(f"TOTAL: {c.total} bloques únicos en {len(c.por_chunk)} chunks")
    return "\n".join(lineas)


def describir_posicion(x: int, z: int) -> str:
    cx, cz = chunk_de(x, z)
    lx, lz = local_de(x, z)
    return f"X {x} · Z {z} · chunk ({cx}, {cz}) · local ({lx}, {lz})"

