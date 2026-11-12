"""Chunks de 16 × 16 bloques anclados al mundo.

El chunk (0, 0) contiene los bloques X = 0…15 y Z = 0…15. Las coordenadas de chunk se
obtienen con división entera hacia menos infinito, así que el bloque X = -1 pertenece al
chunk X = -1 y tiene coordenada local 15.
"""

from __future__ import annotations

from collections.abc import Iterator

TAMANO_CHUNK = 16


def chunk_de(x: int, z: int) -> tuple[int, int]:
    return x // TAMANO_CHUNK, z // TAMANO_CHUNK


def local_de(x: int, z: int) -> tuple[int, int]:
    return x % TAMANO_CHUNK, z % TAMANO_CHUNK


def limites_chunk(cx: int, cz: int) -> tuple[int, int, int, int]:
    """(x0, z0, x1, z1) inclusivos del chunk."""
    x0, z0 = cx * TAMANO_CHUNK, cz * TAMANO_CHUNK
    return x0, z0, x0 + TAMANO_CHUNK - 1, z0 + TAMANO_CHUNK - 1


def repartir(x0: int, x1: int) -> Iterator[tuple[int, int, int]]:
    """Divide el tramo [x0, x1] en trozos (chunk_x, inicio, fin) que no cruzan chunks."""
    inicio = x0
    while inicio <= x1:
        cx = inicio // TAMANO_CHUNK
        fin = min(x1, (cx + 1) * TAMANO_CHUNK - 1)
        yield cx, inicio, fin
        inicio = fin + 1
