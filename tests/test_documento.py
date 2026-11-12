"""Chunks, documento con varias figuras, fusiones, operaciones y deshacer/rehacer."""

from __future__ import annotations

import random

import pytest

from figuras_bloques import intervalos as iv
from figuras_bloques.chunks import chunk_de, limites_chunk, local_de, repartir
from figuras_bloques.construccion import (
    construir,
    filas_guia,
    instrucciones,
    instrucciones_por_chunk,
    pintar,
)
from figuras_bloques.documento import FUSION_BLOQUES, FUSION_SILUETA, Documento, Objeto
from figuras_bloques.geometria import generar
from figuras_bloques.historial import Historial
from figuras_bloques import operaciones as op


def hexagono(id_, x, z, tamano=21, **extra):
    return Objeto(id_, f"Hexágono {id_}", "hexagono", x=x, z=z, tamano=tamano, **extra)


def celdas(objetos) -> set[tuple[int, int]]:
    return {(x, z) for x, z, _ in construir(objetos).celdas()}


def celdas_de(objeto: Objeto, superficie=False) -> set[tuple[int, int]]:
    forma = objeto.forma()
    filas = forma.superficie if superficie else forma.filas
    return {(objeto.x + x, objeto.z + dz) for dz, fila in enumerate(filas) for a, b in fila for x in range(a, b + 1)}


def vecinos4(x, z):
    return ((x + 1, z), (x - 1, z), (x, z + 1), (x, z - 1))


# ------------------------------------------------------------------ chunks
@pytest.mark.parametrize("x, chunk, local", [
    (0, 0, 0), (15, 0, 15), (16, 1, 0), (31, 1, 15), (32, 2, 0),
    (-1, -1, 15), (-16, -1, 0), (-17, -2, 15), (-32, -2, 0), (-33, -3, 15),
])
def test_chunk_y_local(x, chunk, local):
    assert chunk_de(x, x) == (chunk, chunk)
    assert local_de(x, x) == (local, local)
    x0, z0, x1, z1 = limites_chunk(chunk, chunk)
    assert x0 <= x <= x1 and z0 <= x <= z1 and x1 - x0 == 15


def test_chunk_origen():
    assert limites_chunk(0, 0) == (0, 0, 15, 15)
    assert limites_chunk(-1, -1) == (-16, -16, -1, -1)


def test_repartir_tramos():
    assert list(repartir(14, 17)) == [(0, 14, 15), (1, 16, 17)]
    assert list(repartir(-2, 1)) == [(-1, -2, -1), (0, 0, 1)]
    assert list(repartir(-40, 40)) == [(-3, -40, -33), (-2, -32, -17), (-1, -16, -1), (0, 0, 15),
                                       (1, 16, 31), (2, 32, 40)]
    for _ in range(200):
        a = random.randint(-100, 100)
        b = a + random.randint(0, 80)
        trozos = list(repartir(a, b))
        assert sum(f - i + 1 for _, i, f in trozos) == b - a + 1
        assert all(chunk_de(i, 0)[0] == cx == chunk_de(f, 0)[0] for cx, i, f in trozos)


def test_figura_que_atraviesa_varios_chunks():
    objeto = hexagono("o1", -30, -25, tamano=101, modo="relleno")
    c = construir([objeto])
    esperado = {}
    for x, z in celdas_de(objeto):
        esperado[chunk_de(x, z)] = esperado.get(chunk_de(x, z), 0) + 1
    assert c.por_chunk == esperado
    assert sum(c.por_chunk.values()) == c.total == generar(objeto.configuracion()).total
    assert len(c.por_chunk) > 20
    assert chunk_de(-30, 18) == (-2, 1) and (-2, 1) in c.por_chunk
    assert chunk_de(70, 18) == (4, 1) and (4, 1) in c.por_chunk


# ------------------------------------------------------------------ intervalos
def test_intervalos_basicos():
    assert iv.normalizar([(5, 7), (1, 2), (3, 3), (10, 12)]) == ((1, 3), (5, 7), (10, 12))
    assert iv.interseccion(((0, 10),), ((3, 4), (8, 20))) == ((3, 4), (8, 10))
    assert iv.restar(((0, 10),), ((3, 4), (8, 20))) == ((0, 2), (5, 7))
    assert iv.erosionar(((0, 0), (2, 3), (5, 9))) == ((6, 8),)


