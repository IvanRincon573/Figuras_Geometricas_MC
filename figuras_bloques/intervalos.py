"""Operaciones sobre filas de bloques expresadas como intervalos enteros inclusivos.

Una fila es una tupla ordenada de intervalos ``(x0, x1)`` disjuntos y no adyacentes,
de modo que cada conjunto de bloques tiene una única representación.
"""

from __future__ import annotations

from collections.abc import Iterable

Intervalo = tuple[int, int]
Fila = tuple[Intervalo, ...]


def normalizar(intervalos: Iterable[Intervalo]) -> Fila:
    resultado: list[list[int]] = []
    for a, b in sorted(intervalos):
        if resultado and a <= resultado[-1][1] + 1:
            resultado[-1][1] = max(resultado[-1][1], b)
        else:
            resultado.append([a, b])
    return tuple((a, b) for a, b in resultado)


def unir(*filas: Iterable[Intervalo]) -> Fila:
    return normalizar(i for fila in filas for i in fila)


def interseccion(a: Fila, b: Fila) -> Fila:
    resultado = []
    i = j = 0
    while i < len(a) and j < len(b):
        inicio = max(a[i][0], b[j][0])
        fin = min(a[i][1], b[j][1])
        if inicio <= fin:
            resultado.append((inicio, fin))
        if a[i][1] < b[j][1]:
            i += 1
        else:
            j += 1
    return tuple(resultado)


def restar(a: Fila, b: Fila) -> Fila:
    resultado = []
    for x0, x1 in a:
        inicio = x0
        for y0, y1 in b:
            if y1 < inicio or y0 > x1:
                continue
            if y0 > inicio:
                resultado.append((inicio, y0 - 1))
            inicio = max(inicio, y1 + 1)
            if inicio > x1:
                break
        if inicio <= x1:
            resultado.append((inicio, x1))
    return tuple(resultado)


def erosionar(fila: Fila) -> Fila:
    """Bloques cuyos dos vecinos horizontales también están en la fila."""
    return tuple((a + 1, b - 1) for a, b in fila if a + 1 <= b - 1)


def desplazar(fila: Fila, dx: int) -> Fila:
    return tuple((a + dx, b + dx) for a, b in fila)


def longitud(fila: Iterable[Intervalo]) -> int:
    return sum(b - a + 1 for a, b in fila)


def contorno(filas: tuple[Fila, ...]) -> tuple[Fila, ...]:
    """Bloques del área con algún vecino ortogonal fuera de ella (los huecos también son exterior)."""
    vacia: Fila = ()
    resultado = []
    for z, fila in enumerate(filas):
        arriba = filas[z - 1] if z > 0 else vacia
        abajo = filas[z + 1] if z + 1 < len(filas) else vacia
        interior = interseccion(interseccion(erosionar(fila), arriba), abajo)
        resultado.append(restar(fila, interior))
    return tuple(resultado)
