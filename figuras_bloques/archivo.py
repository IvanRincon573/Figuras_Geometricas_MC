"""Guardar y abrir diseños en JSON."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .geometria import Configuracion, ErrorDeTamano, Figura, generar
from .guia import filas_guia

FORMATO = "figuras-bloques"
VERSION = 1
BLOQUES_POR_LINEA = 16
AVISO_BLOQUES_DISTINTOS = (
    "Los bloques guardados en el archivo no coinciden con los que genera esta "
    "versión del programa para la misma configuración. Se muestra la figura recalculada."
)


class ErrorDeArchivo(Exception):
    """Archivo ilegible o con un formato no reconocido."""


@dataclass
class DisenoCargado:
    figura: Figura
    aviso: str | None


def a_diccionario(figura: Figura) -> dict:
    cfg = figura.config
    return {
        "formato": FORMATO,
        "version": VERSION,
        "configuracion": {
            "figura": cfg.figura,
            "tamano": cfg.tamano,
            "orientacion": cfg.orientacion,
            "modo": cfg.modo,
            "color": cfg.color,
        },
        "coordenadas": (
            "Cada bloque es [x, y]: x = columna (1 = izquierda), "
            "y = fila (1 = arriba). Los tramos incluyen ambos extremos."
        ),
        "dimensiones": {
            "ancho": figura.ancho,
            "alto": figura.alto,
            "ancho_teorico": round(figura.ancho_teorico, 6),
            "alto_teorico": round(figura.alto_teorico, 6),
            "total_bloques": figura.total,
        },
        "centro": {
            "x": round(figura.centro[0] + 0.5, 6),
            "y": round(figura.centro[1] + 0.5, 6),
        },
        "filas": [
            {"fila": f.fila, "bloques": f.bloques, "tramos": [list(t) for t in f.tramos]}
            for f in filas_guia(figura)
        ],
        "bloques": [[x + 1, y + 1] for x, y in figura.celdas],
    }


def guardar(figura: Figura, ruta: str | Path) -> None:
    Path(ruta).write_text(_serializar(a_diccionario(figura)), encoding="utf-8")


def _serializar(datos: dict) -> str:
    """JSON indentado, con una fila por línea y los bloques agrupados para que ocupe poco."""
    cabecera = {k: v for k, v in datos.items() if k not in ("filas", "bloques")}
    cuerpo = json.dumps(cabecera, ensure_ascii=False, indent=2).removesuffix("\n}")
    filas = ",\n    ".join(json.dumps(f, ensure_ascii=False) for f in datos["filas"])
    bloques = datos["bloques"]
    grupos = ",\n    ".join(
        ", ".join(json.dumps(b) for b in bloques[i : i + BLOQUES_POR_LINEA])
        for i in range(0, len(bloques), BLOQUES_POR_LINEA)
    )
    return f'{cuerpo},\n  "filas": [\n    {filas}\n  ],\n  "bloques": [\n    {grupos}\n  ]\n}}\n'


def abrir(ruta: str | Path) -> DisenoCargado:
    return desde_diccionario(_leer_json(Path(ruta)))


def _leer_json(ruta: Path) -> object:
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ErrorDeArchivo("No se encuentra el archivo.") from None
    except (OSError, UnicodeDecodeError) as e:
        raise ErrorDeArchivo(f"No se pudo leer el archivo: {e}") from None
    except json.JSONDecodeError as e:
        raise ErrorDeArchivo(f"El archivo no es un JSON válido (línea {e.lineno}).") from None


def desde_diccionario(datos: object) -> DisenoCargado:
    _validar_cabecera(datos)
    figura = _generar_desde(datos.get("configuracion"))
    return DisenoCargado(figura, _comparar_bloques(datos.get("bloques"), figura))


def _validar_cabecera(datos: object) -> None:
    if not isinstance(datos, dict) or datos.get("formato") != FORMATO:
        raise ErrorDeArchivo("El archivo no es un diseño de Hexabloq.")
    if not isinstance(datos.get("version"), int) or datos["version"] > VERSION:
        raise ErrorDeArchivo("El diseño se guardó con una versión más reciente del programa.")


def _generar_desde(config: object) -> Figura:
    if not isinstance(config, dict):
        raise ErrorDeArchivo("Falta la sección «configuracion» en el archivo.")
    try:
        return generar(
            Configuracion(
                figura=str(config["figura"]),
                tamano=config["tamano"],
                orientacion=str(config.get("orientacion", "")),
                modo=str(config.get("modo", "contorno")),
                color=str(config.get("color", Configuracion().color)),
            )
        )
    except KeyError as e:
        raise ErrorDeArchivo(f"Falta el dato {e} en la configuración.") from None
    except ErrorDeTamano as e:
        raise ErrorDeArchivo(f"Configuración no válida: {e}") from None


def _comparar_bloques(bloques: object, figura: Figura) -> str | None:
    if bloques is None:
        return None
    try:
        guardados = [(int(x) - 1, int(y) - 1) for x, y in bloques]
    except (TypeError, ValueError):
        return AVISO_BLOQUES_DISTINTOS
    if len(guardados) != figura.total or set(guardados) != figura.conjunto:
        return AVISO_BLOQUES_DISTINTOS
    return None
