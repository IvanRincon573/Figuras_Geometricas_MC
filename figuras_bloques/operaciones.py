"""Operaciones de edición. Cada una recibe un documento y devuelve uno nuevo sin modificarlo.

Los objetos bloqueados no se mueven, editan ni eliminan; solo pueden cambiar su nombre,
visibilidad y bloqueo.
"""

from __future__ import annotations

import re
from dataclasses import replace

from .chunks import TAMANO_CHUNK
from .documento import (
    COMPUESTA,
    FUSION_SILUETA,
    FUSIONES,
    NOMBRES_TIPO,
    Documento,
    Grupo,
    Objeto,
    limites_de,
)
from .geometria import ErrorDeTamano

DESPLAZAMIENTO_DUPLICADO = 2
CAMPOS_LIBRES_SI_BLOQUEADO = {"nombre", "visible", "bloqueado"}
ALINEACIONES = ("izquierda", "centro_x", "derecha", "arriba", "centro_z", "abajo")


class ErrorDeOperacion(ValueError):
    """Operación no aplicable, con un mensaje pensado para el usuario."""


def _todos_los_ids(objetos) -> set[str]:
    ids = set()
    for objeto in objetos:
        ids.add(objeto.id)
        ids |= _todos_los_ids(objeto.origenes)
    return ids


def _siguiente(existentes, prefijo: str) -> str:
    numeros = [int(m.group(1)) for e in existentes if (m := re.fullmatch(rf"{prefijo}(\d+)", e))]
    return f"{prefijo}{max(numeros, default=0) + 1}"


def nuevo_id(doc: Documento) -> str:
    return _siguiente(_todos_los_ids(doc.objetos), "o")


def nuevo_id_grupo(doc: Documento) -> str:
    return _siguiente({g.id for g in doc.grupos}, "g")


def nombre_nuevo(doc: Documento, tipo: str) -> str:
    base = NOMBRES_TIPO[tipo]
    numeros = [
        int(m.group(1)) for o in doc.objetos if (m := re.fullmatch(rf"{re.escape(base)} (\d+)", o.nombre))
    ]
    return f"{base} {max(numeros, default=0) + 1}"


def _editables(doc: Documento, ids) -> set[str]:
    return {o.id for o in doc.seleccionados(ids) if not o.bloqueado}


def _sin_grupos_vacios(doc: Documento) -> Documento:
    usados = {o.grupo for o in doc.objetos}
    return replace(doc, grupos=tuple(g for g in doc.grupos if g.id in usados))


def agregar(doc: Documento, objeto: Objeto) -> tuple[Documento, str]:
    objeto.forma()  # valida la configuración antes de añadirla
    id_nuevo = objeto.id or nuevo_id(doc)
    nombre = objeto.nombre or nombre_nuevo(doc, objeto.tipo)
    return replace(doc, objetos=doc.objetos + (replace(objeto, id=id_nuevo, nombre=nombre),)), id_nuevo


def mover(doc: Documento, ids, dx: int, dz: int) -> Documento:
    movibles = _editables(doc, ids)
    if not movibles or (dx, dz) == (0, 0):
        return doc
    return replace(doc, objetos=tuple(o.mover(dx, dz) if o.id in movibles else o for o in doc.objetos))


def colocar(doc: Documento, ids, x: int, z: int) -> Documento:
    """Mueve la selección para que la esquina de su caja quede en (x, z)."""
    caja = limites_de(doc.seleccionados(ids))
    if caja is None:
        return doc
    return mover(doc, ids, x - caja[0], z - caja[1])


def editar(doc: Documento, id_objeto: str, **cambios) -> Documento:
    objeto = doc.buscar(id_objeto)
    if objeto is None:
        raise ErrorDeOperacion("El objeto ya no existe.")
    if objeto.bloqueado and not set(cambios) <= CAMPOS_LIBRES_SI_BLOQUEADO:
        raise ErrorDeOperacion(f"«{objeto.nombre}» está bloqueado: desbloquéalo para editarlo.")
    nuevo = replace(objeto, **cambios)
    if nuevo.es_compuesta and nuevo.fusion not in FUSIONES:
        raise ErrorDeOperacion("Tipo de fusión desconocido.")
    try:
        nuevo.forma()
    except ErrorDeTamano as e:
        raise ErrorDeOperacion(str(e)) from None
    return replace(doc, objetos=tuple(nuevo if o.id == id_objeto else o for o in doc.objetos))


