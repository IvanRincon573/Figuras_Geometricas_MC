"""Dibujo del mundo de bloques, compartido por el lienzo y la exportación PNG.

``dibujar_mundo`` pinta solo el resultado de construcción y las ayudas de lectura
(cuadrícula, chunks, ejes, coordenadas). La selección, el cursor y la vista previa se
dibujan con funciones aparte que la exportación no usa.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, fields
from functools import lru_cache
from types import SimpleNamespace

from PySide6.QtCore import QLineF, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPen

from ..chunks import TAMANO_CHUNK
from ..construccion import Construccion
from ..documento import Objeto
from .tema import LIENZO_OSCURO, PaletaLienzo, color_qt

PASOS_ETIQUETA = (1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024)
ESCALA_MIN_LINEAS_BLOQUE = 6
ESCALA_MIN_SEPARADORES = 6
ESCALA_MIN_RELIEVE = 14
MAX_CELDAS_CON_SEPARADORES = 60_000
SEPARACION_MIN_CHUNKS_PX = 8
ANCHO_CHUNK_PARA_ETIQUETA_PX = 90
REGLA_LOGICA = 20


@dataclass
class Vista:
    """Transformación mundo → píxeles físicos: el punto (0, 0) del mundo cae en ``origen``."""

    escala: float
    origen: QPointF
    dpr: float = 1.0

    def px(self, x: float) -> float:
        return self.origen.x() + x * self.escala

    def pz(self, z: float) -> float:
        return self.origen.y() + z * self.escala

    def bloque_en(self, px: float, py: float) -> tuple[int, int]:
        return (math.floor((px - self.origen.x()) / self.escala),
                math.floor((py - self.origen.y()) / self.escala))

    def rect(self, x0: float, z0: float, x1: float, z1: float) -> QRectF:
        """Rectángulo en píxeles de los bloques x0…x1, z0…z1 (inclusivos)."""
        return QRectF(self.px(x0), self.pz(z0), (x1 - x0 + 1) * self.escala, (z1 - z0 + 1) * self.escala)


@dataclass
class OpcionesDibujo:
    cuadricula: bool = True
    chunks: bool = True
    coordenadas: bool = True
    ejes: bool = True
    paleta: PaletaLienzo = LIENZO_OSCURO
    rellenar_fondo: bool = True
    fila_resaltada: int | None = None


@lru_cache(maxsize=None)
def colores(paleta: PaletaLienzo) -> SimpleNamespace:
    return SimpleNamespace(**{
        campo.name: color_qt(getattr(paleta, campo.name))
        for campo in fields(paleta) if campo.name != "nombre"
    })


@lru_cache(maxsize=256)
def _tonos(color: str) -> tuple[QColor, QColor, QColor]:
    base = QColor(color)
    return base, base.lighter(125), base.darker(150)


def paso_etiquetas(escala: float, espacio: float) -> int:
    return next((paso for paso in PASOS_ETIQUETA if paso * escala >= espacio), PASOS_ETIQUETA[-1])


def alto_regla(dpr: float) -> float:
    return REGLA_LOGICA * dpr


def dibujar_mundo(p: QPainter, c: Construccion, vista: Vista, visible: QRectF, opciones: OpcionesDibujo) -> None:
    _Mundo(p, c, vista, visible, opciones).dibujar()


class _Mundo:
    def __init__(self, p, c, vista, visible, opciones) -> None:
        self.p, self.c, self.v, self.visible, self.o = p, c, vista, visible, opciones
        self.col = colores(opciones.paleta)
        s = vista.escala
        self.x_min = math.floor((visible.left() - vista.origen.x()) / s) - 1
        self.x_max = math.ceil((visible.right() - vista.origen.x()) / s) + 1
        self.z_min = math.floor((visible.top() - vista.origen.y()) / s) - 1
        self.z_max = math.ceil((visible.bottom() - vista.origen.y()) / s) + 1

    def dibujar(self) -> None:
        self.p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        if self.o.rellenar_fondo:
            self.p.fillRect(self.visible, self.col.fondo)
        if self.o.cuadricula and self.v.escala >= ESCALA_MIN_LINEAS_BLOQUE:
            self._lineas_bloque()
        if self.o.chunks:
            self._lineas_chunk()
            if self.o.coordenadas:
                self._etiquetas_chunk()
        if self.o.fila_resaltada is not None:
            self._banda_fila()
        celdas = self._bloques()
        if self.v.escala >= ESCALA_MIN_SEPARADORES and celdas <= MAX_CELDAS_CON_SEPARADORES:
            self._separadores()
        if self.o.fila_resaltada is not None:
            self._borde_fila()
        if self.o.ejes:
            self._ejes()
        if self.o.coordenadas:
            self._reglas()

    def _tramos_visibles(self):
        if self.c.limites is None:
            return
        _, z_primera, _, z_ultima = self.c.limites
        for z in range(max(self.z_min, z_primera), min(self.z_max, z_ultima) + 1):
            for a, b, color in self.c.filas.get(z, ()):
                inicio, fin = max(a, self.x_min), min(b, self.x_max)
                if inicio <= fin:
                    yield z, inicio, fin, color

    def _lineas_bloque(self) -> None:
        v, area = self.v, self.visible
        omitir_chunks = self.o.chunks
        lineas = [QLineF(v.px(x), area.top(), v.px(x), area.bottom())
                  for x in range(self.x_min, self.x_max + 1) if not (omitir_chunks and x % TAMANO_CHUNK == 0)]
        lineas += [QLineF(area.left(), v.pz(z), area.right(), v.pz(z))
                   for z in range(self.z_min, self.z_max + 1) if not (omitir_chunks and z % TAMANO_CHUNK == 0)]
        self.p.setPen(QPen(self.col.linea_bloque, 1))
        self.p.drawLines(lineas)

    def _paso_chunks(self) -> int:
        paso = TAMANO_CHUNK
        while paso * self.v.escala < SEPARACION_MIN_CHUNKS_PX:
            paso *= 2
        return paso

    def _lineas_chunk(self) -> None:
        v, area = self.v, self.visible
        paso = self._paso_chunks()
        primera_x = math.floor(self.x_min / paso) * paso
        primera_z = math.floor(self.z_min / paso) * paso
        lineas = [QLineF(v.px(x), area.top(), v.px(x), area.bottom())
                  for x in range(primera_x, self.x_max + 1, paso)]
        lineas += [QLineF(area.left(), v.pz(z), area.right(), v.pz(z))
                   for z in range(primera_z, self.z_max + 1, paso)]
        grosor = 2.0 if v.escala >= 6 else 1.0
        self.p.setPen(QPen(self.col.linea_chunk, grosor * max(1.0, v.dpr * 0.8)))
        self.p.drawLines(lineas)

    def _banda_fila(self) -> None:
        z = self.o.fila_resaltada
        self.p.fillRect(QRectF(self.visible.left(), self.v.pz(z), self.visible.width(), self.v.escala),
                        self.col.resaltado_banda)

    def _borde_fila(self) -> None:
        z = self.o.fila_resaltada
        self.p.setPen(QPen(self.col.resaltado_borde, max(2.0, min(4.0, self.v.escala / 6))))
        self.p.setBrush(Qt.BrushStyle.NoBrush)
        for a, b, _ in self.c.filas.get(z, ()):
            self.p.drawRect(self.v.rect(a, z, b, z))

    def _bloques(self) -> int:
        por_color: dict[str, list[QRectF]] = defaultdict(list)
        celdas = 0
        for z, a, b, color in self._tramos_visibles():
            por_color[color].append(self.v.rect(a, z, b, z))
            celdas += b - a + 1
        self.p.setPen(Qt.PenStyle.NoPen)
        for color, rects in por_color.items():
            self.p.setBrush(_tonos(color)[0])
            self.p.drawRects(rects)
        return celdas

    def _separadores(self) -> None:
        s = self.v.escala
        relieve = s >= ESCALA_MIN_RELIEVE
        sombras: dict[str, list[QLineF]] = defaultdict(list)
        luces: dict[str, list[QLineF]] = defaultdict(list)
        for z, a, b, color in self._tramos_visibles():
            arriba, abajo = self.v.pz(z), self.v.pz(z + 1)
            izquierda, derecha = self.v.px(a), self.v.px(b + 1)
            sombras[color] += [QLineF(izquierda, arriba, derecha, arriba),
                               QLineF(izquierda, abajo - 1, derecha, abajo - 1)]
            for x in range(a, b + 2):
                px = self.v.px(x)
                sombras[color].append(QLineF(px, arriba, px, abajo))
                if relieve and x <= b:
                    luces[color] += [QLineF(px + 1, arriba + 1, px + s - 2, arriba + 1),
                                     QLineF(px + 1, arriba + 1, px + 1, abajo - 2)]
        for color, lineas in luces.items():
            self.p.setPen(QPen(_tonos(color)[1], 1))
            self.p.drawLines(lineas)
        for color, lineas in sombras.items():
            self.p.setPen(QPen(_tonos(color)[2], 1))
            self.p.drawLines(lineas)

    def _ejes(self) -> None:
        v, area = self.v, self.visible
        grosor = max(1.5, 2 * v.dpr)
        self.p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.p.setPen(QPen(self.col.eje_x, grosor))
        self.p.drawLine(QLineF(v.px(0), area.top(), v.px(0), area.bottom()))
        self.p.setPen(QPen(self.col.eje_z, grosor))
        self.p.drawLine(QLineF(area.left(), v.pz(0), area.right(), v.pz(0)))
        radio = max(4.0, 5 * v.dpr)
        self.p.setPen(QPen(self.col.origen, max(1.5, 1.5 * v.dpr)))
        self.p.setBrush(self.col.fondo)
        self.p.drawEllipse(QPointF(v.px(0), v.pz(0)), radio, radio)
        self.p.setRenderHint(QPainter.RenderHint.Antialiasing, False)

    def _fuente(self, puntos_logicos: float, negrita: bool = False) -> QFont:
        fuente = QFont("Segoe UI")
        fuente.setPixelSize(max(6, round(puntos_logicos * self.v.dpr)))
        fuente.setBold(negrita)
        return fuente

    def _etiquetas_chunk(self) -> None:
        tam_chunk = TAMANO_CHUNK * self.v.escala
        if tam_chunk < ANCHO_CHUNK_PARA_ETIQUETA_PX * self.v.dpr:
            return
        self.p.setFont(self._fuente(9))
        self.p.setPen(self.col.etiqueta_chunk)
        margen = 4 * self.v.dpr
        for cz in range(math.floor(self.z_min / TAMANO_CHUNK), self.z_max // TAMANO_CHUNK + 1):
            for cx in range(math.floor(self.x_min / TAMANO_CHUNK), self.x_max // TAMANO_CHUNK + 1):
                x, z = self.v.px(cx * TAMANO_CHUNK) + margen, self.v.pz(cz * TAMANO_CHUNK) + margen
                self.p.drawText(QRectF(x, z, tam_chunk, tam_chunk),
                                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, f"chunk {cx}, {cz}")

    def _reglas(self) -> None:
        v, area = self.v, self.visible
        alto = alto_regla(v.dpr)
        fuente = self._fuente(8.5)
        negrita = self._fuente(8.5, negrita=True)
        metricas = QFontMetricsF(fuente)
        self.p.fillRect(QRectF(area.left(), area.top(), area.width(), alto), self.col.regla_fondo)
        self.p.fillRect(QRectF(area.left(), area.top(), alto * 2.2, area.height()), self.col.regla_fondo)
        ancho_etiqueta = metricas.horizontalAdvance("-00000") + 6 * v.dpr
        paso_x = paso_etiquetas(v.escala, ancho_etiqueta)
        paso_z = paso_etiquetas(v.escala, metricas.height() + 4 * v.dpr)
        for x in range(math.floor(self.x_min / paso_x) * paso_x, self.x_max + 1, paso_x):
            es_chunk = x % TAMANO_CHUNK == 0
            self.p.setFont(negrita if es_chunk else fuente)
            self.p.setPen(self.col.regla_chunk if es_chunk else self.col.regla_texto)
            rect = QRectF(v.px(x + 0.5) - ancho_etiqueta / 2, area.top(), ancho_etiqueta, alto)
            if rect.left() > area.left() + alto * 2.2:
                self.p.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(x))
        ancho_regla_z = alto * 2.2
        for z in range(math.floor(self.z_min / paso_z) * paso_z, self.z_max + 1, paso_z):
            es_chunk = z % TAMANO_CHUNK == 0
            resaltada = z == self.o.fila_resaltada
            self.p.setFont(negrita if es_chunk or resaltada else fuente)
            self.p.setPen(self.col.resaltado_borde if resaltada else
                          (self.col.regla_chunk if es_chunk else self.col.regla_texto))
            rect = QRectF(area.left(), v.pz(z + 0.5) - alto / 2, ancho_regla_z - 4 * v.dpr, alto)
            if rect.top() > area.top() + alto:
                self.p.drawText(rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, str(z))
        self.p.setFont(negrita)
        self.p.setPen(self.col.regla_texto)
        self.p.drawText(QRectF(area.left(), area.top(), ancho_regla_z, alto), Qt.AlignmentFlag.AlignCenter, "X / Z")


def dibujar_seleccion(p: QPainter, vista: Vista, objetos: tuple[Objeto, ...], grupos: list[tuple[int, int, int, int]],
                      paleta: PaletaLienzo) -> None:
    """Marco discontinuo alrededor de cada objeto seleccionado (no forma parte del diseño)."""
    col = colores(paleta)
    grosor = max(1.5, 1.5 * vista.dpr)
    holgura = 2 * vista.dpr
    p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
    p.setBrush(Qt.BrushStyle.NoBrush)
    for x0, z0, x1, z1 in grupos:
        p.setPen(QPen(col.seleccion_grupo, grosor, Qt.PenStyle.DotLine))
        p.drawRect(vista.rect(x0, z0, x1, z1).adjusted(-2 * holgura, -2 * holgura, 2 * holgura, 2 * holgura))
    for objeto in objetos:
        rect = vista.rect(*objeto.limites()).adjusted(-holgura, -holgura, holgura, holgura)
        color = col.seleccion if objeto.visible else col.seleccion_oculta
        p.setPen(QPen(color, grosor, Qt.PenStyle.DashLine))
        p.drawRect(rect)
        lado = 5 * vista.dpr
        p.setBrush(color)
        for esquina in (rect.topLeft(), rect.topRight(), rect.bottomLeft(), rect.bottomRight()):
            p.drawRect(QRectF(esquina.x() - lado / 2, esquina.y() - lado / 2, lado, lado))
        p.setBrush(Qt.BrushStyle.NoBrush)
    if len(objetos) == 1:
        _marca_centro(p, vista, *objetos[0].centro(), col.centro_objeto)


def _marca_centro(p: QPainter, vista: Vista, x: float, z: float, color: QColor) -> None:
    centro = QPointF(vista.px(x), vista.pz(z))
    r = max(4.0, min(9.0, vista.escala * 0.35))
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setPen(QPen(color, max(1.5, 1.5 * vista.dpr)))
    p.drawEllipse(centro, r, r)
    p.drawLine(QLineF(centro.x() - r * 1.6, centro.y(), centro.x() + r * 1.6, centro.y()))
    p.drawLine(QLineF(centro.x(), centro.y() - r * 1.6, centro.x(), centro.y() + r * 1.6))
    p.setRenderHint(QPainter.RenderHint.Antialiasing, False)


def dibujar_banda(p: QPainter, rect: QRectF, paleta: PaletaLienzo, dpr: float) -> None:
    col = colores(paleta)
    p.fillRect(rect, col.banda_seleccion)
    p.setPen(QPen(col.seleccion, max(1.0, dpr), Qt.PenStyle.DashLine))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRect(rect)


def dibujar_cursor(p: QPainter, vista: Vista, x: int, z: int, paleta: PaletaLienzo) -> None:
    if vista.escala < 3:
        return
    p.setPen(QPen(colores(paleta).cursor, max(1.5, 1.5 * vista.dpr)))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRect(vista.rect(x, z, x, z))


def dibujar_fantasma(p: QPainter, vista: Vista, objeto: Objeto, paleta: PaletaLienzo) -> None:
    """Vista previa semitransparente de la figura que se va a añadir."""
    color = QColor(objeto.color)
    color.setAlpha(110)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(color)
    forma = objeto.forma()
    p.drawRects([vista.rect(objeto.x + a, objeto.z + dz, objeto.x + b, objeto.z + dz)
                 for dz, fila in enumerate(forma.filas) for a, b in fila])
    p.setPen(QPen(colores(paleta).seleccion, max(1.0, vista.dpr), Qt.PenStyle.DotLine))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRect(vista.rect(*objeto.limites()))