def test_intervalos_aleatorios():
    rng = random.Random(7)
    for _ in range(300):
        a = {rng.randint(-20, 20) for _ in range(rng.randint(0, 25))}
        b = {rng.randint(-20, 20) for _ in range(rng.randint(0, 25))}
        fa, fb = iv.normalizar((x, x) for x in a), iv.normalizar((x, x) for x in b)
        expandir = lambda f: {x for i, j in f for x in range(i, j + 1)}  # noqa: E731
        assert expandir(iv.unir(fa, fb)) == a | b
        assert expandir(iv.interseccion(fa, fb)) == a & b
        assert expandir(iv.restar(fa, fb)) == a - b


# ------------------------------------------------------------------ construcción
def test_solapamiento_sin_doble_conteo():
    a = hexagono("o1", 0, 0, modo="relleno", color="#111111")
    b = hexagono("o2", 10, 4, modo="relleno", color="#222222")
    c = construir([a, b])
    union = celdas_de(a) | celdas_de(b)
    assert c.total == len(union) < a.forma().total + b.forma().total
    assert {(x, z) for x, z, _ in c.celdas()} == union
    lista = list(c.celdas())
    assert len(lista) == len({(x, z) for x, z, _ in lista})


def test_color_del_objeto_superior():
    a = hexagono("o1", 0, 0, modo="relleno", color="#111111")
    b = hexagono("o2", 10, 4, modo="relleno", color="#222222")
    compartidas = celdas_de(a) & celdas_de(b)
    assert compartidas
    for orden, color in (([a, b], "#222222"), ([b, a], "#111111")):
        c = construir(orden)
        assert all(c.color_en(x, z) == color for x, z in compartidas)
    assert sum(construir([a, b]).por_color.values()) == construir([a, b]).total


def test_pintar_aleatorio_equivale_a_diccionario():
    rng = random.Random(3)
    for _ in range(200):
        tramos, referencia = [], {}
        for color in "abcdef":
            x0 = rng.randint(-10, 30)
            x1 = x0 + rng.randint(0, 12)
            tramos = pintar(tramos, x0, x1, color)
            referencia.update({x: color for x in range(x0, x1 + 1)})
        assert {x: c for a, b, c in tramos for x in range(a, b + 1)} == referencia
        assert all(t[1] < u[0] for t, u in zip(tramos, tramos[1:]))


def test_ocultos_excluidos_y_bloqueados_incluidos():
    visible = hexagono("o1", 0, 0)
    oculto = hexagono("o2", 50, 0, visible=False)
    bloqueado = hexagono("o3", 100, 0, bloqueado=True)
    assert celdas([visible, oculto, bloqueado]) == celdas_de(visible) | celdas_de(bloqueado)


def test_guia_global_coincide():
    doc = Documento((hexagono("o1", -12, -7, modo="relleno"), hexagono("o2", 3, -7, tamano=10)))
    c = construir(doc.objetos)
    filas = filas_guia(c)
    assert sum(f.bloques for f in filas) == c.total
    assert {(x, f.z) for f in filas for a, b, _ in f.tramos for x in range(a, b + 1)} == celdas(doc.objetos)
    texto = instrucciones(c)
    assert f"TOTAL: {c.total} bloques únicos" in texto and "Z -7:" in texto
    por_chunk = instrucciones_por_chunk(c)
    for (cx, cz), n in c.por_chunk.items():
        assert f"=== Chunk ({cx}, {cz})" in por_chunk and f"— {n} bloques ===" in por_chunk


