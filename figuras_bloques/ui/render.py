"""Dibujo de una figura en bloques, compartido por el lienzo y la exportación PNG."""

from __future__ import annotations

import math
from dataclasses import dataclass, fields
from functools import lru_cache
from types import SimpleNamespace

from PySide6.QtCore import QLineF, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPen

from ..geometria import Figura
from .tema import LIENZO_OSCURO, PaletaLienzo, color_qt

PASOS_ETIQUETA = (1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000)
ESCALA_MIN_SEPARADORES = 5
ESCALA_MIN_RELIEVE = 12
MAX_CELDAS_CON_SEPARADORES = 80_000


@dataclass
class OpcionesDibujo:
    cuadricula: bool = True
    ejes: bool = True
    centro: bool = True
    numeros: bool = True
    marco: bool = True
    fila_resaltada: int | None = None
    celda_cursor: tuple[int, int] | None = None
    paleta: PaletaLienzo = LIENZO_OSCURO
    rellenar_fondo: bool = True


@lru_cache(maxsize=None)
def colores(paleta: PaletaLienzo) -> SimpleNamespace:
    return SimpleNamespace(**{
        campo.name: color_qt(getattr(paleta, campo.name))
        for campo in fields(paleta) if campo.name != "nombre"
    })


def paso_etiquetas(escala: float, ancho_texto: float) -> int:
    """Cada cuántas filas o columnas cabe una etiqueta numérica."""
    return next((paso for paso in PASOS_ETIQUETA if paso * escala >= ancho_texto), PASOS_ETIQUETA[-1])


def dibujar_figura(
    p: QPainter,
    figura: Figura,
    escala: float,
    origen: QPointF,
    visible: QRectF,
    opciones: OpcionesDibujo,
) -> None:
    """Dibuja la figura con la celda (0, 0) en ``origen`` y ``escala`` píxeles por bloque."""
    _Dibujo(p, figura, escala, origen, visible, opciones).dibujar()


