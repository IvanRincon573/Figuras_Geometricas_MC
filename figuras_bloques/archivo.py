"""Guardar y abrir diseños en JSON (sin dependencias de Qt)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .geometria import Configuracion, ErrorDeTamano, Figura, generar
from .guia import filas_guia

FORMATO = "figuras-bloques"
VERSION = 1


class ErrorDeArchivo(Exception):
    """Archivo ilegible o con un formato no reconocido (mensaje para el usuario)."""


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
        # Centro de la figura continua con la misma numeración (x.5 = entre dos).
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
    Path(ruta).write_text(_compactar(a_diccionario(figura)), encoding="utf-8")


def _compactar(datos: dict) -> str:
    """JSON legible pero con listas de números en una línea."""
    partes = dict(datos)
    bloques = partes.pop("bloques")
    filas = partes.pop("filas")
    cuerpo = json.dumps(partes, ensure_ascii=False, indent=2)[:-2]  # sin "\n}"
    lineas_filas = ",\n    ".join(json.dumps(f, ensure_ascii=False) for f in filas)
    lineas_bloques = ",\n    ".join(
        ", ".join(json.dumps(b) for b in bloques[i : i + 16]) for i in range(0, len(bloques), 16)
    )
    return (
        f"{cuerpo},\n  \"filas\": [\n    {lineas_filas}\n  ],\n"
        f"  \"bloques\": [\n    {lineas_bloques}\n  ]\n}}\n"
    )


@dataclass
class DisenoCargado:
    figura: Figura
    #: Aviso para el usuario si los bloques guardados no coinciden con los que
    #: genera esta versión del programa (None si todo coincide).
    aviso: str | None


def abrir(ruta: str | Path) -> DisenoCargado:
    try:
        datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ErrorDeArchivo("No se encuentra el archivo.") from None
    except (OSError, UnicodeDecodeError) as e:
        raise ErrorDeArchivo(f"No se pudo leer el archivo: {e}") from None
    except json.JSONDecodeError as e:
        raise ErrorDeArchivo(f"El archivo no es un JSON válido (línea {e.lineno}).") from None
    return desde_diccionario(datos)


def desde_diccionario(datos: object) -> DisenoCargado:
    if not isinstance(datos, dict) or datos.get("formato") != FORMATO:
        raise ErrorDeArchivo("El archivo no es un diseño de Figuras con bloques.")
    if not isinstance(datos.get("version"), int) or datos["version"] > VERSION:
        raise ErrorDeArchivo(
            "El diseño se guardó con una versión más reciente del programa."
        )
    c = datos.get("configuracion")
    if not isinstance(c, dict):
        raise ErrorDeArchivo("Falta la sección «configuracion» en el archivo.")
    try:
        cfg = Configuracion(
            figura=str(c["figura"]),
            tamano=c["tamano"],
            orientacion=str(c.get("orientacion", "")),
            modo=str(c.get("modo", "contorno")),
            color=str(c.get("color", Configuracion().color)),
        )
        figura = generar(cfg)
    except KeyError as e:
        raise ErrorDeArchivo(f"Falta el dato {e} en la configuración.") from None
    except ErrorDeTamano as e:
        raise ErrorDeArchivo(f"Configuración no válida: {e}") from None

    aviso = None
    bloques = datos.get("bloques")
    if bloques is not None:
        try:
            guardados = {(int(x) - 1, int(y) - 1) for x, y in bloques}
        except (TypeError, ValueError):
            guardados = None
        if guardados is None or guardados != figura.conjunto or len(bloques) != figura.total:
            aviso = (
                "Los bloques guardados en el archivo no coinciden con los que genera "
                "esta versión del programa para la misma configuración. Se muestra la "
                "figura recalculada."
            )
    return DisenoCargado(figura, aviso)