# ------------------------------------------------------------------ fusión
def test_fusion_silueta_sin_lineas_internas():
    a, b = hexagono("o1", 0, 0), hexagono("o2", 12, 0)
    doc, id_c = op.fusionar(Documento((a, b)), ["o1", "o2"], FUSION_SILUETA, "contorno")
    compuesta = doc.buscar(id_c)
    area = celdas_de(a, True) | celdas_de(b, True)
    borde = {c for c in area if any(v not in area for v in vecinos4(*c))}
    assert celdas_de(compuesta) == borde
    internas = (celdas_de(a) | celdas_de(b)) - borde
    assert internas, "los contornos originales se cruzaban dentro de la unión"
    assert not internas & celdas_de(compuesta)


def test_fusion_silueta_relleno_es_union_de_areas():
    a, b = hexagono("o1", 0, 0), Objeto("o2", "c", "circulo", x=15, z=3, tamano=13)
    doc, id_c = op.fusionar(Documento((a, b)), ["o1", "o2"], FUSION_SILUETA, "relleno")
    assert celdas_de(doc.buscar(id_c)) == celdas_de(a, True) | celdas_de(b, True)


def test_fusion_bloques_conserva_celdas():
    a = hexagono("o1", 0, 0)
    b = Objeto("o2", "c", "circulo", x=8, z=2, tamano=15, modo="relleno")
    antes = celdas([a, b])
    doc, id_c = op.fusionar(Documento((a, b)), ["o1", "o2"], FUSION_BLOQUES)
    assert celdas_de(doc.buscar(id_c)) == antes == celdas(doc.objetos)


def test_fusion_figuras_separadas_no_crea_puentes():
    a, b = hexagono("o1", 0, 0, tamano=11), hexagono("o2", 40, 30, tamano=11)
    for fusion in (FUSION_BLOQUES, FUSION_SILUETA):
        doc, id_c = op.fusionar(Documento((a, b)), ["o1", "o2"], fusion, "contorno")
        assert celdas_de(doc.buscar(id_c)) == celdas_de(a) | celdas_de(b)


def _huecos(area: set) -> set:
    """Celdas vacías que no se pueden alcanzar desde el exterior."""
    xs, zs = [x for x, _ in area], [z for _, z in area]
    x0, x1, z0, z1 = min(xs) - 1, max(xs) + 1, min(zs) - 1, max(zs) + 1
    fuera, pila = {(x0, z0)}, [(x0, z0)]
    while pila:
        for v in vecinos4(*pila.pop()):
            if x0 <= v[0] <= x1 and z0 <= v[1] <= z1 and v not in area and v not in fuera:
                fuera.add(v)
                pila.append(v)
    return {(x, z) for x in range(x0, x1 + 1) for z in range(z0, z1 + 1)} - area - fuera


def test_fusion_conserva_bordes_de_huecos():
    posiciones = [(0, 0), (7, 0), (14, 0), (0, 7), (14, 7), (0, 14), (7, 14), (14, 14)]
    piezas = [Objeto(f"o{i}", "h", "hexagono", x=x, z=z, tamano=9, modo="relleno")
              for i, (x, z) in enumerate(posiciones)]
    doc, id_c = op.fusionar(Documento(tuple(piezas)), [p.id for p in piezas], FUSION_SILUETA, "contorno")
    area = set().union(*(celdas_de(p, True) for p in piezas))
    huecos = _huecos(area)
    assert huecos, "el anillo de hexágonos encierra un hueco"
    resultado = celdas_de(doc.buscar(id_c))
    assert not huecos & resultado, "el hueco no se rellena"
    borde_hueco = {v for h in huecos for v in vecinos4(*h) if v in area}
    assert borde_hueco <= resultado, "el borde del hueco forma parte del contorno"
    assert resultado == {c for c in area if any(v not in area for v in vecinos4(*c))}
    relleno, id_r = op.fusionar(Documento(tuple(piezas)), [p.id for p in piezas], FUSION_SILUETA, "relleno")
    assert not huecos & celdas_de(relleno.buscar(id_r)), "el relleno tampoco tapa los huecos"


def test_silueta_de_una_figura_es_su_contorno():
    for tamano in (7, 10, 21, 40):
        a = hexagono("o1", 3, -5, tamano)
        doc, id_c = op.fusionar(Documento((a, hexagono("o2", 3, -5, tamano))), ["o1", "o2"], FUSION_SILUETA)
        assert celdas_de(doc.buscar(id_c)) == celdas_de(a)


