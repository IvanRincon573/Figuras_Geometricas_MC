"""Guardar y abrir diseños en JSON.

Versión 2: documento con varios objetos, grupos y figuras compuestas.
Versión 1 (una sola figura): se abre como un documento con un objeto en X = 0, Z = 0.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path

from .construccion import Construccion, construir
from .documento import COMPUESTA, NOMBRES_TIPO, Documento, Grupo, Objeto
from .geometria import Configuracion, ErrorDeTamano, Figura, generar
from .guia import filas_guia

FORMATO = "figuras-bloques"
VERSION = 2
BLOQUES_POR_LINEA = 12
CAMPOS_OBJETO = ("id", "nombre", "tipo", "x", "z", "tamano", "orientacion", "modo", "color",
                 "visible", "bloqueado", "grupo", "fusion")
AVISO_BLOQUES_DISTINTOS = (
    "Los bloques guardados en el archivo no coinciden con los que genera esta "
    "versión del programa para el mismo diseño. Se muestra el diseño recalculado."
)


class ErrorDeArchivo(Exception):
    """Archivo ilegible o con un formato no reconocido."""


@dataclass
class DisenoCargado:
    documento: Documento
    aviso: str | None
    version: int


def objeto_a_dict(objeto: Objeto) -> dict:
    datos = {campo: getattr(objeto, campo) for campo in CAMPOS_OBJETO}
    if objeto.es_compuesta:
        datos["origenes"] = [objeto_a_dict(o) for o in objeto.origenes]
    else:
        del datos["fusion"]
    return datos


def objeto_desde_dict(datos: dict) -> Objeto:
    try:
        valores = {campo: datos[campo] for campo in CAMPOS_OBJETO if campo in datos}
        valores["origenes"] = tuple(objeto_desde_dict(o) for o in datos.get("origenes", ()))
        objeto = Objeto(**valores)
        if not isinstance(objeto.x, int) or not isinstance(objeto.z, int):
            raise ErrorDeArchivo(f"La posición de «{objeto.nombre}» no es un número entero de bloques.")
        if objeto.es_compuesta and not objeto.origenes:
            raise ErrorDeArchivo(f"La figura compuesta «{objeto.nombre}» no tiene figuras de origen.")
        if objeto.tipo != COMPUESTA:
            objeto = replace(objeto, color=objeto.configuracion().validada().color)
        objeto.forma()
        return objeto
    except (KeyError, TypeError) as e:
        raise ErrorDeArchivo(f"Un objeto del archivo está incompleto o mal formado ({e}).") from None
    except ErrorDeTamano as e:
        raise ErrorDeArchivo(f"Un objeto del archivo no es válido: {e}") from None


def a_diccionario(documento: Documento) -> dict:
    resultado = construir(documento.objetos)
    return {
        "formato": FORMATO,
        "version": VERSION,
        "coordenadas": (
            "Bloques [x, z, color] en coordenadas globales: X hacia el este, Z hacia el sur. "
            "Chunk = (x // 16, z // 16). Los objetos están en orden de apilado: los últimos "
            "quedan por encima y deciden el color de los bloques compartidos."
        ),
        "documento": {
            "objetos": [objeto_a_dict(o) for o in documento.objetos],
            "grupos": [{"id": g.id, "nombre": g.nombre} for g in documento.grupos],
        },
        "resultado": _resultado(resultado),
    }


def _resultado(c: Construccion) -> dict:
    return {
        "total_bloques": c.total,
        "limites": None if c.limites is None else dict(zip(("x0", "z0", "x1", "z1"), c.limites)),
        "chunks": [{"chunk": [cx, cz], "bloques": n} for (cx, cz), n in c.por_chunk.items()],
        "bloques": [[x, z, color] for x, z, color in c.celdas()],
    }


def guardar(documento: Documento, ruta: str | Path) -> None:
    Path(ruta).write_text(_serializar(a_diccionario(documento)), encoding="utf-8")


def _serializar(datos: dict) -> str:
    """JSON legible con los bloques agrupados en pocas líneas para que ocupe poco."""
    bloques = datos["resultado"]["bloques"]
    marcador = "__BLOQUES__"
    datos = {**datos, "resultado": {**datos["resultado"], "bloques": marcador}}
    texto = json.dumps(datos, ensure_ascii=False, indent=2)
    grupos = ",\n      ".join(
        ", ".join(json.dumps(b, ensure_ascii=False) for b in bloques[i:i + BLOQUES_POR_LINEA])
        for i in range(0, len(bloques), BLOQUES_POR_LINEA)
    )
    return texto.replace(f'"{marcador}"', f"[\n      {grupos}\n    ]" if bloques else "[]") + "\n"


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
    if not isinstance(datos, dict) or datos.get("formato") != FORMATO:
        raise ErrorDeArchivo("El archivo no es un diseño de Hexabloq.")
    version = datos.get("version")
    if not isinstance(version, int) or version > VERSION:
        raise ErrorDeArchivo("El diseño se guardó con una versión más reciente del programa.")
    if version == 1:
        return _desde_version_1(datos)
    return _desde_version_2(datos)


def _desde_version_2(datos: dict) -> DisenoCargado:
    contenido = datos.get("documento")
    if not isinstance(contenido, dict) or not isinstance(contenido.get("objetos"), list):
        raise ErrorDeArchivo("Falta la sección «documento» con la lista de objetos.")
    objetos = tuple(objeto_desde_dict(o) for o in contenido["objetos"])
    if len({o.id for o in objetos}) != len(objetos):
        raise ErrorDeArchivo("Hay objetos con el mismo identificador.")
    try:
        grupos = tuple(Grupo(str(g["id"]), str(g["nombre"])) for g in contenido.get("grupos", ()))
    except (KeyError, TypeError):
        raise ErrorDeArchivo("La lista de grupos está mal formada.") from None
    documento = Documento(objetos, grupos)
    guardados = (datos.get("resultado") or {}).get("bloques")
    aviso = None
    if guardados is not None and not _coinciden(guardados, construir(objetos)):
        aviso = AVISO_BLOQUES_DISTINTOS
    return DisenoCargado(documento, aviso, 2)


def _coinciden(guardados, c: Construccion) -> bool:
    try:
        lista = [(int(x), int(z), str(color)) for x, z, color in guardados]
    except (TypeError, ValueError):
        return False
    return len(lista) == c.total and set(lista) == set(c.celdas())


def _desde_version_1(datos: dict) -> DisenoCargado:
    c = datos.get("configuracion")
    if not isinstance(c, dict):
        raise ErrorDeArchivo("Falta la sección «configuracion» en el archivo.")
    try:
        figura = generar(Configuracion(
            figura=str(c["figura"]), tamano=c["tamano"], orientacion=str(c.get("orientacion", "")),
            modo=str(c.get("modo", "contorno")), color=str(c.get("color", Configuracion().color)),
        ))
    except KeyError as e:
        raise ErrorDeArchivo(f"Falta el dato {e} en la configuración.") from None
    except ErrorDeTamano as e:
        raise ErrorDeArchivo(f"Configuración no válida: {e}") from None
    cfg = figura.config
    objeto = Objeto(id="o1", nombre=f"{NOMBRES_TIPO[cfg.figura]} 1", tipo=cfg.figura, tamano=cfg.tamano,
                    orientacion=cfg.orientacion, modo=cfg.modo, color=cfg.color)
    aviso = None if _coinciden_v1(datos.get("bloques"), figura) else AVISO_BLOQUES_DISTINTOS
    return DisenoCargado(Documento((objeto,)), aviso, 1)


def _coinciden_v1(bloques, figura: Figura) -> bool:
    if bloques is None:
        return True
    try:
        guardados = [(int(x) - 1, int(y) - 1) for x, y in bloques]
    except (TypeError, ValueError):
        return False
    return len(guardados) == figura.total and set(guardados) == figura.conjunto


def a_diccionario_v1(figura: Figura) -> dict:
    """Formato de una sola figura (versión 1); se conserva para pruebas de compatibilidad."""
    cfg = figura.config
    return {
        "formato": FORMATO,
        "version": 1,
        "configuracion": {"figura": cfg.figura, "tamano": cfg.tamano, "orientacion": cfg.orientacion,
                          "modo": cfg.modo, "color": cfg.color},
        "filas": [{"fila": f.fila, "bloques": f.bloques, "tramos": [list(t) for t in f.tramos]}
                  for f in filas_guia(figura)],
        "bloques": [[x + 1, y + 1] for x, y in figura.celdas],
    }