def duplicar(doc: Documento, ids, dx: int = DESPLAZAMIENTO_DUPLICADO,
             dz: int = DESPLAZAMIENTO_DUPLICADO) -> tuple[Documento, tuple[str, ...]]:
    originales = doc.seleccionados(ids)
    grupos_completos = {
        o.grupo for o in originales
        if o.grupo and {m.id for m in doc.miembros(o.grupo)} <= {x.id for x in originales}
    }
    nuevos_grupos: dict[str, str] = {}
    grupos = list(doc.grupos)
    for id_grupo in sorted(grupos_completos):
        nuevo = nuevo_id_grupo(replace(doc, grupos=tuple(grupos)))
        nuevos_grupos[id_grupo] = nuevo
        grupos.append(Grupo(nuevo, f"{doc.grupo(id_grupo).nombre} (copia)"))
    objetos = list(doc.objetos)
    nuevos_ids = []
    for original in originales:
        id_nuevo = nuevo_id(replace(doc, objetos=tuple(objetos)))
        copia = replace(
            original.mover(dx, dz), id=id_nuevo, nombre=f"{original.nombre} (copia)",
            bloqueado=False, grupo=nuevos_grupos.get(original.grupo),
        )
        objetos.append(copia)
        nuevos_ids.append(id_nuevo)
    return replace(doc, objetos=tuple(objetos), grupos=tuple(grupos)), tuple(nuevos_ids)


def eliminar(doc: Documento, ids) -> Documento:
    borrables = _editables(doc, ids)
    return _sin_grupos_vacios(replace(doc, objetos=tuple(o for o in doc.objetos if o.id not in borrables)))


def agrupar(doc: Documento, ids, nombre: str = "") -> tuple[Documento, str]:
    miembros = doc.seleccionados(ids)
    if len(miembros) < 2:
        raise ErrorDeOperacion("Selecciona al menos dos objetos para agruparlos.")
    id_grupo = nuevo_id_grupo(doc)
    nombre = nombre or f"Grupo {id_grupo[1:]}"
    elegidos = {o.id for o in miembros}
    objetos = tuple(replace(o, grupo=id_grupo) if o.id in elegidos else o for o in doc.objetos)
    return _sin_grupos_vacios(replace(doc, objetos=objetos, grupos=doc.grupos + (Grupo(id_grupo, nombre),))), id_grupo


def desagrupar(doc: Documento, ids) -> Documento:
    grupos = {o.grupo for o in doc.seleccionados(ids) if o.grupo}
    if not grupos:
        raise ErrorDeOperacion("La selección no contiene ningún grupo.")
    objetos = tuple(replace(o, grupo=None) if o.grupo in grupos else o for o in doc.objetos)
    return _sin_grupos_vacios(replace(doc, objetos=objetos))


def fusionar(doc: Documento, ids, fusion: str, modo: str = "contorno", nombre: str = "") -> tuple[Documento, str]:
    """Sustituye la selección por una figura compuesta que conserva las originales como origen.

    * ``bloques``: unión exacta de los bloques que ocupan ahora las figuras.
    * ``silueta``: unión de sus áreas rellenas; en contorno solo queda el borde exterior y el
      de los huecos que deje la unión. Las piezas separadas siguen separadas.
    """
    fuentes = doc.seleccionados(ids)
    if len(fuentes) < 2:
        raise ErrorDeOperacion("Selecciona al menos dos figuras para fusionarlas.")
    if fusion not in FUSIONES:
        raise ErrorDeOperacion("Tipo de fusión desconocido.")
    if any(o.bloqueado for o in fuentes):
        raise ErrorDeOperacion("No se pueden fusionar figuras bloqueadas.")
    if any(not o.visible for o in fuentes):
        raise ErrorDeOperacion("No se pueden fusionar figuras ocultas: muéstralas primero.")
    x0, z0, _, _ = limites_de(fuentes)
    origenes = tuple(replace(o.mover(-x0, -z0), grupo=None, visible=True, bloqueado=False) for o in fuentes)
    compuesta = Objeto(
        id=nuevo_id(doc),
        nombre=nombre or nombre_nuevo(doc, COMPUESTA),
        tipo=COMPUESTA, x=x0, z=z0, modo=modo if fusion == FUSION_SILUETA else "relleno",
        color=fuentes[-1].color, fusion=fusion, origenes=origenes,
    )
    elegidos = {o.id for o in fuentes}
    posicion = max(doc.indice(i) for i in elegidos)
    objetos = [o for i, o in enumerate(doc.objetos) if o.id not in elegidos or i == posicion]
    objetos[objetos.index(doc.objetos[posicion])] = compuesta
    return _sin_grupos_vacios(replace(doc, objetos=tuple(objetos))), compuesta.id


