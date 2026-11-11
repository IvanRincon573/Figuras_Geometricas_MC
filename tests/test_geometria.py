"""Pruebas de la lógica geométrica (sin interfaz)."""

from __future__ import annotations

import math

import pytest

from figuras_bloques.geometria import (
    RAIZ3,
    TAMANO_MAXIMO,
    Configuracion,
    ErrorDeTamano,
    Figura,
    generar,
)

HEX_TAMANOS = list(range(1, 81)) + [99, 100, 127, 128, 255, 256, 499, 500, 999, 1000]
ORIENT_HEX = ("plano", "vertice")
MODOS = ("contorno", "relleno")


def hexagono(w: int, orient: str, modo: str = "relleno") -> Figura:
    return generar(Configuracion("hexagono", w, orient, modo))


def vecinos4(x, y):
    return ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))


def vecinos8(x, y):
    return [(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy]


def componentes8(celdas: set) -> int:
    pendientes = set(celdas)
    n = 0
    while pendientes:
        n += 1
        pila = [pendientes.pop()]
        while pila:
            c = pila.pop()
            for v in vecinos8(*c):
                if v in pendientes:
                    pendientes.remove(v)
                    pila.append(v)
    return n


def caja(celdas) -> tuple[int, int, int, int]:
    xs = [x for x, _ in celdas]
    ys = [y for _, y in celdas]
    return min(xs), max(xs), min(ys), max(ys)


def comprobar_basico(f: Figura) -> None:
    """Propiedades comunes a cualquier figura."""
    celdas = f.celdas
    assert len(celdas) == len(set(celdas)) == f.total
    assert sum(f.bloques_por_fila()) == f.total
    assert len(f.filas) == f.alto
    assert all(isinstance(x, int) and isinstance(y, int) for x, y in celdas)
    assert caja(celdas) == (0, f.ancho - 1, 0, f.alto - 1)
    for fila in f.filas:
        for (a0, a1), (b0, b1) in zip(fila, fila[1:]):
            assert a0 <= a1 < b0 - 1 < b1
    assert generar(f.config).filas == f.filas


@pytest.mark.parametrize("orient", ORIENT_HEX)
@pytest.mark.parametrize("w", HEX_TAMANOS)
def test_hexagono_dimensiones(w, orient):
    f = hexagono(w, orient)
    comprobar_basico(f)
    assert f.ancho == w, "el ancho en bloques debe ser exactamente el pedido"
    teorico = w * RAIZ3 / 2 if orient == "plano" else 2 * w / RAIZ3
    assert f.alto_teorico == pytest.approx(teorico)
    assert abs(f.alto - teorico) <= 0.6, (f.alto, teorico)


@pytest.mark.parametrize("modo", MODOS)
@pytest.mark.parametrize("orient", ORIENT_HEX)
@pytest.mark.parametrize("w", HEX_TAMANOS)
def test_hexagono_simetrias(w, orient, modo):
    f = hexagono(w, orient, modo)
    s = f.conjunto
    espejo_h = {(f.ancho - 1 - x, y) for x, y in s}
    espejo_v = {(x, f.alto - 1 - y) for x, y in s}
    assert espejo_h == s, "simetría izquierda-derecha"
    assert espejo_v == s, "simetría arriba-abajo"
    assert f.centro == (f.ancho / 2, f.alto / 2)


@pytest.mark.parametrize("orient", ORIENT_HEX)
@pytest.mark.parametrize("w", HEX_TAMANOS)
def test_hexagono_forma(w, orient):
    """Convexidad, lados rectos y bordes inclinados sin saltos."""
    f = hexagono(w, orient)
    assert all(len(fila) == 1 for fila in f.filas), "cada fila del relleno es un único tramo"
    anchos = f.bloques_por_fila()
    mitad = (f.alto - 1) // 2
    assert all(a <= b for a, b in zip(anchos[: mitad + 1], anchos[1 : mitad + 1]))
    assert anchos == anchos[::-1]
    x0 = [fila[0][0] for fila in f.filas]
    saltos = [abs(a - b) for a, b in zip(x0, x0[1:])]
    if orient == "plano":
        # pendiente teórica 1/√3 ≈ 0,58 bloques por fila
        assert max(saltos, default=0) <= 1
        assert anchos[0] % 2 == w % 2
        if w >= 8:
            assert abs(anchos[0] - w / 2) <= 1.5, "el lado superior mide ≈ la mitad del ancho"
    else:
        # pendiente teórica √3 ≈ 1,73 bloques por fila
        assert max(saltos, default=0) <= 2
        llenas = [i for i, a in enumerate(anchos) if a == w]
        assert llenas == list(range(llenas[0], llenas[-1] + 1))
        assert llenas[0] == f.alto - 1 - llenas[-1]
        # Una fila es "completa" si el centro de su bloque extremo cae dentro del
        # hexágono: eso alarga el tramo hasta 2·0,5/√3 ≈ 0,58 bloques, más 1 por
        # el redondeo a filas enteras.
        assert abs(len(llenas) - w / RAIZ3) <= 1 + 1 / RAIZ3 + 1e-9, "lado vertical ≈ ancho/√3"


@pytest.mark.parametrize("orient", ORIENT_HEX)
@pytest.mark.parametrize("w", HEX_TAMANOS)
def test_hexagono_pendiente_real(w, orient):
    """Cada borde inclinado sigue la recta del hexágono regular a menos de 1 bloque."""
    f = hexagono(w, orient)
    cx, cy = f.centro
    radio = w / 2 if orient == "plano" else w / RAIZ3
    for y, ((x0, x1),) in enumerate(f.filas):
        dy = abs(y + 0.5 - cy)
        if orient == "plano":
            semiancho = radio - dy / RAIZ3
        else:
            semiancho = w / 2 if dy <= radio / 2 else (radio - dy) * RAIZ3
        borde_izq = cx - semiancho
        assert abs((x0 + 0.5) - max(borde_izq, 0)) <= 1.0 + 1e-9


def _contorno_fuerza_bruta(relleno: set) -> set:
    return {c for c in relleno if any(v not in relleno for v in vecinos4(*c))}


@pytest.mark.parametrize("orient", ORIENT_HEX)
@pytest.mark.parametrize("w", list(range(1, 61)) + [101, 256, 333])
def test_hexagono_contorno(w, orient):
    rel = hexagono(w, orient, "relleno")
    con = hexagono(w, orient, "contorno")
    comprobar_basico(con)
    R, C = rel.conjunto, con.conjunto
    assert (con.ancho, con.alto) == (rel.ancho, rel.alto)
    assert C <= R
    assert C == _contorno_fuerza_bruta(R)
    interior = R - C
    assert all(v in R for c in interior for v in vecinos4(*c))
    assert componentes8(C) == 1, "el contorno debe ser una sola pieza"
    if w > 2:
        assert not any(
            (x + 1, y) in C and (x, y + 1) in C and (x + 1, y + 1) in C for x, y in C
        )
    assert {(con.ancho - 1 - x, y) for x, y in C} == C
    assert {(x, con.alto - 1 - y) for x, y in C} == C


@pytest.mark.parametrize("orient", ORIENT_HEX)
def test_hexagono_centro_par_impar(orient):
    assert hexagono(21, orient).centro[0] == 10.5
    assert hexagono(20, orient).centro[0] == 10.0
    for w in range(1, 200):
        f = hexagono(w, orient)
        assert f.centro[1] == f.alto / 2


def test_hexagono_casos_conocidos():
    """Casos revisados a mano (útiles para detectar cambios accidentales)."""
    plano10 = hexagono(10, "plano")
    assert plano10.bloques_por_fila() == [6, 6, 8, 8, 10, 8, 8, 6, 6]
    assert hexagono(10, "plano", "contorno").total == 26
    vert10 = hexagono(10, "vertice")
    assert vert10.bloques_por_fila() == [2, 6, 10, 10, 10, 10, 10, 10, 10, 6, 2]
    vert11 = hexagono(11, "vertice")
    assert vert11.bloques_por_fila()[:4] == [1, 5, 9, 11]
    assert vert11.alto == 13


@pytest.mark.parametrize("modo", MODOS)
@pytest.mark.parametrize("d", list(range(1, 70)) + [128, 255, 500, 1000])
def test_circulo(d, modo):
    f = generar(Configuracion("circulo", d, "", modo))
    comprobar_basico(f)
    assert f.ancho == f.alto == d
    s = f.conjunto
    assert {(d - 1 - x, y) for x, y in s} == s
    assert {(x, d - 1 - y) for x, y in s} == s
    assert {(y, x) for x, y in s} == s, "simetría diagonal (giro de 90°)"
    if modo == "contorno" and d > 1:
        assert componentes8(s) == 1
        if d > 2:
            assert not any((x + 1, y) in s and (x, y + 1) in s and (x + 1, y + 1) in s for x, y in s)


def test_circulo_criterio_centro():
    d = 31
    f = generar(Configuracion("circulo", d, "", "relleno"))
    r = d / 2
    for y in range(d):
        for x in range(d):
            dentro = (x + 0.5 - r) ** 2 + (y + 0.5 - r) ** 2 <= r * r + 1e-9
            assert f.contiene(x, y) == dentro


@pytest.mark.parametrize("modo", MODOS)
@pytest.mark.parametrize("orient", ("arriba", "abajo", "izquierda", "derecha"))
@pytest.mark.parametrize("b", list(range(1, 60)) + [127, 128, 500, 1000])
def test_triangulo(b, orient, modo):
    f = generar(Configuracion("triangulo", b, orient, modo))
    comprobar_basico(f)
    s = f.conjunto
    altura = b * RAIZ3 / 2
    if orient in ("arriba", "abajo"):
        assert f.ancho == b
        assert abs(f.alto - altura) < 1
        assert {(f.ancho - 1 - x, y) for x, y in s} == s
    else:
        assert f.alto == b
        assert abs(f.ancho - altura) < 1
        assert {(x, f.alto - 1 - y) for x, y in s} == s
    if modo == "contorno" and b > 2:
        assert componentes8(s) == 1


@pytest.mark.parametrize("b", range(1, 80))
def test_triangulo_orientaciones_equivalentes(b):
    arriba = generar(Configuracion("triangulo", b, "arriba", "relleno"))
    abajo = generar(Configuracion("triangulo", b, "abajo", "relleno"))
    izq = generar(Configuracion("triangulo", b, "izquierda", "relleno"))
    der = generar(Configuracion("triangulo", b, "derecha", "relleno"))
    assert arriba.total == abajo.total == izq.total == der.total
    assert {(x, arriba.alto - 1 - y) for x, y in arriba.conjunto} == abajo.conjunto
    assert {(y, x) for x, y in arriba.conjunto} == izq.conjunto
    assert {(izq.ancho - 1 - x, y) for x, y in izq.conjunto} == der.conjunto
    assert arriba.bloques_por_fila()[-1] == b


@pytest.mark.parametrize("tamano", [0, -5, TAMANO_MAXIMO + 1, 99999])
@pytest.mark.parametrize("figura", ["circulo", "triangulo", "hexagono"])
def test_tamano_fuera_de_rango(figura, tamano):
    from figuras_bloques.geometria import ORIENTACION_POR_DEFECTO

    with pytest.raises(ErrorDeTamano) as e:
        generar(Configuracion(figura, tamano, ORIENTACION_POR_DEFECTO[figura]))
    assert "entre 1 y" in str(e.value)


def test_parametros_no_validos():
    with pytest.raises(ErrorDeTamano):
        generar(Configuracion("hexagono", 10, "arriba"))
    with pytest.raises(ErrorDeTamano):
        generar(Configuracion("pentagono", 10, ""))
    with pytest.raises(ErrorDeTamano):
        generar(Configuracion("hexagono", 10, "plano", "hueco"))
    with pytest.raises(ErrorDeTamano):
        generar(Configuracion("hexagono", 10.5, "plano"))  # type: ignore[arg-type]
    with pytest.raises(ErrorDeTamano):
        generar(Configuracion("hexagono", 10, "plano", color="verde"))
    assert generar(Configuracion("hexagono", 10, "plano", color="#abc")).config.color == "#AABBCC"


def test_rendimiento_figura_maxima():
    import time

    t = time.perf_counter()
    for orient in ORIENT_HEX:
        for modo in MODOS:
            hexagono(TAMANO_MAXIMO, orient, modo)
    assert time.perf_counter() - t < 2.0
    assert math.isclose(hexagono(1000, "plano").total, 0.6495 * 1000 * 1000, rel_tol=0.01)
