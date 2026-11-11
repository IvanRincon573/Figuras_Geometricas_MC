"""Guía por filas y archivos JSON: deben usar exactamente los mismos bloques."""

from __future__ import annotations

import json

import pytest

from figuras_bloques.archivo import ErrorDeArchivo, a_diccionario, abrir, guardar
from figuras_bloques.geometria import Configuracion, generar
from figuras_bloques.guia import filas_guia, instrucciones, posicion_centro, resumen

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
    desde_guia = {
        (x - 1, r.fila - 1) for r in filas for a, b in r.tramos for x in range(a, b + 1)
    }
    assert desde_guia == f.conjunto
    texto = instrucciones(f)
    assert f"TOTAL: {f.total} bloques" in texto
    assert texto.count("\nFila ") == f.alto


@pytest.mark.parametrize("cfg", CONFIGS, ids=str)
def test_json_ida_y_vuelta(cfg, tmp_path):
    f = generar(cfg)
    ruta = tmp_path / "diseno.json"
    guardar(f, ruta)
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    assert datos == json.loads(json.dumps(a_diccionario(f)))
    assert datos["dimensiones"]["total_bloques"] == f.total == len(datos["bloques"])
    assert {(x - 1, y - 1) for x, y in datos["bloques"]} == f.conjunto
    assert sum(r["bloques"] for r in datos["filas"]) == f.total
    cargado = abrir(ruta)
    assert cargado.aviso is None
    assert cargado.figura.config == f.config
    assert cargado.figura.filas == f.filas


def test_json_bloques_alterados(tmp_path):
    f = generar(Configuracion("hexagono", 12, "plano", "contorno"))
    datos = a_diccionario(f)
    datos["bloques"].pop()
    ruta = tmp_path / "x.json"
    ruta.write_text(json.dumps(datos), encoding="utf-8")
    assert abrir(ruta).aviso is not None


@pytest.mark.parametrize(
    "contenido",
    [
        "no es json",
        "[]",
        '{"formato": "otro"}',
        '{"formato": "figuras-bloques", "version": 1}',
        '{"formato": "figuras-bloques", "version": 1, '
        '"configuracion": {"figura": "hexagono", "tamano": 0}}',
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