def separar(doc: Documento, id_objeto: str) -> tuple[Documento, tuple[str, ...]]:
    """Deshace una fusión: devuelve las figuras de origen a su posición actual en el mundo."""
    compuesta = doc.buscar(id_objeto)
    if compuesta is None or not compuesta.es_compuesta:
        raise ErrorDeOperacion("Selecciona una figura compuesta para separarla.")
    if compuesta.bloqueado:
        raise ErrorDeOperacion(f"«{compuesta.nombre}» está bloqueada: desbloquéala para separarla.")
    usados = _todos_los_ids(o for o in doc.objetos if o.id != id_objeto)
    restaurados = []
    for origen in compuesta.origenes:
        id_final = origen.id if origen.id not in usados else _siguiente(usados, "o")
        usados.add(id_final)
        restaurados.append(replace(origen.mover(compuesta.x, compuesta.z), id=id_final, grupo=compuesta.grupo))
    i = doc.indice(id_objeto)
    objetos = doc.objetos[:i] + tuple(restaurados) + doc.objetos[i + 1:]
    return replace(doc, objetos=objetos), tuple(o.id for o in restaurados)


def reordenar(doc: Documento, ids, hacia: str) -> Documento:
    """``hacia``: "frente", "fondo", "subir" o "bajar" en el orden de apilado."""
    elegidos = set(ids)
    objetos = list(doc.objetos)
    if hacia == "frente":
        objetos = [o for o in objetos if o.id not in elegidos] + [o for o in objetos if o.id in elegidos]
    elif hacia == "fondo":
        objetos = [o for o in objetos if o.id in elegidos] + [o for o in objetos if o.id not in elegidos]
    else:
        paso = 1 if hacia == "subir" else -1
        indices = range(len(objetos) - 2, -1, -1) if paso == 1 else range(1, len(objetos))
        for i in indices:
            j = i + paso
            if objetos[i].id in elegidos and objetos[j].id not in elegidos:
                objetos[i], objetos[j] = objetos[j], objetos[i]
    return replace(doc, objetos=tuple(objetos))


def alinear(doc: Documento, ids, como: str) -> Documento:
    """Alinea bordes o centros de cada objeto con la caja de toda la selección."""
    objetos = [o for o in doc.seleccionados(ids) if not o.bloqueado]
    caja = limites_de(doc.seleccionados(ids))
    if len(objetos) < 2 or caja is None:
        raise ErrorDeOperacion("Selecciona al menos dos objetos desbloqueados para alinearlos.")
    x0, z0, x1, z1 = caja
    for objeto in objetos:
        ox0, oz0, ox1, oz1 = objeto.limites()
        dx = dz = 0
        if como == "izquierda":
            dx = x0 - ox0
        elif como == "derecha":
            dx = x1 - ox1
        elif como == "centro_x":
            dx = (x0 + x1 - ox0 - ox1) // 2
        elif como == "arriba":
            dz = z0 - oz0
        elif como == "abajo":
            dz = z1 - oz1
        elif como == "centro_z":
            dz = (z0 + z1 - oz0 - oz1) // 2
        else:
            raise ErrorDeOperacion(f"Alineación desconocida: {como}.")
        doc = mover(doc, [objeto.id], dx, dz)
    return doc


def ajustar_a_chunk(x: int, z: int) -> tuple[int, int]:
    """Esquina de chunk más cercana a (x, z); a igual distancia, la de mayor coordenada."""
    mitad = TAMANO_CHUNK // 2
    return ((x + mitad) // TAMANO_CHUNK) * TAMANO_CHUNK, ((z + mitad) // TAMANO_CHUNK) * TAMANO_CHUNK
