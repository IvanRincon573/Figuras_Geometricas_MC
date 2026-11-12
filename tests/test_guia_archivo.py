"""Guía de una figura y archivos JSON: deben usar exactamente los mismos bloques."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from figuras_bloques.archivo import ErrorDeArchivo, a_diccionario, a_diccionario_v1, abrir, guardar
from figuras_bloques.construccion import construir
from figuras_bloques.documento import COMPUESTA, FUSION_SILUETA, Documento, Objeto
from figuras_bloques.geometria import Configuracion, generar
from figuras_bloques.guia import filas_guia, instrucciones, posicion_centro, resumen
from figuras_bloques.operaciones import agrupar, fusionar

DATOS = Path(__file__).parent / "datos"

CONFIGS = [
    Configuracion("hexagono", w, o, m)
    for w in (1, 2, 7, 10, 11, 20, 21, 64, 65)
    for o in ("plano", "vertice")
    for m in ("contorno", "relleno")
] + [
    Configuracion("circulo", 31, "", "contorno"),
    Configuracion("circulo", 30, "", "relleno"),
    Configuracion("triangulo", 9, "izquierda", "contorno"),
    Configuracion("triangulo", 12, "abajo", "relleno"),
]


@pytest.mark.parametrize("cfg", CONFIGS, ids=str)
def test_guia_coincide_con_bloques(cfg):
    f = generar(cfg)
    filas = filas_guia(f)
    assert len(filas) == f.alto
    assert sum(r.bloques for r in filas) == f.total
    desde_guia = {(x - 1, r.fila - 1) for r in filas for a, b in r.tramos for x in range(a, b + 1)}
    assert desde_guia == f.conjunto
    texto = instrucciones(f)
    assert f"TOTAL: {f.total} bloques" in texto
    assert texto.count("\nFila ") == f.alto


def _diseno_compuesto() -> Documento:
    doc = Documento((
        Objeto("o1", "Hexágono 1", "hexagono", x=-20, z=-3, tamano=21),
        Objeto("o2", "Hexágono 2", "hexagono", x=-3, z=-3, tamano=21, color="#3F7FE0"),
        Objeto("o3", "Círculo 1", "circulo", x=30, z=10, tamano=15, modo="relleno", visible=False),
        Objeto("o4", "Triángulo 1", "triangulo", x=5, z=40, tamano=12, orientacion="abajo", bloqueado=True),
        Objeto("o5", "Círculo 2", "circulo", x=40, z=40, tamano=9),
    ))
    doc, _ = fusionar(doc, ["o1", "o2"], FUSION_SILUETA, "contorno", "Base")
    doc, _ = agrupar(doc, ["o4", "o5"], "Torres")
    return doc


@pytest.mark.parametrize("cfg", CONFIGS, ids=str)
def test_json_ida_y_vuelta_una_figura(cfg, tmp_path):
    doc = Documento((Objeto("o1", "Figura", cfg.figura, x=-7, z=13, tamano=cfg.tamano,
                            orientacion=cfg.orientacion, modo=cfg.modo),))
    ruta = tmp_path / "diseno.json"
    guardar(doc, ruta)
    cargado = abrir(ruta)
    assert cargado.aviso is None and cargado.version == 2
    assert cargado.documento == doc
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    assert datos["resultado"]["total_bloques"] == generar(cfg).total == len(datos["resultado"]["bloques"])


def test_json_diseno_compuesto(tmp_path):
    doc = _diseno_compuesto()
    ruta = tmp_path / "compuesto.json"
    guardar(doc, ruta)
    cargado = abrir(ruta)
    assert cargado.aviso is None
    assert cargado.documento == doc
    assert [o.id for o in cargado.documento.objetos] == [o.id for o in doc.objetos]
    compuesta = next(o for o in cargado.documento.objetos if o.tipo == COMPUESTA)
    assert [o.nombre for o in compuesta.origenes] == ["Hexágono 1", "Hexágono 2"]
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    c = construir(doc.objetos)
    assert datos["resultado"]["total_bloques"] == c.total
    assert {tuple(b) for b in datos["resultado"]["bloques"]} == set(c.celdas())
    assert sum(ch["bloques"] for ch in datos["resultado"]["chunks"]) == c.total
    assert datos == json.loads(json.dumps(a_diccionario(doc)))


def test_json_bloques_alterados(tmp_path):
    datos = a_diccionario(_diseno_compuesto())
    datos["resultado"]["bloques"].pop()
    ruta = tmp_path / "x.json"
    ruta.write_text(json.dumps(datos), encoding="utf-8")
    assert abrir(ruta).aviso is not None


@pytest.mark.parametrize("archivo", sorted(DATOS.glob("v1_*.json")), ids=lambda p: p.name)
def test_compatibilidad_version_1(archivo):
    """Archivos reales guardados con la versión anterior (una sola figura).

    Los hexágonos se dibujan ahora con escalones simétricos: el archivo se abre con
    la figura recalculada y un aviso; las demás figuras conservan sus bloques."""
    original = json.loads(archivo.read_text(encoding="utf-8"))
    cargado = abrir(archivo)
    cfg = original["configuracion"]
    hexagono = cfg["figura"] == "hexagono"
    assert cargado.version == 1
    assert (cargado.aviso is not None) == hexagono
    (objeto,) = cargado.documento.objetos
    assert (objeto.tipo, objeto.tamano, objeto.orientacion, objeto.modo, objeto.color) == (
        cfg["figura"], cfg["tamano"], cfg["orientacion"], cfg["modo"], cfg["color"])
    assert (objeto.x, objeto.z) == (0, 0)
    bloques = {(x, z) for x, z, _ in construir(cargado.documento.objetos).celdas()}
    esperados = generar(Configuracion(cfg["figura"], cfg["tamano"], cfg["orientacion"], cfg["modo"])).conjunto
    assert bloques == set(esperados)
    if not hexagono:
        assert bloques == {(x - 1, y - 1) for x, y in original["bloques"]}


def test_compatibilidad_version_1_alterada(tmp_path):
    datos = a_diccionario_v1(generar(Configuracion("hexagono", 12, "vertice", "relleno")))
    datos["bloques"].pop()
    ruta = tmp_path / "v1.json"
    ruta.write_text(json.dumps(datos), encoding="utf-8")
    assert abrir(ruta).aviso is not None


@pytest.mark.parametrize(
    "contenido",
    [
        "no es json",
        "[]",
        '{"formato": "otro"}',
        '{"formato": "figuras-bloques", "version": 1}',
        '{"formato": "figuras-bloques", "version": 1, "configuracion": {"figura": "hexagono", "tamano": 0}}',
        '{"formato": "figuras-bloques", "version": 2}',
        '{"formato": "figuras-bloques", "version": 2, "documento": {"objetos": [{"id": "o1"}]}}',
        '{"formato": "figuras-bloques", "version": 2, "documento": {"objetos": [{"id": "o1", "nombre": "a",'
        ' "tipo": "hexagono", "tamano": 5000}]}}',
        '{"formato": "figuras-bloques", "version": 2, "documento": {"objetos": [{"id": "o1", "nombre": "a",'
        ' "tipo": "compuesta", "fusion": "silueta", "origenes": []}]}}',
        '{"formato": "figuras-bloques", "version": 9}',
    ],
)
def test_json_no_valido(contenido, tmp_path):
    ruta = tmp_path / "malo.json"
    ruta.write_text(contenido, encoding="utf-8")
    with pytest.raises(ErrorDeArchivo):
        abrir(ruta)


def test_posicion_centro():
    assert posicion_centro(5.5, "columna") == "columna 6"
    assert posicion_centro(5.0, "columna") == "entre las columnas 5 y 6"
    assert posicion_centro(4.5, "fila") == "fila 5"
    assert posicion_centro(9.0, "fila") == "entre las filas 9 y 10"


def test_resumen_hexagono():
    r = resumen(generar(Configuracion("hexagono", 10, "plano", "contorno")))
    assert r["Total de bloques"] == "26"
    assert r["Centro"] == "fila 5, entre las columnas 5 y 6"
    assert r["Alto real"].startswith("9 bloques")