class _Dibujo:
    def __init__(self, p, figura, escala, origen, visible, opciones) -> None:
        self.p = p
        self.figura = figura
        self.s = escala
        self.ox, self.oy = origen.x(), origen.y()
        self.visible = visible
        self.opciones = opciones
        self.c = colores(opciones.paleta)
        self.color = QColor(figura.config.color)
        self.col_min = math.floor((visible.left() - self.ox) / escala) - 1
        self.col_max = math.ceil((visible.right() - self.ox) / escala) + 1
        self.fila_min = math.floor((visible.top() - self.oy) / escala) - 1
        self.fila_max = math.ceil((visible.bottom() - self.oy) / escala) + 1
        fila = opciones.fila_resaltada
        self.fila = fila if fila is not None and 0 <= fila < figura.alto else None

    def dibujar(self) -> None:
        o = self.opciones
        if o.rellenar_fondo:
            self.p.fillRect(self.visible, self.c.fondo)
        self.p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        if o.marco:
            self.p.fillRect(self._caja(), self.c.marco_relleno)
        if o.cuadricula:
            self._cuadricula()
        if self.fila is not None:
            self._banda_fila()
        celdas = self._bloques()
        if self.s >= ESCALA_MIN_SEPARADORES and celdas <= MAX_CELDAS_CON_SEPARADORES:
            self._separadores()
        if o.marco:
            self._borde_caja()
        if self.fila is not None:
            self._borde_fila()
        self.p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if o.ejes:
            self._ejes()
        if o.centro:
            self._marca_centro()
        if o.celda_cursor is not None and self.s >= 3:
            self._celda_cursor()
        if o.numeros and self.s >= 2:
            self._numeros()

    def _x(self, columna: float) -> float:
        return self.ox + columna * self.s

    def _y(self, fila: float) -> float:
        return self.oy + fila * self.s

    def _caja(self) -> QRectF:
        return QRectF(self.ox, self.oy, self.figura.ancho * self.s, self.figura.alto * self.s)

    def _tramos_visibles(self):
        """(y, primera, última) de cada tramo recortado a la zona visible."""
        for y in range(max(0, self.fila_min), min(self.figura.alto - 1, self.fila_max) + 1):
            for x0, x1 in self.figura.filas[y]:
                a, b = max(x0, self.col_min), min(x1, self.col_max)
                if a <= b:
                    yield y, a, b

    def _cuadricula(self) -> None:
        s, v = self.s, self.visible
        paso_mayor = 5 if s * 5 >= 6 else (10 if s * 10 >= 6 else 50)
        con_menores = s >= 4
        menores: list[QLineF] = []
        mayores: list[QLineF] = []
        for x in range(self.col_min, self.col_max + 1):
            linea = QLineF(self._x(x), v.top(), self._x(x), v.bottom())
            if x % paso_mayor == 0:
                mayores.append(linea)
            elif con_menores:
                menores.append(linea)
        for y in range(self.fila_min, self.fila_max + 1):
            linea = QLineF(v.left(), self._y(y), v.right(), self._y(y))
            if y % paso_mayor == 0:
                mayores.append(linea)
            elif con_menores:
                menores.append(linea)
        self.p.setPen(QPen(self.c.linea_menor, 1))
        self.p.drawLines(menores)
        self.p.setPen(QPen(self.c.linea_mayor, 1))
        self.p.drawLines(mayores)

    def _banda_fila(self) -> None:
        v = self.visible
        self.p.fillRect(QRectF(v.left(), self._y(self.fila), v.width(), self.s), self.c.resaltado_banda)

    def _bloques(self) -> int:
        rects = []
        celdas = 0
        for y, a, b in self._tramos_visibles():
            rects.append(QRectF(self._x(a), self._y(y), (b - a + 1) * self.s, self.s))
            celdas += b - a + 1
        self.p.setPen(Qt.PenStyle.NoPen)
        self.p.setBrush(self.color)
        self.p.drawRects(rects)
        return celdas

    def _separadores(self) -> None:
        s = self.s
        con_relieve = s >= ESCALA_MIN_RELIEVE
        sombras: list[QLineF] = []
        luces: list[QLineF] = []
        for y, a, b in self._tramos_visibles():
            arriba, abajo = self._y(y), self._y(y + 1)
            sombras.append(QLineF(self._x(a), arriba, self._x(b + 1), arriba))
            sombras.append(QLineF(self._x(a), abajo - 1, self._x(b + 1), abajo - 1))
            for x in range(a, b + 2):
                px = self._x(x)
                sombras.append(QLineF(px, arriba, px, abajo))
                if con_relieve and x <= b:
                    luces.append(QLineF(px + 1, arriba + 1, px + s - 2, arriba + 1))
                    luces.append(QLineF(px + 1, arriba + 1, px + 1, abajo - 2))
        if luces:
            self.p.setPen(QPen(self.color.lighter(125), 1))
            self.p.drawLines(luces)
        self.p.setPen(QPen(self.color.darker(150), 1))
        self.p.drawLines(sombras)

    def _borde_caja(self) -> None:
        self.p.setPen(QPen(self.c.marco_borde, 1, Qt.PenStyle.DashLine))
        self.p.setBrush(Qt.BrushStyle.NoBrush)
        self.p.drawRect(self._caja())

    def _borde_fila(self) -> None:
        self.p.setPen(QPen(self.c.resaltado_borde, max(2.0, min(4.0, self.s / 6))))
        self.p.setBrush(Qt.BrushStyle.NoBrush)
        for x0, x1 in self.figura.filas[self.fila]:
            self.p.drawRect(QRectF(self._x(x0), self._y(self.fila), (x1 - x0 + 1) * self.s, self.s))

    def _centro_px(self) -> QPointF:
        cx, cy = self.figura.centro
        return QPointF(self._x(cx), self._y(cy))

    def _ejes(self) -> None:
        c, v = self._centro_px(), self.visible
        grosor = max(1.5, min(3.0, self.s / 8))
        self.p.setPen(QPen(self.c.eje_vertical, grosor, Qt.PenStyle.DashLine))
        self.p.drawLine(QLineF(c.x(), v.top(), c.x(), v.bottom()))
        self.p.setPen(QPen(self.c.eje_horizontal, grosor, Qt.PenStyle.DashLine))
        self.p.drawLine(QLineF(v.left(), c.y(), v.right(), c.y()))

    def _marca_centro(self) -> None:
        c = self._centro_px()
        r = max(4.0, min(10.0, self.s * 0.35))
        self.p.setBrush(Qt.BrushStyle.NoBrush)
        self.p.setPen(QPen(self.c.centro_halo, 3))
        self.p.drawEllipse(c, r, r)
        self.p.setPen(QPen(self.c.centro, 2))
        self.p.drawEllipse(c, r, r)
        self.p.drawLine(QLineF(c.x() - r * 1.6, c.y(), c.x() + r * 1.6, c.y()))
        self.p.drawLine(QLineF(c.x(), c.y() - r * 1.6, c.x(), c.y() + r * 1.6))

    def _celda_cursor(self) -> None:
        x, y = self.opciones.celda_cursor
        self.p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        self.p.setPen(QPen(self.c.cursor, 2))
        self.p.setBrush(Qt.BrushStyle.NoBrush)
        self.p.drawRect(QRectF(self._x(x), self._y(y), self.s, self.s))

    def _numeros(self) -> None:
        fuente = QFont("Segoe UI")
        fuente.setPixelSize(int(round(max(7.0, min(13.0, self.s * 0.55)))))
        self.p.setFont(fuente)
        metricas = QFontMetricsF(fuente)
        ancho_txt = metricas.horizontalAdvance(str(max(self.figura.ancho, self.figura.alto))) + 6
        alto_txt = metricas.height()
        self._numeros_columnas(ancho_txt, alto_txt)
        self._numeros_filas(fuente, ancho_txt, alto_txt)

    def _etiqueta_visible(self, n: int, total: int, paso: int, espacio: float) -> bool:
        if n == 1 or n % paso == 0:
            return True
        return n == total and (n % paso) * self.s >= espacio

    def _numeros_columnas(self, ancho_txt: float, alto_txt: float) -> None:
        paso = paso_etiquetas(self.s, ancho_txt)
        y_txt = max(self.visible.top() + 2, self.oy - alto_txt - 3)
        self.p.setPen(self.c.numeros)
        for x in range(max(0, self.col_min), min(self.figura.ancho - 1, self.col_max) + 1):
            if self._etiqueta_visible(x + 1, self.figura.ancho, paso, ancho_txt):
                rect = QRectF(self._x(x + 0.5) - ancho_txt / 2, y_txt, ancho_txt, alto_txt)
                self.p.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(x + 1))

    def _numeros_filas(self, fuente: QFont, ancho_txt: float, alto_txt: float) -> None:
        paso = paso_etiquetas(self.s, alto_txt + 2)
        x_txt = max(self.visible.left() + 2, self.ox - ancho_txt - 4)
        negrita = QFont(fuente)
        negrita.setBold(True)
        alineacion = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        for y in range(max(0, self.fila_min), min(self.figura.alto - 1, self.fila_max) + 1):
            resaltada = y == self.fila
            if not resaltada and not self._etiqueta_visible(y + 1, self.figura.alto, paso, alto_txt + 2):
                continue
            self.p.setFont(negrita if resaltada else fuente)
            self.p.setPen(self.c.numeros_resaltado if resaltada else self.c.numeros)
            rect = QRectF(x_txt, self._y(y + 0.5) - alto_txt / 2, ancho_txt, alto_txt)
            self.p.drawText(rect, alineacion, str(y + 1))
