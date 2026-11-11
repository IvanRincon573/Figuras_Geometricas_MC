"""Cuadrícula interactiva con zoom, desplazamiento y fila resaltada.

Trabaja en píxeles físicos y, desde 4 px por bloque, con escala entera para que
todos los bloques se vean como cuadrados idénticos y nítidos.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QMouseEvent, QPainter, QWheelEvent
from PySide6.QtWidgets import QSizePolicy, QWidget

from ..geometria import Figura
from .render import OpcionesDibujo, Paleta, dibujar_figura

ESCALA_MIN = 0.25
ESCALA_MAX = 160.0
MARGEN_AJUSTE = 2.5  # bloques libres alrededor, para la numeración


class Lienzo(QWidget):
    celdaBajoCursor = Signal(object)
    filaSeleccionada = Signal(object)
    zoomCambiado = Signal(float)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setMinimumSize(320, 240)

        self.figura: Figura | None = None
        self.opciones = OpcionesDibujo(fondo=Paleta.fondo)
        self._escala = 16.0
        self._origen = QPointF(0, 0)
        self._arrastre_inicio: QPointF | None = None
        self._origen_inicio = QPointF(0, 0)
        self._arrastrando = False
        self._pendiente_ajuste = True
        self.mensaje_vacio = ""

    def _dpr(self) -> float:
        return self.devicePixelRatioF() or 1.0

    def _tam_fisico(self) -> tuple[float, float]:
        d = self._dpr()
        return self.width() * d, self.height() * d

    def _a_fisico(self, pos: QPointF) -> QPointF:
        d = self._dpr()
        return QPointF(pos.x() * d, pos.y() * d)

    def celda_en(self, pos_logica: QPointF) -> tuple[int, int]:
        p = self._a_fisico(pos_logica)
        x = math.floor((p.x() - self._origen.x()) / self._escala)
        y = math.floor((p.y() - self._origen.y()) / self._escala)
        return x, y

    @property
    def zoom_logico(self) -> float:
        """Píxeles lógicos (los de Windows con su escalado) por bloque."""
        return self._escala / self._dpr()

    @staticmethod
    def _normalizar_escala(escala: float) -> float:
        escala = max(ESCALA_MIN, min(ESCALA_MAX, escala))
        if escala >= 4:
            escala = float(round(escala))
        return escala

    def set_figura(self, figura: Figura | None, reajustar: bool) -> None:
        anterior = self.figura
        self.figura = figura
        fila = self.opciones.fila_resaltada
        if figura is None or (fila is not None and fila >= figura.alto):
            self.set_fila(None)
        if figura is not None:
            if reajustar or anterior is None:
                self.ajustar()
            elif anterior is not None and (anterior.ancho, anterior.alto) != (figura.ancho, figura.alto):
                d_cx = (figura.centro[0] - anterior.centro[0]) * self._escala
                d_cy = (figura.centro[1] - anterior.centro[1]) * self._escala
                self._origen -= QPointF(d_cx, d_cy)
        self.update()

    def set_opcion(self, nombre: str, valor) -> None:
        setattr(self.opciones, nombre, valor)
        self.update()

    def set_fila(self, fila: int | None, emitir: bool = True) -> None:
        if self.figura is not None and fila is not None:
            if not 0 <= fila < self.figura.alto:
                fila = None
        if fila == self.opciones.fila_resaltada:
            return
        self.opciones.fila_resaltada = fila
        if fila is not None:
            self._asegurar_fila_visible(fila)
        self.update()
        if emitir:
            self.filaSeleccionada.emit(fila)

    def _asegurar_fila_visible(self, fila: int) -> None:
        _, h = self._tam_fisico()
        top = self._origen.y() + fila * self._escala
        margen = 2 * self._escala
        if top < margen:
            self._origen += QPointF(0, margen - top)
        elif top + self._escala > h - margen:
            self._origen -= QPointF(0, top + self._escala - (h - margen))

    def ajustar(self) -> None:
        """Escala y centra la figura para que quepa entera en la ventana."""
        if self.figura is None:
            return
        if self.width() < 10 or self.height() < 10:
            self._pendiente_ajuste = True
            return
        self._pendiente_ajuste = False
        w, h = self._tam_fisico()
        f = self.figura
        escala = min(w / (f.ancho + 2 * MARGEN_AJUSTE), h / (f.alto + 2 * MARGEN_AJUSTE))
        nueva = max(ESCALA_MIN, min(ESCALA_MAX, escala))
        if nueva >= 4:
            nueva = float(math.floor(nueva))
        self._escala = nueva
        self.centrar()
        self.zoomCambiado.emit(self.zoom_logico)

    def centrar(self) -> None:
        if self.figura is None:
            return
        w, h = self._tam_fisico()
        f = self.figura
        self._origen = QPointF(
            round(w / 2 - f.ancho * self._escala / 2),
            round(h / 2 - f.alto * self._escala / 2),
        )
        self.update()

    def zoom(self, factor: float, ancla: QPointF | None = None) -> None:
        """Multiplica el zoom manteniendo fijo el punto ``ancla``."""
        w, h = self._tam_fisico()
        a = self._a_fisico(ancla) if ancla is not None else QPointF(w / 2, h / 2)
        vieja = self._escala
        nueva = self._normalizar_escala(vieja * factor)
        if nueva == vieja and vieja >= 4:
            nueva = self._normalizar_escala(vieja + (1 if factor > 1 else -1))
        if nueva == vieja:
            return
        gx = (a.x() - self._origen.x()) / vieja
        gy = (a.y() - self._origen.y()) / vieja
        self._escala = nueva
        self._origen = QPointF(round(a.x() - gx * nueva), round(a.y() - gy * nueva))
        self.update()
        self.zoomCambiado.emit(self.zoom_logico)

    def mover_fila(self, delta: int) -> None:
        if self.figura is None:
            return
        actual = self.opciones.fila_resaltada
        if actual is None:
            nueva = 0 if delta > 0 else self.figura.alto - 1
        else:
            nueva = max(0, min(self.figura.alto - 1, actual + delta))
        self.set_fila(nueva)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if self._pendiente_ajuste:
            self.ajustar()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        d = self._dpr()
        p.scale(1 / d, 1 / d)
        w, h = self._tam_fisico()
        visible = QRectF(0, 0, w, h)
        p.fillRect(visible, Paleta.fondo)
        if self.figura is None:
            p.resetTransform()
            p.setPen(QColor("#6B665C"))
            f = QFont(self.font())
            f.setPointSize(12)
            p.setFont(f)
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.mensaje_vacio)
            return
        dibujar_figura(p, self.figura, self._escala, self._origen, visible, self.opciones)
        p.end()

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802
        delta = event.angleDelta().y()
        if delta == 0:
            return
        self.zoom(1.15 ** (delta / 120), event.position())
        event.accept()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        self.setFocus()
        if event.button() in (
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.MiddleButton,
            Qt.MouseButton.RightButton,
        ):
            self._arrastre_inicio = event.position()
            self._origen_inicio = QPointF(self._origen)
            self._arrastrando = event.button() != Qt.MouseButton.LeftButton
            if self._arrastrando:
                self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        pos = event.position()
        if self._arrastre_inicio is not None:
            delta = pos - self._arrastre_inicio
            if not self._arrastrando and (abs(delta.x()) + abs(delta.y())) > 4:
                self._arrastrando = True
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
            if self._arrastrando:
                d = self._dpr()
                self._origen = QPointF(
                    round(self._origen_inicio.x() + delta.x() * d),
                    round(self._origen_inicio.y() + delta.y() * d),
                )
                self.update()
        celda = self.celda_en(pos)
        if celda != self.opciones.celda_cursor:
            self.opciones.celda_cursor = celda
            self.update()
            self.celdaBajoCursor.emit(celda)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._arrastre_inicio is None:
            return
        fue_arrastre = self._arrastrando
        self._arrastre_inicio = None
        self._arrastrando = False
        self.setCursor(Qt.CursorShape.CrossCursor)
        if not fue_arrastre and event.button() == Qt.MouseButton.LeftButton and self.figura:
            _, y = self.celda_en(event.position())
            if 0 <= y < self.figura.alto:
                self.set_fila(None if y == self.opciones.fila_resaltada else y)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self.opciones.celda_cursor = None
        self.update()
        self.celdaBajoCursor.emit(None)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        k = event.key()
        if k in (Qt.Key.Key_Down, Qt.Key.Key_S):
            self.mover_fila(1)
        elif k in (Qt.Key.Key_Up, Qt.Key.Key_W):
            self.mover_fila(-1)
        elif k == Qt.Key.Key_Escape:
            self.set_fila(None)
        elif k in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
            self.zoom(1.25)
        elif k == Qt.Key.Key_Minus:
            self.zoom(1 / 1.25)
        else:
            super().keyPressEvent(event)