def test_separar_restaura_origenes_movidos():
    a, b = hexagono("o1", 0, 0), hexagono("o2", 12, 0, color="#123456")
    doc, id_c = op.fusionar(Documento((a, b)), ["o1", "o2"], FUSION_SILUETA)
    doc = op.mover(doc, [id_c], 20, -7)
    doc, ids = op.separar(doc, id_c)
    restaurados = doc.seleccionados(ids)
    assert [(o.x, o.z) for o in restaurados] == [(20, -7), (32, -7)]
    assert restaurados[1].color == "#123456"
    assert celdas(doc.objetos) == celdas([a.mover(20, -7), b.mover(20, -7)])


def test_fusion_anidada():
    doc = Documento((hexagono("o1", 0, 0), hexagono("o2", 12, 0), hexagono("o3", 6, 10)))
    doc, c1 = op.fusionar(doc, ["o1", "o2"], FUSION_SILUETA)
    doc, c2 = op.fusionar(doc, [c1, "o3"], FUSION_SILUETA)
    area = set().union(*(celdas_de(hexagono(i, x, z), True) for i, x, z in (("a", 0, 0), ("b", 12, 0), ("c", 6, 10))))
    assert celdas_de(doc.buscar(c2)) == {c for c in area if any(v not in area for v in vecinos4(*c))}


def test_fusion_rechaza_bloqueadas_y_ocultas():
    doc = Documento((hexagono("o1", 0, 0, bloqueado=True), hexagono("o2", 5, 0), hexagono("o3", 9, 0, visible=False)))
    with pytest.raises(op.ErrorDeOperacion):
        op.fusionar(doc, ["o1", "o2"], FUSION_SILUETA)
    with pytest.raises(op.ErrorDeOperacion):
        op.fusionar(doc, ["o2", "o3"], FUSION_SILUETA)
    with pytest.raises(op.ErrorDeOperacion):
        op.fusionar(doc, ["o2"], FUSION_SILUETA)


# ------------------------------------------------------------------ operaciones
def test_agregar_ids_y_nombres_unicos():
    doc = Documento()
    for _ in range(3):
        doc, _ = op.agregar(doc, Objeto("", "", "hexagono"))
    assert [o.id for o in doc.objetos] == ["o1", "o2", "o3"]
    assert [o.nombre for o in doc.objetos] == ["Hexágono 1", "Hexágono 2", "Hexágono 3"]


def test_grupo_se_mueve_conservando_posiciones_relativas():
    doc = Documento((hexagono("o1", 0, 0), hexagono("o2", 17, 5), hexagono("o3", 40, 40)))
    doc, id_g = op.agrupar(doc, ["o1", "o2"])
    seleccion = doc.con_grupos(["o1"])
    assert seleccion == ("o1", "o2")
    antes = {o.id: (o.x, o.z) for o in doc.objetos}
    doc = op.mover(doc, seleccion, -16, 32)
    for o in doc.seleccionados(seleccion):
        assert (o.x, o.z) == (antes[o.id][0] - 16, antes[o.id][1] + 32)
    assert doc.buscar("o3").x == 40
    doc = op.desagrupar(doc, ["o1"])
    assert all(o.grupo is None for o in doc.objetos) and not doc.grupos
    assert [(o.x, o.z) for o in doc.objetos][:2] == [(-16, 32), (1, 37)]


def test_bloqueados_no_se_editan():
    doc = Documento((hexagono("o1", 0, 0, bloqueado=True), hexagono("o2", 5, 5)))
    assert op.mover(doc, ["o1", "o2"], 3, 3).buscar("o1").x == 0
    assert op.eliminar(doc, ["o1"]).buscar("o1") is not None
    with pytest.raises(op.ErrorDeOperacion):
        op.editar(doc, "o1", tamano=30)
    assert op.editar(doc, "o1", visible=False).buscar("o1").visible is False


def test_editar_valida_tamano():
    doc = Documento((hexagono("o1", 0, 0),))
    with pytest.raises(op.ErrorDeOperacion):
        op.editar(doc, "o1", tamano=0)
    assert op.editar(doc, "o1", tamano=40).buscar("o1").tamano == 40


