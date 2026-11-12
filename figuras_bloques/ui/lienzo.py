"""Lienzo del mundo: zoom, desplazamiento, selección, arrastre y colocación de figuras.

El lienzo no modifica el documento: emite señales con lo que pide el usuario y la ventana
aplica las operaciones. Trabaja en píxeles físicos y, desde 4 px por bloque, con escala
entera para que todos los bloques se vean como cuadrados idénticos.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QFont, QMouseEvent, QPainter, QPen, QWheelEvent
from PySide6.QtWidgets import QSizePolicy, QWidget

from ..chunks import TAMANO_CHUNK
from ..construccion import Construccion
from ..documento import Documento, Objeto, limites_de
from ..operaciones import ajustar_a_chunk
from . import tema
from .render import (
    OpcionesDibujo,
    Vista,
    colores,
    dibujar_banda,
    dibujar_cursor,
    dibujar_fantasma,
    dibujar_mundo,
    dibujar_seleccion,
)

ESCALA_MIN = 0.25
ESCALA_MAX = 160.0
MARGEN_AJUSTE = 3
UMBRAL_ARRASTRE_PX = 4

SELECCIONAR, MANO, ANADIR = "seleccionar", "mano", "anadir"
REEMPLAZAR, ALTERNAR, SUMAR = "reemplazar", "alternar", "sumar"


class Lienzo(QWidget):
    celdaBajoCursor = Signal(object)
    zoomCambiado = Signal(float)
    seleccionPedida = Signal(tuple, str)
    arrastreMovido = Signal(int, int)
    arrastreTerminado = Signal(int, int)
    colocarPedido = Signal(int, int)
    moverPedido = Signal(int, int)
    eliminarPedido = Signal()
    menuPedido = Signal(QPoint)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setMinimumSize(320, 240)
        self.opciones = OpcionesDibujo()
        self.construccion = Construccion({})
        self.documento = Documento()
        self.seleccion: tuple[str, ...] = ()
        self.plantilla: Objeto | None = None
        self.herramienta = SELECCIONAR
        self.ajuste_chunk = False
        self.mensaje_vacio = ""
        self._escala = 16.0
        self._origen = QPointF(0, 0)
        self._celda_cursor: tuple[int, int] | None = None
        self._pulsacion: QPointF | None = None
        self._modo_arrastre = ""
        self._origen_inicio = QPointF()
        self._desplazamiento = (0, 0)
        self._banda: QRectF | None = None
        self._espacio = False
        self._pendiente_ajuste = True
        self._actualizar_cursor()

    def _dpr(self) -> float:
        return self.devicePixelRatioF() or 1.0

    def _tam_fisico(self) -> tuple[float, float]:
        return self.width() * self._dpr(), self.height() * self._dpr()

    def _fisico(self, pos: QPointF) -> QPointF:
        return QPointF(pos.x() * self._dpr(), pos.y() * self._dpr())

    def vista(self) -> Vista:
        return Vista(self._escala, self._origen, self._dpr())

    def celda_en(self, pos_logica: QPointF) -> tuple[int, int]:
        p = self._fisico(pos_logica)
        return self.vista().bloque_en(p.x(), p.y())

    def centro_visible(self) -> tuple[int, int]:
        w, h = self._tam_fisico()
        return self.vista().bloque_en(w / 2, h / 2)

    @property
    def zoom_logico(self) -> float:
        return self._escala / self._dpr()

    @staticmethod
    def _normalizar(escala: float) -> float:
        escala = max(ESCALA_MIN, min(ESCALA_MAX, escala))
        return float(round(escala)) if escala >= 4 else escala

    def ajustar(self, limites: tuple[int, int, int, int] | None = None) -> None:
        """Encuadra los límites dados (o todo el diseño) en la ventana."""
        por_defecto = (-TAMANO_CHUNK, -TAMANO_CHUNK, TAMANO_CHUNK - 1, TAMANO_CHUNK - 1)
        limites = limites or self.construccion.limites or por_defecto
        if self.width() < 10 or self.height() < 10:
            self._pendiente_ajuste = True
            return
        self._pendiente_ajuste = False
        w, h = self._tam_fisico()
        x0, z0, x1, z1 = limites
        escala = min(w / (x1 - x0 + 1 + 2 * MARGEN_AJUSTE), h / (z1 - z0 + 1 + 2 * MARGEN_AJUSTE))
        escala = max(ESCALA_MIN, min(ESCALA_MAX, escala))
        self._escala = float(math.floor(escala)) if escala >= 4 else escala
        self.centrar_en((x0 + x1 + 1) / 2, (z0 + z1 + 1) / 2)
        self.zoomCambiado.emit(self.zoom_logico)

    def centrar_en(self, x: float, z: float) -> None:
        w, h = self._tam_fisico()
        self._origen = QPointF(round(w / 2 - x * self._escala), round(h / 2 - z * self._escala))
        self.update()

    def zoom(self, factor: float, ancla: QPointF | None = None) -> None:
        w, h = self._tam_fisico()
        a = self._fisico(ancla) if ancla is not None else QPointF(w / 2, h / 2)
        vieja = self._escala
        nueva = self._normalizar(vieja * factor)
        if nueva == vieja and vieja >= 4:
            nueva = self._normalizar(vieja + (1 if factor > 1 else -1))
        if nueva == vieja:
            return
        gx = (a.x() - self._origen.x()) / vieja
        gz = (a.y() - self._origen.y()) / vieja
        self._escala = nueva
        self._origen = QPointF(round(a.x() - gx * nueva), round(a.y() - gz * nueva))
        self.update()
        self.zoomCambiado.emit(self.zoom_logico)

    def asegurar_visible(self, x: int, z: int) -> None:
        w, h = self._tam_fisico()
        v = self.vista()
        margen = 3 * self._escala
        if not (margen <= v.px(x) <= w - margen and margen <= v.pz(z) <= h - margen):
            self.centrar_en(x + 0.5, z + 0.5)

    def set_estado(self, construccion: Construccion, documento: Documento, seleccion) -> None:
        self.construccion = construccion
        self.documento = documento
        self.seleccion = tuple(seleccion)
        self.update()

    def set_opcion(self, nombre: str, valor) -> None:
        setattr(self.opciones, nombre, valor)
        self.update()

    def set_herramienta(self, herramienta: str) -> None:
        self.herramienta = herramienta
        self._actualizar_cursor()
        self.update()

    def set_fila(self, z: int | None) -> None:
        self.opciones.fila_resaltada = z
        if z is not None and self.construccion.filas.get(z):
            self.asegurar_visible(self.construccion.filas[z][0][0], z)
        self.update()

    def _actualizar_cursor(self) -> None:
        forma = {MANO: Qt.CursorShape.OpenHandCursor, ANADIR: Qt.CursorShape.CrossCursor}
        self.setCursor(Qt.CursorShape.OpenHandCursor if self._espacio
                       else forma.get(self.herramienta, Qt.CursorShape.ArrowCursor))

    def fantasma(self) -> Objeto | None:
        """Plantilla centrada en el bloque bajo el cursor, tal como se colocaría al hacer clic."""
        if self.herramienta != ANADIR or self.plantilla is None or self._celda_cursor is None:
            return None
        return posicionar_centrado(self.plantilla, *self._celda_cursor)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if self._pendiente_ajuste:
            self.ajustar()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        d = self._dpr()
        p.scale(1 / d, 1 / d)
        w, h = self._tam_fisico()
        vista = self.vista()
        dibujar_mundo(p, self.construccion, vista, QRectF(0, 0, w, h), self.opciones)
        self._pintar_seleccion(p, vista)
        fantasma = self.fantasma()
        if fantasma is not None:
            dibujar_fantasma(p, vista, fantasma, self.opciones.paleta)
        elif self._celda_cursor is not None:
            dibujar_cursor(p, vista, *self._celda_cursor, self.opciones.paleta)
        if self._banda is not None:
            dibujar_banda(p, self._banda.normalized(), self.opciones.paleta, d)
        p.resetTransform()
        if not self.documento.objetos and self.mensaje_vacio:
            self._pintar_mensaje(p)
        if self.hasFocus():
            p.setPen(QPen(tema.color_qt(tema.ACENTO), 2))
            p.drawRect(self.rect().adjusted(1, 1, -1, -1))
        p.end()

    def _pintar_seleccion(self, p: QPainter, vista: Vista) -> None:
        objetos = self.documento.seleccionados(self.seleccion)
        if not objetos:
            return
        grupos = sorted({o.grupo for o in objetos if o.grupo})
        cajas = [c for g in grupos if (c := limites_de(self.documento.miembros(g)))]
        dibujar_seleccion(p, vista, objetos, cajas, self.opciones.paleta)

    def _pintar_mensaje(self, p: QPainter) -> None:
        fuente = QFont(self.font())
        fuente.setPointSize(11)
        p.setFont(fuente)
        p.setPen(colores(self.opciones.paleta).regla_texto)
        zona = self.rect().adjusted(40, 0, -40, 0)
        p.drawText(zona, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, self.mensaje_vacio)

    def objeto_en(self, x: int, z: int) -> Objeto | None:
        """Objeto visible más arriba cuya área contiene el bloque."""
        return next((o for o in reversed(self.documento.objetos) if o.visible and o.cubre(x, z)), None)

    @staticmethod
    def _modo_seleccion(event) -> str:
        mods = event.modifiers()
        if mods & Qt.KeyboardModifier.ControlModifier:
            return ALTERNAR
        if mods & Qt.KeyboardModifier.ShiftModifier:
            return SUMAR
        return REEMPLAZAR

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802
        delta = event.angleDelta().y()
        if delta:
            self.zoom(1.15 ** (delta / 120), event.position())
        event.accept()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        self.setFocus()
        self._pulsacion = event.position()
        self._origen_inicio = QPointF(self._origen)
        self._desplazamiento = (0, 0)
        if event.button() == Qt.MouseButton.RightButton:
            self._pulsacion = None
            objeto = self.objeto_en(*self.celda_en(event.position()))
            if objeto is not None and objeto.id not in self.seleccion:
                self.seleccionPedida.emit(self.documento.con_grupos([objeto.id]), REEMPLAZAR)
            self.menuPedido.emit(event.globalPosition().toPoint())
            return
        if event.button() == Qt.MouseButton.MiddleButton or self._espacio or self.herramienta == MANO:
            self._modo_arrastre = "vista"
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return
        if event.button() != Qt.MouseButton.LeftButton:
            self._pulsacion = None
            return
        if self.herramienta == ANADIR:
            self._modo_arrastre = "anadir"
            return
        objeto = self.objeto_en(*self.celda_en(event.position()))
        if objeto is None:
            self._modo_arrastre = "banda"
            return
        ids = self.documento.con_grupos([objeto.id])
        modo = self._modo_seleccion(event)
        if modo != REEMPLAZAR:
            self.seleccionPedida.emit(ids, modo)
            self._modo_arrastre = ""
            return
        if objeto.id not in self.seleccion:
            self.seleccionPedida.emit(ids, REEMPLAZAR)
        self._modo_arrastre = "objetos"

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        pos = event.position()
        celda = self.celda_en(pos)
        if celda != self._celda_cursor:
            self._celda_cursor = celda
            self.celdaBajoCursor.emit(celda)
            self.update()
        if self._pulsacion is None or not self._modo_arrastre:
            return
        delta = pos - self._pulsacion
        if self._modo_arrastre == "vista":
            d = self._dpr()
            self._origen = QPointF(round(self._origen_inicio.x() + delta.x() * d),
                                   round(self._origen_inicio.y() + delta.y() * d))
            self.update()
        elif self._modo_arrastre == "objetos":
            self._arrastrar_objetos(delta)
        elif self._modo_arrastre == "banda" and delta.manhattanLength() > UMBRAL_ARRASTRE_PX:
            self._banda = QRectF(self._fisico(self._pulsacion), self._fisico(pos))
            self.update()

    def _arrastrar_objetos(self, delta: QPointF) -> None:
        if delta.manhattanLength() <= UMBRAL_ARRASTRE_PX and self._desplazamiento == (0, 0):
            return
        s = self.zoom_logico
        dx, dz = round(delta.x() / s), round(delta.y() / s)
        if self.ajuste_chunk:
            dx, dz = self._ajustar_desplazamiento_a_chunk(dx, dz)
        if (dx, dz) != self._desplazamiento:
            self._desplazamiento = (dx, dz)
            self.arrastreMovido.emit(dx, dz)

    def _ajustar_desplazamiento_a_chunk(self, dx: int, dz: int) -> tuple[int, int]:
        """La esquina de la selección cae en la esquina de chunk más cercana."""
        caja = limites_de(self.documento.seleccionados(self.seleccion))
        if caja is None:
            return dx, dz
        x_inicial = caja[0] - self._desplazamiento[0]
        z_inicial = caja[1] - self._desplazamiento[1]
        x, z = ajustar_a_chunk(x_inicial + dx, z_inicial + dz)
        return x - x_inicial, z - z_inicial

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._pulsacion is None:
            return
        modo, self._modo_arrastre = self._modo_arrastre, ""
        movido = (event.position() - self._pulsacion).manhattanLength() > UMBRAL_ARRASTRE_PX
        self._pulsacion = None
        self._actualizar_cursor()
        if modo == "objetos" and self._desplazamiento != (0, 0):
            self.arrastreTerminado.emit(*self._desplazamiento)
        elif modo == "anadir" and not movido:
            self.colocarPedido.emit(*self.celda_en(event.position()))
        elif modo == "banda":
            self._terminar_banda(self._modo_seleccion(event), movido)
        self._desplazamiento = (0, 0)

    def _terminar_banda(self, modo: str, movido: bool) -> None:
        banda, self._banda = self._banda, None
        self.update()
        if not movido or banda is None:
            if modo == REEMPLAZAR:
                self.seleccionPedida.emit((), REEMPLAZAR)
            return
        v = self.vista()
        r = banda.normalized()
        x0, z0 = v.bloque_en(r.left(), r.top())
        x1, z1 = v.bloque_en(r.right(), r.bottom())
        tocados = [o.id for o in self.documento.objetos if o.visible and _se_tocan(o.limites(), (x0, z0, x1, z1))]
        self.seleccionPedida.emit(self.documento.con_grupos(tocados), REEMPLAZAR if modo == REEMPLAZAR else SUMAR)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._celda_cursor = None
        self.celdaBajoCursor.emit(None)
        self.update()

    def keyPressEvent(self, event) -> None:  # noqa: N802
        k = event.key()
        paso = TAMANO_CHUNK if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else 1
        direcciones = {Qt.Key.Key_Left: (-paso, 0), Qt.Key.Key_Right: (paso, 0),
                       Qt.Key.Key_Up: (0, -paso), Qt.Key.Key_Down: (0, paso)}
        if k in direcciones and not event.modifiers() & Qt.KeyboardModifier.AltModifier:
            self.moverPedido.emit(*direcciones[k])
        elif k in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.eliminarPedido.emit()
        elif k == Qt.Key.Key_Space and not event.isAutoRepeat():
            self._espacio = True
            self._actualizar_cursor()
        elif k in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
            self.zoom(1.25)
        elif k == Qt.Key.Key_Minus:
            self.zoom(1 / 1.25)
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self._espacio = False
            self._actualizar_cursor()
        else:
            super().keyReleaseEvent(event)

    def focusInEvent(self, event) -> None:  # noqa: N802
        super().focusInEvent(event)
        self.update()

    def focusOutEvent(self, event) -> None:  # noqa: N802
        super().focusOutEvent(event)
        self._espacio = False
        self.update()


def posicionar_centrado(objeto: Objeto, x: int, z: int) -> Objeto:
    """Coloca el objeto con su centro en el bloque (x, z)."""
    forma = objeto.forma()
    return objeto.mover(x - objeto.x - (forma.ancho - 1) // 2, z - objeto.z - (forma.alto - 1) // 2)


def _se_tocan(a, b) -> bool:
    return a[0] <= b[2] and b[0] <= a[2] and a[1] <= b[3] and b[1] <= a[3]