def test_duplicar_grupo_completo():
    doc = Documento((hexagono("o1", 0, 0), hexagono("o2", 10, 0)))
    doc, id_g = op.agrupar(doc, ["o1", "o2"])
    doc, nuevos = op.duplicar(doc, ["o1", "o2"])
    copias = doc.seleccionados(nuevos)
    assert len(copias) == 2 and copias[0].grupo == copias[1].grupo != id_g
    assert [(o.x, o.z) for o in copias] == [(2, 2), (12, 2)]


def test_alinear_bordes_y_centros():
    doc = Documento((hexagono("o1", 0, 0, tamano=21), hexagono("o2", 30, 9, tamano=11)))
    izq = op.alinear(doc, ["o1", "o2"], "izquierda")
    assert izq.buscar("o2").limites()[0] == 0
    centro = op.alinear(doc, ["o1", "o2"], "centro_z")
    c1, c2 = centro.buscar("o1").limites(), centro.buscar("o2").limites()
    assert abs((c1[1] + c1[3]) - (c2[1] + c2[3])) <= 1
    abajo = op.alinear(doc, ["o1", "o2"], "abajo")
    assert abajo.buscar("o1").limites()[3] == abajo.buscar("o2").limites()[3]


def test_reordenar():
    doc = Documento((hexagono("a", 0, 0), hexagono("b", 0, 0), hexagono("c", 0, 0)))
    assert [o.id for o in op.reordenar(doc, ["a"], "frente").objetos] == ["b", "c", "a"]
    assert [o.id for o in op.reordenar(doc, ["c"], "fondo").objetos] == ["c", "a", "b"]
    assert [o.id for o in op.reordenar(doc, ["a"], "subir").objetos] == ["b", "a", "c"]
    assert [o.id for o in op.reordenar(doc, ["c"], "bajar").objetos] == ["a", "c", "b"]


@pytest.mark.parametrize("x, esperado", [(0, 0), (7, 0), (8, 16), (-8, 0), (-9, -16), (23, 16), (24, 32)])
def test_ajustar_a_chunk(x, esperado):
    assert op.ajustar_a_chunk(x, x) == (esperado, esperado)


# ------------------------------------------------------------------ historial
def test_deshacer_y_rehacer_todas_las_operaciones():
    h = Historial(Documento())
    pasos = []

    def paso(doc, descripcion):
        h.registrar(doc, descripcion)
        pasos.append(doc)
        return doc

    doc = paso(op.agregar(Documento(), hexagono("", 0, 0))[0], "añadir")
    doc = paso(op.agregar(doc, hexagono("", 30, 0))[0], "añadir")
    doc = paso(op.mover(doc, ["o1"], 5, 5), "mover")
    doc = paso(op.editar(doc, "o2", tamano=31), "editar")
    doc = paso(op.duplicar(doc, ["o2"])[0], "duplicar")
    doc = paso(op.agrupar(doc, ["o1", "o3"])[0], "agrupar")
    doc = paso(op.fusionar(doc, ["o1", "o2"], FUSION_SILUETA)[0], "fusionar")
    doc = paso(op.eliminar(doc, ["o3"]), "eliminar")
    for esperado in reversed([Documento()] + pasos[:-1]):
        assert h.deshacer() == esperado
    assert not h.puede_deshacer()
    for esperado in pasos:
        assert h.rehacer() == esperado
    assert not h.puede_rehacer()


def test_historial_fusiona_ediciones_consecutivas():
    h = Historial(Documento())
    doc = op.agregar(Documento(), hexagono("", 0, 0))[0]
    h.registrar(doc, "añadir")
    for tamano in (22, 23, 24):
        doc = op.editar(doc, "o1", tamano=tamano)
        h.registrar(doc, "tamaño", clave="o1:tamano")
    assert h.deshacer().buscar("o1").tamano == 21
    h.rehacer()
    h.registrar(op.mover(doc, ["o1"], 1, 0), "mover")
    h.deshacer()
    assert h.actual.buscar("o1").tamano == 24
